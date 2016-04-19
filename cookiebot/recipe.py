'''
Created on Jan 18, 2016

@author: justinpalpant
'''

import enum

class RecipeError(Exception):
    pass


class Recipe(object):
    '''
    Recipe is a small class that holds the information necessary to specify
    a set of cookies to all possible stages.

    To that end, it must contain all information about the cookie for each
    possible location.

    However, this information will be fairly simple - the processing happens in
    each stage to convert the Recipe to real instructions
    '''
    @enum.unique
    class IcingType(enum.Enum):
        square = 'icing_patterns/square.txt'
        duke_fill = 'icing_patterns/duke_d12_fill.txt'
        d_outline = 'icing_patterns/duke_d12_outline.txt'
        u_outline = 'icing_patterns/duke_u12_outline.txt'
        k_outline = 'icing_patterns/duke_k12_outline.txt'
        e_outline = 'icing_patterns/duke_e12_outline.txt'
        maze = 'icing_patterns/maze.txt'
        spiral_square = 'icing_patterns/spiral_square.txt'
        blue_devil = 'icing_patterns/blue_devil.txt'

    class IcingImage(enum.Enum):
        square = 'icing_images/square.jpg'
        duke_fill = 'icing_images/duke_d12_fill.jpg'
        d_outline = 'icing_images/duke_d12_outline.jpg'
        u_outline = 'icing_images/duke_u12_outline.jpg'
        k_outline = 'icing_images/duke_k12_outline.jpg'
        e_outline = 'icing_images/duke_e12_outline.jpg'
        maze = 'icing_images/maze.jpg'
        spiral_square = 'icing_images/spiral_square.jpg'
        blue_devil = 'icing_images/blue_devil.jpg' 

    def __init__(self):
        self.cookies = {}

    def add_cookie(self, cookiespec, pos=(0, 0)):
        '''Adds cookie to this recipe's cookie dictionary

        If a cookie already exists for that position, the old cookie is
        overwritten

        Arguments:
            cookiespec: a dictionary of all the information needed to define
                a cookie.  For now, this dictionary will have one entry, and
                it will map 'icing' to one of Recipe.IcingType
                e.g.: cookiespec = {'icing': Recipe.IcingType.square}
                The above is a valid cookiespec for an icing-only cookiebot
        '''

        self.cookies[pos] = cookiespec
