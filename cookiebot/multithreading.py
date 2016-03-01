'''
Created on Feb 27, 2016

@author: justinpalpant
'''
import time
from threading import Event, Thread

class RepeatedTimer(object):
    """Repeat `function` every `interval` seconds.

    Class courtesy of Six on StackOverflow
    See http://stackoverflow.com/a/33054922/5370002 for more
    """

    def __init__(self, interval, function, start=True, *args, **kwargs):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.start = time.time()
        self.running = False
        if start:
            self.restart()

    def _target(self):
        while not self.event.wait(self._time):
            self.function(*self.args, **self.kwargs)

    @property
    def _time(self):
        return self.interval - ((time.time() - self.start) % self.interval)

    def stop(self):
        if self.running:
            self.event.set()
            self.my_thread.join()
            self.running = False

    def restart(self):
        if not self.running:
            self.event = Event()
            self.my_thread = Thread(target=self._target)
            self.my_thread.start()
            self.running = True


def demo():
    count = [0]

    othercount = [0]
    
    def countup(id, counter, start, printiter):
        counter[0] += 1
        if counter[0] % printiter == 0:
            print 'ID {0}, time {1}, did a thing {2} times'.format(id, time.time() - start, counter[0])

    start = time.time()
    res = 2000
    res2 = 200
    t = RepeatedTimer(1.0 / res, lambda: countup('1st', count, start, res))
    t2 = RepeatedTimer(1.0 / res2, lambda: countup('2nd', othercount, start, res2))

    time.sleep(8)

    t.stop()

    print 'Stopped?  Wait 2s and then restart Restart'

    time.sleep(2)

    t.restart()

    time.sleep(5.01)

    t.stop()
    t2.stop()


if __name__ == '__main__':
    demo()
