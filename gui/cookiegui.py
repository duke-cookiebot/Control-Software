'''
Created on Jan 29, 2016

@author: justinpalpant
'''
# You need these things and probably don't have them
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import pyqtSignal, QRectF
from PyQt4.QtGui import QGraphicsScene, QPixmap
from PyQt4.uic import loadUiType
import sys
import logging
import datetime
import os

from cookiebot.recipe import Recipe, RecipeError
from cookiebot.stages import IcingStage
from cookiebot.multithreading import RepeatedTimer
from threadsafety import OutLog, SignalStream

MAIN_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_DIR = os.path.join(MAIN_DIR, 'data')
GUI_DIR = os.path.join(MAIN_DIR, 'gui')
Ui_MainWindow, QMainWindow = loadUiType(os.path.join(GUI_DIR, 'main.ui'))


class CookieGUI(Ui_MainWindow, QMainWindow):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        Constructor
        '''

        # Initialization of GUI from Qt Designer
        super(CookieGUI, self).__init__()
        self.setupUi(self)

        # add button
        # clear button (must reset all displays and cookiepos)
        # run button
        # cancel button

        self.add_cookie_button.clicked.connect(self._add_cookie_callback)
        self.clear_recipe_button.clicked.connect(self._reset_recipe_callback)
        self.start_button.clicked.connect(self._run_click_callback)
        self.stop_button.clicked.connect(self._cancel_execution_callback)
        self.terminate_button.clicked.connect(self._shutdown_stage_callback)

        self.logger = logging.getLogger('cookiebot')

        self.printerbox = OutLog(self.console, interval_ms=250)
        self.printstream = SignalStream(interval_ms=100)

        sys.stdout = self.printstream
        sys.stderr = self.printstream
        self.printstream.write_signal.connect(self.print_to_gui)
        screen_handler = logging.StreamHandler(stream=self.printstream)
        screen_format = logging.Formatter(fmt='%(asctime)s - %(message)s')
        screen_handler.setLevel(logging.INFO)
        screen_handler.setFormatter(screen_format)
        self.logger.addHandler(screen_handler)

        self.logger.setLevel(logging.DEBUG)

        self.logger.info('Start of program execution '
                         '{0}'.format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        self.recipe = Recipe()
        self.stage = IcingStage(zero=False, actuators=[0, 1, 2])

        self.positions = [(0, 0), (1, 0), (0, 1), (1, 1)]
        self.q_image_displays = [
            self.image_00, self.image_10, self.image_01, self.image_11]

        self.icings = [
            Recipe.IcingType.d_outline,
            Recipe.IcingType.u_outline,
            Recipe.IcingType.k_outline,
            Recipe.IcingType.e_outline,
            Recipe.IcingType.square,
            Recipe.IcingType.spiral_square,
            Recipe.IcingType.blue_devil
        ]

        self.pattern_images = [
            Recipe.IcingImage.d_outline,
            Recipe.IcingImage.u_outline,
            Recipe.IcingImage.k_outline,
            Recipe.IcingImage.e_outline,
            Recipe.IcingImage.square,
            Recipe.IcingImage.spiral_square,
            Recipe.IcingImage.blue_devil
        ]

        self.pbar_timer = RepeatedTimer(0.25, self._update_progress_bar, start=False)

        self.show()

    @QtCore.pyqtSlot(str)
    def print_to_gui(self, text):
        '''Routes a message to this instance's textbox

        This is a slot and is implemented in conjunction with the SignalStream
        in threadsafety to provide thread safe access to the GUI textbox
        '''
        self.printerbox.write(text)

    def _run_click_callback(self):
        if self.stage.live:
            if self.stage.recipe_done():
                self.logger.info('Starting a new recipe!')
                try:
                    self.stage.load_recipe(self.recipe)
                    self.num_steps = float(len(self.stage.steps))
                except (RecipeError, IOError) as e:
                    logging.error(
                        'Something is wrong with that recipe file! Shutting down.')
                    self.stage.shutdown()
                    raise e
                self.pbar_timer.restart()
            else:
                self.logger.info('Rebooting the recipe that was running')
            self.stage.start_recipe()
        else:
            self.logger.info(
                'Stage is dead, cannot do anything.  Please exit.')

    def _add_cookie_callback(self):
        if self.stage.live:
            cookie_idx = self.cookie_select.currentIndex()
            pos_idx = self.pos_select.currentIndex()

            self.logger.info(
                'Adding cookie {0} to the recipe at {1}'.format(self.icings[cookie_idx], self.positions[pos_idx]))
            self.recipe.add_cookie(
                {'icing': self.icings[cookie_idx]}, self.positions[pos_idx])

            image = self.q_image_displays[pos_idx]

            scene = QGraphicsScene()
            scene.addPixmap(
                QPixmap(os.path.join(DATA_DIR, self.pattern_images[cookie_idx].value)))
            image.setScene(scene)
            image.fitInView(scene.itemsBoundingRect())

            image.show()

        else:
            self.logger.info(
                'Stage is dead, cannot do anything.  Please exit.')

    def _reset_recipe_callback(self):
        if self.stage.live:
            self.recipe = Recipe()
            if self.stage.steps:
                self.stage.steps = []
                
            for image in self.q_image_displays:
                image.setScene(QGraphicsScene())

            self.logger.info('Recipe cleared')
        else:
            self.logger.info(
                'Stage is dead, cannot do anything.  Please exit.')

    def _cancel_execution_callback(self):
        if self.stage.live and not self.stage.recipe_done():
            self.logger.info('Pausing recipe execution')
            self.stage.stop_recipe()
            self.logger.info('Recipe execution paused')

    def _shutdown_stage_callback(self):
        self.logger.warning('Terminating the icing stage')
        self.stage.shutdown()
        self.logger.warning('Stage terminated.  Please exit.')
        
    def _update_progress_bar(self):
        fraction_to_go = len(self.stage.steps) / self.num_steps if self.num_steps else 1
        self.progress_bar.setValue(100*(1-fraction_to_go))

    def closeEvent(self, event):
        self.logger.info("User has clicked the red x on the main window")
        self.stage.shutdown()
        self.pbar_timer.stop()
        event.accept()

def main():
    displayformat = '%(levelname)s: %(asctime)s from %(name)s in %(funcName)s: %(message)s'

    logging.basicConfig(
        level=logging.DEBUG, format=displayformat, stream=sys.stdout)

    app = QtGui.QApplication(sys.argv)

    main_window = CookieGUI()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
