'''
Created on Jan 29, 2016

@author: justinpalpant
'''
#You need these things and probably don't have them
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal
from PyQt4.uic import loadUiType

Ui_MainWindow, QMainWindow = loadUiType('main.ui')

class CookieGUI(Ui_MainWindow, QMainWindow):
    '''
    classdocs
    '''


    def __init__(self, params):
        '''
        Constructor
        '''
        
        #Initialization of GUI from Qt Designer
        super(AudioGUI, self).__init__()
        self.setupUi(self)
        