'''
Created on Feb 9, 2016

@author: justinpalpant
'''
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QThread, QObject, QTimer, QMutex, QMutexLocker
from PyQt4.QtCore import pyqtSignal, pyqtSlot
import collections

class BGThread(QThread):
    '''
    BGThread defines a background QThread that will run a single function

    The function, self.function, must be parameterless, because it is called as
    part of start() without arguments.  If there are parameters for the
    function, use a lambda to make it a parameterless lambda before initializing
    the BGThread
    '''

    def __init__(self, fn, name=''):
        '''Create a BGThread that will run fn() when started'''

        super(BGThread, self).__init__()
        self._function = fn
        self.name = name

    def __del__(self):
        '''Safe thread deletion... maybe bad if a thread is non-terminating'''
        self.wait()

    def run(self):
        '''The overriden run function just calls this thread's function'''
        self._function()


class SignalStream(QObject):
    '''SignalStream is a file-like object that emits a text signal on writing

    This class is used to provide threadsafe communication of data to the GUI.
    A SignalStream can be used in place of sys.stdout and the instance's 
    write_signal can be connected to a slot that processes the text to where it
    ought to go.  Since signals and slots are threadsafe, this lets you pass
    text from anywhere to anywhere reasonably safely

    SignalStream uses some intelligent buffering to prevent the signalstorm that
    happened the first time I used it.  Signal emit only happens when flush()
    is called - so an application can force a flush - but in order to make sure
    that happens reasonable often SignalStream can be initialized with a QTimer
    on an interval (default: 100ms) and the QTimer will make sure to call flush()
    every 100ms.
    '''

    write_signal = pyqtSignal(str)

    def __init__(self, interval_ms=100):
        '''Create a SignalStream that emits text at least every interval_ms'''

        super(SignalStream, self).__init__()
        self.mutex = QMutex()

        self.data = []
        self.thread = QThread()

        self.pbar_timer = QTimer()
        self.pbar_timer.moveToThread(self.thread)
        self.pbar_timer.setInterval(interval_ms)
        self.pbar_timer.timeout.connect(self.flush)
        self.thread.started.connect(self.pbar_timer.start)
        self.thread.start()

    def __del__(self):
        self.thread.quit()
        self.thread.wait()

    def write(self, m):
        '''Add the message in m to this stream's cache'''
        locker = QMutexLocker(self.mutex)

        self.data.append(m)

    @pyqtSlot()
    def flush(self):
        '''Write all data in the stream and clear the stream's cache'''
        locker = QMutexLocker(self.mutex)

        if self.data:
            self.write_signal.emit(''.join(self.data))
            self.data = []

    def set_interval(self, interval_ms):
        '''Alter the pbar_timer period'''
        self.pbar_timer.setInteval(interval_ms)
        
class OutLog:
    '''OutLog pipes output from a stream to a QTextEdit widget
    '''

    def __init__(self, edit, interval_ms=200):
        """

        """
        self.mutex = QtCore.QMutex()
        self.flag = False

        self.edit = edit
        self.cache = collections.deque()

        self.thread = QtCore.QThread()
        self.pbar_timer = QtCore.QTimer()
        self.pbar_timer.moveToThread(self.thread)
        self.pbar_timer.setInterval(interval_ms)
        self.pbar_timer.timeout.connect(self.flush)
        self.thread.started.connect(self.pbar_timer.start)
        self.thread.start()

    def __del__(self):
        self.thread.quit()
        self.thread.wait()

    def write(self, m):
        locker = QtCore.QMutexLocker(self.mutex)

        for char in str(m):
            if char == '\r':
                if not self.flag:
                    self.edit.moveCursor(
                        QtGui.QTextCursor.StartOfLine,
                        mode=QtGui.QTextCursor.KeepAnchor
                    )
                    self.flag = True

                while char != '\n' and self.cache:
                    char = self.cache.pop()

                if char == '\n':
                    self.cache.append('\n')

            else:
                self.cache.append(char)

    @QtCore.pyqtSlot()
    def flush(self):
        locker = QtCore.QMutexLocker(self.mutex)
        if self.flag:
            self.edit.textCursor().removeSelectedText()
            self.flag = False

        if self.cache:
            self.edit.moveCursor(QtGui.QTextCursor.End)
            self.edit.insertPlainText(''.join(self.cache))
            self.cache = []
            self.edit.moveCursor(QtGui.QTextCursor.End)
