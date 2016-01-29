# Control-Software
All Python and other software needed to control the CookieBot


# General Class Structure

- Controller

- Stage
	- IcingStage

- Actuator
	- LinearActuator
		- Motor
		- Platform
		- Nozzle
	- DigitalActuator

- Recipe

- Sensors


# Class Descriptions
## CookieGUI
The primary class for handling user interaction with the device.  The CookieGUI is contained in the gui package, not the cookiebot package, and the only external it needs to implement is IP messaging with the controller.

## Controller
Each instance should have one controller which handles all control of all stages and modules, regardless of it there is one stage or all four.  It also handles the communication with externals like a webservice (not implemented in this prototype.  The controller will have several Stages and will handle interaction between them.  It will take a recipe (it may have several at a time, in a queue) and commit the recipe to the first of its stages.  It then waits for some sort of signal from that stage - either that the stage is done, or that something is wrong.  If the stage finishes correctly, it gives the recipe to the next stage and activates that stage.  Etc. etc. until all stages have finished or one stages has errored out. 

Coincidentally, it would be totally reasonable for the controller to be operated on a remote server.  But we'll put it on a Pi.  Controller will require some sort of IP communicating ability.
## Stage
A stage is the highest-level class responsible for control of a single physical operation.  Each stage should probably be run on its own Pi.  A stage has actuators and sensors, listens for commands from the Controller that are addressed to the stage, and communicates with the Controller when it needs to.  But the Stage handles all the operations needed to complete a recipe.  A stage receives a recipe from the controller, figures out what it will need to do to complete that recipe (assuming all preceding stages completed correctly) and waits for the GO signal from the controller to start.  Stages will also require some sort of IP communication ability.

### IcingStage(Stage)
Subclass stage that handles all processes for icing a set of baked cookies.

## Actuator
Actuator is an abstract superclass for anything that moves anything in the physical world.  Actuators handle their own control and expose a simple, uniform API to the Stage that owns them.
### LinearActuator(Actuator)
 A subclass of actuators that only moves along one axis.  Important features of all linear actuators will be a bounded domain and the ability to  move to a set location along their axis.  
#### Motor(LinearActuator)
Subclass of linear actuator for moving the nozzle.  Should provide the ability to not only move to a location, but to control speed.
#### PlatformActuator(LinearActuator)
Subclass of linear actuator for lifting or lowering the platform - only needs to provide position control, does not need to implement speed control
#### NozzleActuator(LinearActuator)
This subclass of linear actuator for actuating the icing nozzle.  Only needs to provide control over the rate of icing deposition, and even that might only need to be binary (on/off).
## Sensor
Sensor is a superclass that should be inherited by anything that collects data but does not influence the physical world.  We might actually not have any of these in the single-stage prototype, not sure yet.
## Recipe
A complete description of what is to be produced by the end of the process.  The recipe is a high-level description, it does not have specific instructions for, say, the IcingStage.  Rather, Recipe defines "two cookies with this pattern, two with this pattern, etc. etc." and each stage must take that information and determine the appropriate steps for itself.
