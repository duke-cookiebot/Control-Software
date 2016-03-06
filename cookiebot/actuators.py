'''
Created on Jan 18, 2016

@author: justinpalpant
'''
import enum
import logging
from uuid import uuid1
from cookiebot.multithreading import RepeatedTimer
import time
import array
import sys

onPI = True

if onPI:
    from Adafruit_MotorHAT import Adafruit_MotorHAT
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)


class Actuator(object):
    '''
    Base class for all types of actuators

    This class exposes a set of public methods that an be called to use the
    actuator.  These methods will be identical for all actuators (although they
    will take different arguments)  It also defines some private methods that
    SHOULD or MUST be overridden in order to have a real, functioning actuator
    '''
    logger = logging.getLogger('cookiebot.Actuator')

    @enum.unique
    class State(enum.IntEnum):
        ready = 0
        executing = 1
        executing_blocked = 2
        dead = 3

    def __init__(self, identity='', run_interval=0.1):
        '''
        Constructor

        Prepares an actuator to receive commands, assigns its ID, and starts
        execution.
        '''
        self.logger.debug('Create actuator {0} with interval {1}'.format(identity, run_interval))
        self.state = Actuator.State.ready
        self.identity = identity if identity else str(uuid1())
        self._task = None

        self._timer = RepeatedTimer(run_interval, self._run_execution)

    def __str__(self):
        return self.identity

    def set_task(self, task=None, blocking=False):
        '''Public API for assigning a task to an actuator

        Raises CommandError if the command is, for some reason, invalid
        '''

        if self.state is Actuator.State.dead:
            self.logger.error(
                'Cannot set tasks on {0} because it is dead'.format(self))
            raise CommandError('Actuator is dead and cannot be commanded')

        if self.state is Actuator.State.executing_blocked:
            self.logger.warning(
                'Cannot change task while executing a blocking task')
            raise CommandError(
                'Cannot change task while executing a blocking task')

        if not self._validate_task(task):
            self.logger.error(
                'Invalid task provided to actuator {0}'.format(self))
            raise CommandError(
                'Task {0} is not valid for actuator {1}'.format(task, self))

        self._task = task
        self._task_is_blocking = blocking

    def _run_execution(self):
        '''Private method called repeatedly and frequently to update the state

        Raises ExecutionError if something goes wrong
        '''

        if self._task and self.state == Actuator.State.ready:
            self.state = Actuator.State.executing_blocked if self._task_is_blocking else Actuator.State.executing

        if self.state == Actuator.State.executing or self.state == Actuator.State.executing_blocked:
            if not self._check_bounds():
                self.state = Actuator.State.dead
                self.logger.error(
                    'Bounds violated, setting state of {0} to dead'.format(self))

            if self._task_is_complete():
                self.state = Actuator.State.ready
                self.logger.debug('Done with task for {0}'.format(self))
            else:
                try:
                    self._execute_task()
                except ExecutionError as e:
                    self.logger.error(
                        'Execution failed with error {0}'.format(e))
                    self.logger.error(
                        'Setting actuator to dead on account of error')
                    self.state = Actuator.State.dead

    def kill(self):
        '''Public API method - kill this actuator

        Prevents setting or executing tasks in the future.  Attempts to halt
        actuator

        DOES NOT stop the execution of the RepeatedTimer
        Because that causes a "joining self" error on the thread
        '''

        self.logger.info(
            'Killing actuator {0} and stopping thread'.format(self))
        self.state = Actuator.State.dead
        self.pause()

    def pause(self):
        self.logger.debug('Pausing thread for actuator {0}'.format(self))
        self._timer.stop()

    def unpause(self):
        self.logger.debug('Unpausing thread for actuator {0}'.format(self))
        self._timer.restart()

    def _check_bounds(self):
        '''Private method to make sure that the actuator in a valid location

        Should be uniquely implemented by all subclasses

        Should return True if the actuator is within its bounds/conditions, or
        False otherwise

        This version assumes everything is fine and reports such
        '''

        return True

    def _validate_task(self, task):
        '''Private method for determining if a task if valid for an actuator

        Must be implemented uniquely by all subclasses

        Returns True if the task will be okay, False otherwise

        Default version assumes anything passed at all is a valid task
        This means I could say task='ASHFSDJHSLKBJNS' and the actuator would go
        "Fine by me!"
        Please override this method in subclasses.
        '''

        return True

    def _task_is_complete(self):
        '''Private method for checking if the assigned task (self.task) is done

        Must be implemented uniquely by all subclasses

        Should return True if the task is done enough to stop, else False
        '''

        return True

    def _execute_task(self):
        '''Private method to do external interfacing and actually send commands
        to the actuator

        Must be uniquely implemented by every subclass

        Void method - does not return anything

        Should raise ExecutionError if something horrid happens
        '''

        pass


