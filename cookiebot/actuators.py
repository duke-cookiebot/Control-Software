'''
Created on Jan 18, 2016

@author: justinpalpant
'''
import enum
import logging
from uuid import uuid1
from threading import Timer


class Actuator(object):
    '''
    Base class for all types of actuators

    This class exposes a set of public methods that an be called to use the
    actuator.  These methods will be identical for all actuators (although they
    will take different arguments)  It also defines some private methods that
    SHOULD or MUST be overridden in order to have a real, functioning actuator
    '''
    logger = logging.getLogger('CookieBot.Actuator')

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
        self.state = Actuator.State.ready
        self.id = identity if identity else str(uuid1())
        self._task = None

        self.timer = RepeatedTimer(run_interval, self.run_execution)

    def __str__(self):
        return self.id

    def set_task(self, task=None, blocking=False):
        '''Public API for assigning a task to an actuator

        Raises CommandError if the command is, for some reason, invalid
        '''

        if self.state is Actuator.State.dead:
            self.logger.error(
                'Cannot set tasks on {0} because it is dead'.format(self.id))
            raise CommandError('Actuator is dead and cannot be commanded')

        if self.state is Actuator.State.executing_blocked:
            self.logger.warning(
                'Cannot change task while executing a blocking task')
            raise CommandError(
                'Cannot change task while executing a blocking task')

        if not self._validate_task(task):
            self.logger.error(
                'Invalid task provided to actuator {0}'.format(self.id))
            raise CommandError(
                'Task {0} is not valid for actautor {1}'.format(task, self.id))

        self._task = task
        self._task_is_blocking = blocking

    def run_execution(self):
        '''Public API called repeatedly and frequently to update the state

        Raises ExecutionError if something goes wrong
        '''

        if self.state is Actuator.State.dead:
            self.logger.error(
                'Cannot set tasks on {0} because it is dead'.format(self.id))
            raise ExecutionError('Actuator is dead and cannot be commanded')

        if self._task and self.state == Actuator.State.ready:
            self.state = Actuator.State.executing_blocked if self._task_is_blocking else Actuator.State.executing

        if self._task and (self.state == Actuator.State.executing or self.state == Actuator.State.executing_blocked):
            if not self._check_bounds():
                self.kill()
                raise ExecutionError('Bounds violated, actuator killed')

            if self._task_is_complete():
                self.state = Actuator.State.ready
                self._task = None
            else:
                try:
                    self._execute_task()

                except ExecutionError as e:
                    self.logger.error('Unable to execute task')
                    raise e

        if self._task is None:
            self.logger.debug('Waiting for a task to be assigned')
            self.logger.debug('Actuator state is {0}'.format(self.state))

    def kill(self):
        '''Public API method - kill this actuator

        Prevents setting or executing tasks in the future.  Attempts to halt
        actuator
        '''

        self.state = Actuator.State.dead
        self._halt()

    def _check_bounds(self):
        '''Private method to make sure that the actuator in a valid location

        Should be uniquely implemented by all subclasses

        Should return True if the actuator is within its bounds/conditions, or
        False otherwise

        This version assumes everything is fine and reports such
        '''

        return True

    def _halt(self):
        '''Private method that should do anything necessary to safely stop the
        actuator

        Should be uniquely implemented by each subclass

        Void method, does not have to return anything
        '''

        pass

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

    logger = logging.getLogger('CookieBot.Actuator.StepperActuator')

    def __init__(self,
                 identity='',
                 run_interval=0.1,
                 dist_per_step=1.0,
                 max_dist=float('inf')):
        '''
        Constructor

        Takes the arguments above (and any other startup information needed,
        like pins, addresses, etc - add them as keyword arguments to the
        constructor) and prepares an actuator for use.

        Connecting to hats and zeroing starting position goes here
        '''

        # superclass constructor
        super(StepperActuator, self).__init__(
            identify=identity, run_interval=run_interval)

        ''' do the things that zero the stepper position here
        
        
        '''
        self.step_pos = 0
        self.step_size = dist_per_step
        self.max_steps = max_dist / self.step_size

    @property
    def real_pos(self):
        return self.step_pos / self.step_size

    def _check_bounds(self):
        return (self.step_pos > 0 and self.step_pos < self.max_steps)

    def _halt(self):
        self._task = []
        # do other things to quickly stop the stepper, if necessary

    def _validate_task(self, task):
        '''Check that task is an iterable containing only -1, 0 or 1'''

        try:
            itertask = iter(task)
        except TypeError:
            return False
        else:
            return set(itertask) <= set((-1, 0, 1))

    def _task_is_complete(self):
        return len(self._task) == 0

    def _execute_task(self):
        step, self._task = self._task[0], self._task[1:]  # aka generalized pop

        self.step_pos += step
        if step == -1:
            # step back oneStep
            pass
        elif step == 1:
            # step forward oneStep
            pass


class RepeatedTimer(object):
    '''Class courtesy of MestreLion on StackOverflow
    See http://stackoverflow.com/a/13151299/5370002 for details
    '''

    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.start()
        self.function(*self.args, **self.kwargs)

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


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
