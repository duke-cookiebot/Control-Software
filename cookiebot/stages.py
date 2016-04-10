'''
Created on Jan 18, 2016

@author: justinpalpant
'''
from cookiebot.actuators import StepperActuator, ActuatorWrapper, ExecutionError
from cookiebot.multithreading import RepeatedTimer
import enum
import logging
from ast import literal_eval
import array
import time
import os
import sys
import argparse
from collections import defaultdict
from enum import IntEnum

MAIN_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_DIR = os.path.join(MAIN_DIR, 'data')


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
        self.live = True


class IcingStage(Stage):
    '''
    classdocs
    '''
    @enum.unique
    class WrapperID(IntEnum):
        carriage = 0  # blocking
        platform = 1  # blocking
        nozzle = 2  # non-blocking

    class CarriageWrapper(ActuatorWrapper):
        logger = logging.getLogger('cookiebot.ActuatorWrapper.CarriageWrapper')

        def __init__(self):
            super(IcingStage.CarriageWrapper, self).__init__()

            # set connection to stepper parameters here
            # addr, stepper_num, and dist_per_step especially are crucial
            self._wrapped_actuators['xmotor'] = StepperActuator(
                identity='X-axis Stepper',
                peak_rpm=5,
                dist_per_step=0.0122,
                addr=0x60,
                steps_per_rev=200,
                stepper_num=1,
                reversed=False
            )

            self._wrapped_actuators['ymotor'] = StepperActuator(
                identity='Y-axis Stepper',
                peak_rpm=5,
                dist_per_step=0.0128,
                addr=0x60,
                steps_per_rev=200,
                stepper_num=2,
                reversed=False
            )

        def zero(self):
            self._wrapped_actuators['xmotor'].go_to_zero()
            self._wrapped_actuators['xmotor'].go_to_zero()

        def send(self, dest):
            xmotor = self._wrapped_actuators['xmotor']
            ymotor = self._wrapped_actuators['ymotor']

            step_pos = (xmotor.step_pos, ymotor.step_pos)
            pos = (xmotor.real_pos, ymotor.real_pos)
            deltas = (dest[0] - pos[0], dest[1] - pos[1])

            step_delta = (
                int(deltas[0] / xmotor.step_size), int(deltas[1] / ymotor.step_size))

            self.logger.debug(
                'Need to move {0} steps from {1} to {2}'.format(step_delta, pos, dest))

            step_points = self.bresenham((0, 0), step_delta)
            step_points.append(step_delta)

            xsteps = []
            ysteps = []

            last_p = (0, 0)
            for p in step_points:
                xsteps.append(cmp(p[0], last_p[0]))
                ysteps.append(cmp(p[1], last_p[1]))
                last_p = p

            #self.logger.debug('Xsteps: {0}'.format(xsteps))
            #self.logger.debug('Ysteps: {0}'.format(ysteps))

            xmotor.set_task(
                task=array.array('b', xsteps),
                blocking=True)

            ymotor.set_task(
                task=array.array('b', ysteps),
                blocking=True)

        def bresenham(self, start_point, end_point):
            """Bresenham's line tracing algorithm, from roguebasin source

            Inputs:
                start_point: (x,y) pair of integer indices representing the grid 
                    cell where the ray begins
                end_point: (x,y) pair of integer indices representing the grid cell
                    where the ray stops
            Outputs:
                intersected_points: list of (x,y) pairs intersected by the line 
                    between the start and end points.  Does not include the start 
                    or end points
            """

            # Setup initial conditions
            x1, y1 = start_point
            x2, y2 = end_point
            dx = x2 - x1
            dy = y2 - y1

            # Determine how steep the line is
            is_steep = abs(dy) > abs(dx)

            # Rotate line
            if is_steep:
                x1, y1 = y1, x1
                x2, y2 = y2, x2

            # Swap start and end points if necessary and store swap state
            swapped = False
            if x1 > x2:
                x1, x2 = x2, x1
                y1, y2 = y2, y1
                swapped = True

            # Recalculate differentials
            dx = x2 - x1
            dy = y2 - y1

            # Calculate error
            error = int(dx / 2.0)
            ystep = 1 if y1 < y2 else -1

            # Iterate over bounding box generating points between start and end
            y = y1
            points = []
            for x in xrange(x1, x2):
                coord = (y, x) if is_steep else (x, y)
                points.append(coord)
                error -= abs(dy)
                if error < 0:
                    y += ystep
                    error += dx

            # Reverse the list if the coordinates were swapped
            if swapped:
                points.reverse()
            return points

    class NozzleWrapper(ActuatorWrapper):
        logger = logging.getLogger('cookiebot.ActuatorWrapper.NozzleWrapper')

        def __init__(self):
            super(IcingStage.NozzleWrapper, self).__init__()

            # set connection to stepper parameters here
            # addr, stepper_num, and dist_per_step especially are crucial
            self._wrapped_actuators['nozzle'] = StepperActuator(
                identity='Nozzle Stepper',
                peak_rpm=10,
                dist_per_step=0.00025,
                addr=0x61,
                max_dist=1.0,
                steps_per_rev=200,
                stepper_num=1,
                reversed=True
            )

        def zero(self):
            pass

        def send(self, bool_command):
            act = self._wrapped_actuators['nozzle']

            if not bool_command:
                self.logger.debug(
                    'Sending an empty task to turn off the nozzle')
                act.set_task(
                    task=array.array('b', [-1 for _ in xrange(100)]),
                    blocking=True)
            else:
                ticks_to_go = act.max_steps - act.step_pos
                self.logger.debug(
                    'Sending {0} forward steps to keep the nozzle running until 1) it runs out or 2) the task is changed'.format(ticks_to_go))

                act.set_task(
                    task=array.array('b', [1 for _ in xrange(ticks_to_go)]),
                    blocking=False)

    class PlatformWrapper(ActuatorWrapper):

        logger = logging.getLogger('cookiebot.ActuatorWrapper.PlatformWrapper')

        def __init__(self):
            super(IcingStage.PlatformWrapper, self).__init__()

            # set connection to stepper parameters here
            # addr, stepper_num, and dist_per_step especially are crucial
            # also the value of go_to_zero
            self._wrapped_actuators['platform'] = StepperActuator(
                identity='Platform Stepper',
                peak_rpm=30,
                dist_per_step=0.00025,
                max_dist=1.0,
                addr=0x61,
                steps_per_rev=200,
                stepper_num=2,
            )

        def zero(self):
            pass

        def send(self, bool_command):
            act = self._wrapped_actuators['platform']

            if bool_command:
                ticks_to_go = act.max_steps - act.step_pos
                act.set_task(
                    task=array.array('b', [1 for _ in xrange(ticks_to_go)]),
                    blocking=True)
                self.logger.debug(
                    'Sending {0} raising steps'.format(ticks_to_go))
            else:
                ticks_to_go = act.step_pos
                act.set_task(
                    task=array.array('b', [-1 for _ in xrange(ticks_to_go)]),
                    blocking=True)
                self.logger.debug(
                    'Sending {0} lowering steps'.format(ticks_to_go))

    logger = logging.getLogger('cookiebot.Stage.IcingStage')

    def __init__(self, zero=False, actuators=[0, 1, 2]):
        '''
        constructor
        '''

        super(IcingStage, self).__init__()

        self.steps = []

        self._wrappers = {
            IcingStage.WrapperID.carriage: IcingStage.CarriageWrapper(),
            IcingStage.WrapperID.nozzle: IcingStage.NozzleWrapper(),
            IcingStage.WrapperID.platform: IcingStage.PlatformWrapper()
        }

        self.active_wrappers = [id for id in self._wrappers.keys() if id.value in actuators]
        self.logger.debug('Active wrappers are {0}'.format(self.active_wrappers))

        # Set up assorted parameters
        if not zero:
            self.x_cookie_shift = (0.0, 4.0)
            self.y_cookie_shift = (0.0, 4.0)
        if zero:
            self.logger.info('Commanded to zero before execution')
            self.x_cookie_shift = (9.0, 4.0)
            self.y_cookie_shift = (9.0, 4.0)

            for wrap in self._wrappers:
                wrap.zero()

        self._recipe_timer = RepeatedTimer(
            0.1, self._check_recipe, start=False)

    def start_recipe(self):
        self.logger.info('Starting recipe')
        self._recipe_timer.restart()
        for actuator in self._wrappers.values():
            actuator.unpause()

    def stop_recipe(self):
        self.logger.info('Halting recipe progress immediately')
        self._recipe_timer.stop()
        for actuator in self._wrappers.values():
            actuator.pause()

    def recipe_done(self):
        return not self.steps and self._check_actuators()

    def shutdown(self):
        '''This recipe completely stops the execution of the stage

        It CANNOT BE CALLED by the self._recipe_timer, in any way
        '''

        self.steps = []
        self._recipe_timer.stop()
        self.live = False
        for act in self._wrappers.values():
            act.kill()

    def _check_recipe(self):
        '''Frequently-called method that checks if another step of the recipe
        should be executed, and executes it if so'''

        if self.live and self.steps and self._check_actuators():
            # we need to start the next command
            next_step, self.steps = self.steps[0], self.steps[1:]
            self.logger.info('Executing step {0}'.format(next_step))

            for actuator, command in next_step.items():
                if actuator in self.active_wrappers:
                    self._wrappers[actuator].pause()
                    self._wrappers[actuator].send(command)
                else:
                    self.logger.debug(
                        'Not taking steps for actuator {0}'.format(actuator))

            for actuator, command in next_step.items():
                if actuator in self.active_wrappers:
                    self._wrappers[actuator].unpause()

    def _check_actuators(self):
        for w in self._wrappers.values():
            try:
                ready = w.check_ready()
            except ExecutionError as e:
                self.logger.error(
                    'Wrapper says actuator is dead with error {0}'.format(e))
                self.logger.error('Terminating stage')
                self.live = False
                return False

            if not ready:
                return False

        return True

    def load_recipe(self, recipe):
        self.logger.info('Begining recipe load')

        parsed = []

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

        self.logger.info('Loaded a recipe with {0} steps'.format(len(parsed)))

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

        with open(os.path.join(DATA_DIR, filename), 'r') as icingspec:
            for line in icingspec:
                coms.append(
                    {IcingStage.WrapperID(idx): com
                     for idx, com in literal_eval(line).items()
                     }
                )

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


