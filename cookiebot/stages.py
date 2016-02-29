'''
Created on Jan 18, 2016

@author: justinpalpant
'''
from cookiebot.actuators import StepperActuator, ActuatorWrapper
from cookiebot.multithreading import RepeatedTimer
import enum
import logging
from ast import literal_eval


class Stage(object):
    '''
    Stage defines one box of the several needed to make a cookie from scratch

    This class is defined based on how the Controller will interact with it,
    and how it will interact with it's actuators. Most of the definition will
    be done in the specific stage subclasses.

    In general this class should be considered abstract, even if I don't put
    the abc decorator on any of the methods in the end
    '''

    def __init__(self):
        '''
        Constructor
        '''
        pass


class IcingStage(Stage):
    '''
    classdocs
    '''
    @enum.unique
    class WrapperID(enum.IntEnum):
        carriage = 0  # blocking
        platform = 1  # blocking
        nozzle = 2  # non-blocking

    class CarriageWrapper(ActuatorWrapper):

        def __init__(self):
            super(IcingStage.CarriageWrapper, self).__init__()

    class NozzleWrapper(ActuatorWrapper):

        def __init__(self):
            super(IcingStage.NozzleWrapper, self).__init__()

    class PlatformWrapper(ActuatorWrapper):

        def __init__(self):
            super(IcingStage.PlatformWrapper, self).__init__()

    logger = logging.getLogger('cookiebot.Stage.IcingStage')

    def __init__(self):
        '''
        constructor
        '''

        super(IcingStage, self).__init__()

        self.steps = []

        # Set up assorted parameters
        self.x_cookie_shift = (3.0, 4.0)
        self.y_cookie_shift = (3.0, 4.0)

        self._wrappers = {
            IcingStage.WrapperID.carriage: IcingStage.CarriageWrapper(),
            IcingStage.WrapperID.nozzle: IcingStage.NozzleWrapper(),
            IcingStage.WrapperID.platform: IcingStage.PlatformWrapper()
        }

        self._recipe_timer = RepeatedTimer(0.05, self._check_recipe)
        self._recipe_timer.stop()

    def start_recipe(self):
        self.logger.info('Starting recipe')
        self._recipe_timer.restart()

    def stop_recipe(self):
        self._recipe_timer.stop()

    def _check_recipe(self):
        '''Frequently-called method that checks if another step of the recipe
        should be executed, and executes it if so'''

        if self.steps and self._actuators_ready:
            # we need to start the next command
            next_step, self.steps = self.steps[0], self.steps[1:]
            self.logger.info('Executing step {0}'.format(next_step))

            for actuator, command in next_step.items():
                self._wrappers[actuator].pause()
                self._wrappers[actuator].send(command)

            for actuator, command in next_step.items():
                self._wrappers[actuator].unpause()

    @property
    def _actuators_ready(self):
        return all([w.ready for w in self._wrappers.values()])

    def load_recipe(self, recipe):
        parsed = []

        # every recipe starts by raising the platform, stopping the nozzle and
        # zeroing the carriage

        parsed.append({IcingStage.WrapperID.carriage: (0, 0),
                       IcingStage.WrapperID.nozzle: False,
                       IcingStage.WrapperID.platform: True
                       })

        for cookie_pos, cookie_spec in recipe.cookies.iteritems():
            icing_coms = self._load_icing_file(cookie_spec['icing'].value)
            offset_coms = self._offset_commands(icing_coms, cookie_pos)
            parsed.extend(offset_coms)

        # every recipe ends by stopping the nozzle, zeroing the carriage, and
        # lowering the platform

        parsed.append({IcingStage.WrapperID.carriage: (0, 0),
                       IcingStage.WrapperID.nozzle: False,
                       IcingStage.WrapperID.platform: False
                       })

        self.steps = parsed[:]

    def _load_icing_file(self, filename):
        '''Load an icing file and return a list of commands

        Arguments:
            filename - an icing spec file

        Returns:
            A list of dictionaries {actuator:command}, each defining one
            'action'

            e.g. [{IcingStage.WrapperID.carriage:(0,1),
                   IcingStage.WrapperID.nozzle:False}]

            Would move to (0,1) with the nozzle off, no action for the platform

            Commands in a dictionary can be assumed to be started relatively
            simultaneously (think us difference)

        Assigned to Cynthia
        '''
        coms = []

        with open(filename, 'r') as icingspec:
            for line in icingspec:
                coms.append(literal_eval(line))

        return coms

    def _offset_commands(self, commands, pos):
        '''Take a list of command dictionaries and shift the positions based on
        which cookie slot the cookie belongs to

        Arguments:
            commands - a list of command dictionaries, as returned by
                load_icing_file
            pos - a cookie position, as returned by a recipe

        Returns:
            An updated list of command dictionaries
        '''
        new_commands = list(commands)

        for c in new_commands:
            if IcingStage.WrapperID.carriage in c:
                old_dest = c[IcingStage.WrapperID.carriage]
                new_dest = self._shift_point(old_dest, pos)
                c[IcingStage.WrapperID.carriage] = new_dest

        return new_commands

    def _shift_point(self, coord, cookiepos):
        '''Shift a single coordinate based on the cookiepos it belongs to'''

        x = self.x_cookie_shift[0] + coord[0] + \
            cookiepos[0] * self.x_cookie_shift[1]
        y = self.y_cookie_shift[0] + coord[1] + \
            cookiepos[1] * self.y_cookie_shift[1]

        return (x, y)


def main():
    from cookiebot.recipe import Recipe, RecipeError

    logging.basicConfig(level=logging.DEBUG)

    r = Recipe()
    r.add_cookie({'icing': Recipe.IcingType.square}, (0, 0))

    stage = IcingStage()
    try:
        stage.load_recipe(r)
    except RecipeError:
        print 'Something is wrong with that recipe file!'
        return

    stage.start_recipe()

if __name__ == '__main__':
    main()
