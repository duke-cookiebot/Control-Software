'''
Created on Jan 18, 2016

@author: justinpalpant
'''
from cookiebot.actuators import StepperActuator
from cookiebot.multithreading import RepeatedTimer
import enum


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

        self.busy = False


class IcingStage(Stage):
    '''
    classdocs
    '''
    @enum.unique
    class Actuators(enum.IntEnum):
        carriage = 0  # blocking
        platform = 1  # blocking
        nozzle = 2  # non-blocking

    def __init__(self):
        '''
        constructor
        '''

        super(IcingStage, self).__init__()

        self.steps = []

        # Set up assorted parameters
        self.x_cookie_shift = (1.0, 3.0)
        self.y_cookie_shift = (1.0, 3.0)

        self.platform_max = 1.0  # inches, acts as bound
        self.xmax = 10.0  # inches, acts as bound
        self.ymax = 10.0  # inches, acts as bound
        self.nozzlemax = 4.0  # inches, acts as bound

        self.platform = StepperActuator()

        self.recipe_timer = RepeatedTimer(0.01, self._check_recipe)
        self.recipe_timer.stop()

    def start_recipe(self):
        self.recipe_timer.start()

    def stop_recipe(self):
        self.recipe_timer.stop()

    def _check_recipe(self):
        '''Frequently-called method that checks if another step of the recipe
        should be executed, and executes it if so'''

        if self.steps:
            if not self.busy or (self.busy and self._actuators_ready):
                # we need to start the next command
                next_step, self.steps = self.steps[0], self.steps[1:]

                for actuator, command in next_step:
                    self._actuators(actuator).pause()
                    self._generate_and_send_task(actuator, command)

                for actuator, command in next_step:
                    self._actuators(actuator).unpause()

    @property
    def _actuators_ready(self):
        return False

    def _generate_and_send_task(self, actuator, command):
        task = []

        if actuator == IcingStage.Actuators.carriage:
            blocking = True
        elif actuator == IcingStage.Actuators.platform:
            blocking = True
        elif actuator == IcingStage.Actuators.nozzle:
            blocking = False

        self._actuators(actuator).set_task(task, blocking)

    def _actuators(self, actuator):
        if actuator == IcingStage.Actuators.carriage:
            return self.carriage
        elif actuator == IcingStage.Actuators.platform:
            return self.platform
        elif actuator == IcingStage.Actuators.nozzle:
            return self.nozzle

    def load_recipe(self, recipe):
        parsed = []

        # every recipe starts by raising the platform, stopping the nozzle and
        # zeroing the carriage

        parsed.append({IcingStage.Actuators.carriage: (0, 0),
                       IcingStage.Actuators.nozzle: False,
                       IcingStage.Actuators.platform: self.platform_max
                       })

        for cookie_pos, cookie_spec in recipe.cookies.iteritem():
            icing_coms = self._load_icing_file(cookie_spec['icing'])
            offset_coms = self._offset_commands(icing_coms, cookie_pos)
            parsed.extend(offset_coms)

        # every recipe ends by stopping the nozzle, zeroing the carriage, and
        # lowering the platform

        parsed.append({IcingStage.Actuators.carriage: (0, 0),
                       IcingStage.Actuators.nozzle: False,
                       IcingStage.Actuators.platform: 0
                       })

        self.steps = parsed[:]

    def _load_icing_file(self, filename):
        '''Load an icing file and return a list of commands

        Arguments:
            filename - an icing spec file

        Returns:
            A list of dictionaries {actuator:command}, each defining one
            'action'

            e.g. [{IcingStage.Actuators.carriage:(0,1),
                   IcingStage.Actuators.nozzle:False}]

            Would move to (0,1) with the nozzle off, no action for the platform

            Commands in a dictionary can be assumed to be started relatively
            simultaneously (think us difference)

        Assigned to Cynthia
        '''

        return []

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
        new_commands = dict(commands)

        for c in new_commands:
            if IcingStage.Actuators.carriage in c:
                old_dest = c[IcingStage.Actuators.carriage]
                new_dest = self._shift_point(old_dest, pos)
                c[IcingStage.Actuators.carriage] = new_dest

        return new_commands

    def _shift_point(self, coord, cookiepos):
        '''Shift a single coordinate based on the cookiepos it belongs to'''

        x = coord[0] + cookiepos[0] * self.x_cookie_spacing
        y = coord[1] + cookiepos[1] * self.y_cookie_spacing

        return (x, y)


def main():
    from cookiebot.recipe import Recipe, RecipeError

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