class StepperActuator(Actuator):
    '''
    Class for controlling any and all linear actuators in the design

    Since we are using the same actuator for all actuation, this should be the
    only class to implement.  Granted, we'll use each actuator differently, but
    all will be instances of this StepperActuator class (barring changes)

    The class must override the five private methods from Actuator - the
    function of each is described in Actuator.
    '''
    class StepType(enum.IntEnum):
        if onPI:
            single = Adafruit_MotorHAT.SINGLE
            double = Adafruit_MotorHAT.DOUBLE
            micro = Adafruit_MotorHAT.MICROSTEP
            interleave = Adafruit_MotorHAT.INTERLEAVE
        else:
            single = 0
            double = 1
            micro = 2
            interleave = 3

    logger = logging.getLogger('cookiebot.Actuator.StepperActuator')

    def __init__(self,
                 identity='',
                 peak_rpm=30,
                 dist_per_step=1.0,
                 max_dist=float('inf'),
                 addr=0x60,
                 steps_per_rev=200,
                 stepper_num=1,
                 step_type=StepType.single,
                 reversed=False):
        '''
        Constructor

        Takes the arguments above (and any other startup information needed,
        like pins, addresses, etc - add them as keyword arguments to the
        constructor) and prepares an actuator for use.

        Connecting to hats and zeroing starting position goes here
        '''

        # superclass constructor
        run_interval = 1.0 / (peak_rpm * 200.0 / 60.0)
        
        super(StepperActuator, self).__init__(
            identity=identity, run_interval=run_interval)

        self.step_style = step_type
        if onPI:
            self.hat = Adafruit_MotorHAT(addr=addr)
            self.stepper = self.hat.getStepper(steps_per_rev, stepper_num)
            self.motors = [1, 2] if stepper_num == 1 else [3, 4]

        self.step_pos = 0
        self.step_size = dist_per_step
        self.max_steps = int(max_dist / self.step_size)

        if reversed:
            self.forward = Adafruit_MotorHAT.BACKWARD
            self.backward = Adafruit_MotorHAT.FORWARD
        else:
            self.forward = Adafruit_MotorHAT.FORWARD
            self.backward = Adafruit_MotorHAT.BACKWARD

    def go_to_zero(self, pin_to_listen):

        # do stuff here - how does GPIO work?
        if onPI:
            GPIO.setup(pin_to_listen, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            
            while GPIO.input(pin_to_listen) == GPIO.LOW:
                time.sleep(0.02)
                self.stepper.oneStep(Adafruit_MotorHAT.BACKWARD, self.step_style.value)

        self.step_pos = 0

    def kill(self):
        super(StepperActuator, self).kill()

        for m in self.motors:
            self.hat.getMotor(m).run(Adafruit_MotorHAT.RELEASE)
        

    @property
    def real_pos(self):
        return self.step_pos * self.step_size

    def _check_bounds(self):
        return (self.step_pos >= 0 and self.step_pos <= self.max_steps)

    def _validate_task(self, task):
        '''Check that task is an iterable containing only -1, 0 or 1'''

        try:
            itertask = iter(task)
        except TypeError:
            return False
        else:
            return set(itertask) <= set((-1, 0, 1))

    def _task_is_complete(self):
        return not self._task

    def _execute_task(self):
        step, self._task = self._task[0], self._task[1:]  # aka generalized pop
        self.step_pos += step
        if onPI:
            if step == -1:
                # step back oneStep
                self.stepper.oneStep(self.backward, self.step_style.value)
            elif step == 1:
                # step forward oneStep
                self.stepper.oneStep(self.forward, self.step_style.value)


class ActuatorWrapper(object):
    '''A wrapper that bundles the function of one or more actuators

    This class is abstract and should not be instantiated in general
    '''

    def __init__(self):
        self._wrapped_actuators = {}

    def unpause(self):
        for act in self._wrapped_actuators.values():
            act.unpause()

    def pause(self):
        for act in self._wrapped_actuators.values():
            act.pause()

    def kill(self):
        for act in self._wrapped_actuators.values():
            act.kill()

    def send(self, command):
        '''The primary method of each ActuatorWrapper - implement the custom
        behavior needed to generate the actuator task, then set the task'''
        pass

    def check_ready(self):
        '''Determine if all actuators can receive a command'''
        readystates = (Actuator.State.ready, Actuator.State.executing)

        for act in self._wrapped_actuators.values():
            if act.state == Actuator.State.dead:
                raise ExecutionError(
                    'Actuator {0} died, cannot be ready'.format(act))
            elif act.state not in readystates:
                return False

        return True


class CommandError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class ExecutionError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def main():

    displayformat = '%(levelname)s: %(asctime)s from %(name)s in %(funcName)s: %(message)s'

    logging.basicConfig(
        level=logging.DEBUG, format=displayformat, stream=sys.stdout)

    
    x = StepperActuator(identity='Test X Actuator',
                 peak_rpm=6,
                 dist_per_step=0.0156,
                 max_dist=16.0,
                 addr=0x60,
                 steps_per_rev=200,
                 stepper_num=1)
    y = StepperActuator(identity='Test Y Actuator',
                 peak_rpm=6,
                 dist_per_step=0.0156,
                 max_dist=16.0,
                 addr=0x60,
                 steps_per_rev=200,
                 stepper_num=2)
    platform = StepperActuator(identity='Test Platform Actuator',
                 peak_rpm=30,
                 dist_per_step=0.00025,
                 max_dist=3.0,
                 addr=0x61,
                 steps_per_rev=200,
                 stepper_num=1)
    nozzle = StepperActuator(identity='Test Nozzle Actuator',
                 peak_rpm=3,
                 dist_per_step=0.00025,
                 max_dist=3.0,
                 addr=0x61,
                 steps_per_rev=200,
                 stepper_num=2)

    acts = [x, y, nozzle, platform]

    for act in acts:
        act.pause()

    task_platform = [1 for _ in xrange(800)]
    task_motor = [1 for _ in xrange(100)]

    platform.set_task(task=array.array('b', task_platform),
                 blocking=True)
    y.set_task(task=array.array('b', task_motor),
               blocking=True)
    x.set_task(task=array.array('b', task_motor),
               blocking=True)

    nozzle.set_task(task=array.array('b', task_motor),
                blocking=False)

    readystates = (Actuator.State.ready, Actuator.State.dead)
    platform.unpause()
    while True:
        print 'Executing platform task'
        time.sleep(1)
        if platform.state in readystates:
            break

    for act in acts:
        act.unpause()
        
    readystates = (Actuator.State.ready, Actuator.State.dead)
    while True:
        print 'Executing task'
        time.sleep(1)
        if all([act.state in readystates for act in acts]):
            break
            

    print 'Done with execution'
    for act in acts:
        act.kill()


if __name__ == "__main__":
    main()
