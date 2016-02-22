'''
Created on Jan 18, 2016

@author: justinpalpant
'''


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


class IcingStage(Stage):
    '''
    classdocs
    '''

    def __init__(self):
        '''
        constructor
        '''

        super(IcingStage, self).__init__()

        # Set up actuators

        # Set up assorted parameters
        self.x_cookie_shift = 10
        self.y_cookie_shift = 10

    def parse_recipe(self, recipe):
        reset_command = {'dest': (0, 0), 'extrude': False}
        commands_list = []

        for cookie_pos in recipe:
            commands = self.icing_file_to_commands(recipe[cookie_pos]['icing'])
            commands = self.offset_commands(commands, cookie_pos)

            commands_list.append(reset_command)
            commands_list.extend(commands)
            
        return commands_list

    def icing_file_to_commands(self, filename):
        '''Load an icing file and return a list of commands

        Arguments:
            filename - an icing spec file

        Returns:
            A list of dictionaries, each defining one movement
            e.g. [{'dest':(0,1), 'extrude':True}, ]

        Assigned to Cynthia
        '''

        return []

    def offset_commands(self, commands, pos):
        '''Take a set of command dictionaries and shift the positions based on
        which cookie slot the cookie belongs to

        Arguments:
            commands - a list of command dictionaries, as returned by
                icing_file_to_commands
            pos - a cookie position, as returned by a recipe

        Returns:
            An updated list of command dictionaries
        '''

        new_commands = []

        for c in commands:
            old_dest = c['dest']

            new_end = self.shift_point_by_pos(old_dest, pos)

            new_c = {'dest': new_end, 'extrude': c['extrude']}
            new_commands.append(new_c)

        return new_commands

    def shift_point_by_pos(self, coord, cookiepos):
        '''Shift a single coordinate based on the cookiepos it belongs to'''

        x = coord[0] + cookiepos[0] * self.x_cookie_spacing
        y = coord[1] + cookiepos[1] * self.y_cookie_spacing

        return (x, y)