def opts():
    parser = argparse.ArgumentParser(
        description='Test full- or partial-stage control',
        add_help=True, prog='cookiebot_icing_stage')

    parser.add_argument(
        '--freeze', nargs='*', type=int, default=[],
        help='List actuator numbers to NOT actuate; 0=XYMotion, 1=Platform, 2=Nozzle')

    parser.add_argument(
        '--recipe',
        help='Define which file to use as a recipe.  Options are "square", "duke_d", and "duke_outline"'
    )

    parser.add_argument(
        '--zero', action='store_true',
        help='Choose whether or not to zero the actuators.  Default False')

    return parser


def main():
    from cookiebot.recipe import Recipe, RecipeError

    displayformat = '%(levelname)s: %(asctime)s from %(name)s in %(funcName)s: %(message)s'

    logging.basicConfig(
        level=logging.INFO, format=displayformat, stream=sys.stdout)

    args = opts().parse_args()

    r = Recipe()
    r.add_cookie({'icing': getattr(Recipe.IcingType, args.recipe)}, (0, 0))

    print args.freeze
    s = set(args.freeze)
    actuators = [a for a in [0, 1, 2] if a not in s]

    stage = IcingStage(zero=args.zero, actuators=actuators)

    try:
        stage.load_recipe(r)
    except (RecipeError, IOError) as e:
        logging.error(
            'Something is wrong with that recipe file! Shutting down.')
        stage.shutdown()
        raise e

    try:
        starttime = time.time()
        stage.start_recipe()

        while not stage.recipe_done() and stage.live:
            time.sleep(5.0)
            logging.info('Executing the recipe provided')

        if not stage.live:
            logging.error('Stage finished with an error')

        else:
            logging.info(
                'Finished the recipe in {0} seconds!'.format(time.time() - starttime))

    except (KeyboardInterrupt, SystemExit) as e:
        logging.error('Execution-ending exception raised')
        logging.error('Error message: {0}'.format(e))
    else:
        logging.info('Execution finished without error')
    finally:
        logging.info('Shutting down the stage and its actuators')
        stage.shutdown()

if __name__ == '__main__':
    main()
