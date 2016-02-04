'''
Created on Jan 18, 2016

@author: justinpalpant
'''    
import enum
import logging
from uuid import uuid1

class Actuator(object):
    '''
    classdocs
    '''
    logger = logging.getLogger('Actuator')
    
    @enum.unique
    class State(enum.IntEnum):
        ready = 0
        executing = 1
        executing_blocked = 2
    

    def __init__(self, id=''):
        '''
        Constructor
        '''
        self.state = Actuator.State.ready
        self.task = None
        self.id = id if id else str(uuid1())
        
        
    def __str__(self):
        return ''
    
    def set_task(self, task, blocking=False):
        '''Public API for assigning a task to an actuator'''
        
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
        
        if self.task is not None and self.state is Actuator.State.ready:
            self.state = Actuator.State.executing_blocked if self._task_is_blocking else Actuator.State.executing
            
        if self.task is not None and self.state is not Actuator.State.ready:
            if self._task_is_complete():
                self.state = Actuator.State.ready 
            else:
                try:
                    self._execute_task()
                    
                except ExecutionError as e:
                    self.logger.error('Unable to execute task')
                    raise e
        
        
    
    
    def _validate_task(self, task):
        '''Private method for determining if a task if valid for an actuator
        
        Must be implemented uniquely by all subclasses
        
        Returns True if the task will be okay, False otherwise
        '''
        
        raise NotImplementedError  
    
    def _task_is_complete(self):
        '''Private method for checking if the assigned task (self.task) is done
        
        Must be implemented uniquely by all subclasses
        
        Should return True if the task is done enough to stop, else False
        '''
        
        raise NotImplementedError
    
    def _execute_task(self):
        '''Private method to do external interfacing and actually send commands
        to the actuator
        
        Must be uniquely implemented by every subclass
        
        Void method - does not return anything
        
        Should raise ExecutionError if something horrid happens
        '''
        
        raise NotImplementedError
     
        
class LinearActuator(Actuator):
    '''
    Classdocs
    '''
    
    def __init__(self, params):
        super(LinearActuator, self).__init__(params)
                   
        
class PlatformActuator(LinearActuator):
    '''
    classdocs
    '''
    
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
