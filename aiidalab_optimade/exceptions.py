# -*- coding: utf-8 -*-

class ApiVersionError(Exception):
    """ API Version Error

    The API version does not have the correct semantic.
    The API version cannot be recognized.
    """
    pass

class InputError(Exception):
    """ Input Error

    Base input error exception.
    Wrong input to a method.
    """
    pass

class DisplayInputError(InputError):
    """ Display Input Error

    The input to display method cannot be used.
    If 'all' is True, 'part' must be None.
    """
    pass
