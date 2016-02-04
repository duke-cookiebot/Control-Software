'''
Created on Jan 18, 2016

@author: justinpalpant
'''    
import enum
import logging
from uuid import uuid1

class Actuator(object):
    '''
    Base class for all types of actuators
    
    This class exposes a set of public methods that an be called to use the
    actuator.  These methods will be identical for all actuators (although they
    will take different arguments)  It also defines some private methods that
    SHOULD or MUST be overridden in order to have a real, functioning actuator
    '''
    logger = logging.getLogger('Actuator')
    
    @enum.unique
    class State(enum.IntEnum):
        ready = 0
        executing = 1
        executing_blocked = 2
        dead = 3
    

    def __init__(self, identity=''):
        '''
        Constructor
        
        Prepares the actuator to receive commands and assigns its id
        '''
        self.state = Actuator.State.ready
        self.task = None
        self.id = identity if identity else str(uuid1())        
        
    def __str__(self):
        return ''
    
    def set_task(self, task, blocking=False):
        '''Public API for assigning a task to an actuator'''   
        
        if self.state is Actuator.State.dead:
            self.logger.error('Cannot set tasks on {0} because it is dead'.format(self.id))
            raise CommandError('Actuator is dead and cannot be commanded')
        
        if self.state is Actuator.State.executing_blocked:
            self.logger.warning('Cannot change task while executing a blocking task')
            raise CommandError('Task {0} is executing'.format(self.task))
        
        if not self._validate_task(task):
            self.logger.error('Invalid task provided to actuator {0}'.format(self.id))
            raise CommandError('Task {0} is not valid for actautor {1}'.format(task, self.id))
        
        self.task = task
        self._task_is_blocking = blocking
    
    def run_execution(self):
        '''Public API called repeatedly and frequently to update the state'''
        
        if self.state is Actuator.State.dead:
            self.logger.error('Cannot set tasks on {0} because it is dead'.format(self.id))
            raise ExecutionError('Actuator is dead and cannot be commanded')
                
        if self.task is not None and self.state is Actuator.State.ready:
            self.state = Actuator.State.executing_blocked if self._task_is_blocking else Actuator.State.executing
            
        if self.task is not None and self.state is Actuator.State.executing or Actuator.State.executing_blocked:
            if self._check_bounds():
                self.kill()
                raise ExecutionError('Bounds violated, actuator killed')
            
            if self._task_is_complete():
                self.state = Actuator.State.ready
                self.task = None
            else:
                try:
                    self._execute_task()
                    
                except ExecutionError as e:
                    self.logger.error('Unable to execute task')
                    raise e
                
        if self.task is None:
            self.logger.debug('Waiting for a task to be assigned')
            self.logger.debug('Actuator state is {0}'.format(self.state))
    
    def kill(self):
        '''Public API method - kill this actuator
        
        Prevents setting or executing tasks in the future.  Attempts to halt the
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
        
        return False
    
    def _execute_task(self):
        '''Private method to do external interfacing and actually send commands
        to the actuator
        
        Must be uniquely implemented by every subclass
        
        Void method - does not return anything
        
        Should raise ExecutionError if something horrid happens
        '''
        
        pass
     
        
class LinearActuator(Actuator):
    '''
    Classdocs
    '''
    
    logger = logging.getLogger('LinearActuator')
    
    def __init__(self, params):
        super(LinearActuator, self).__init__(params)
                   
        
class PlatformActuator(LinearActuator):
    '''
    classdocs
    '''
    
    logger = logging.getLogger('PlatformActuator')
    
    def __init__(self, params):
        '''
        Constructor
        '''
        
        super(PlatformActuator, self).__init__(params)
        
        
class NozzleActuator(LinearActuator):
    '''
    classdocs
    '''
    
    def __init__(self, params):
        '''
        Constructor
        '''
        
        super(NozzleActuator, self).__init__(params)
        
        
class MotorActuator(LinearActuator):
    '''
    This class will be used for each of the two linear actuators controlling
    the location of the nozzle
    
    It must implement set_task() to take both a desired location and a desired
    speed
    
    Like all LinearActuators, it must be initialized with a bounded domain and
    must stop if it reaches the edges of that domain or raise an exception if a
    command is given that is outside of that bound.  It should additionally have
    a maximum speed at which it can move, which should be public and accessible,
    and should raise an exception if a speed command is greater than that speed.
    
    Assigned: XY motion team, Mari and Carrina
    '''
    
    def __init__(self, params):
        '''
        Constructor
        '''
        
        super(MotorActuator, self).__init__(params)
        
    
        
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
