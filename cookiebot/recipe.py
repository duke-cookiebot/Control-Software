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
        duke_d = 'icing_patterns/duke_d12.txt'

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
