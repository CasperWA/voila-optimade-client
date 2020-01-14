class ApiVersionError(Exception):
    """ API Version Error
    The API version does not have the correct semantic.
    The API version cannot be recognized.
    """


class NonExistent(Exception):
    """ Non Existent
    An entity does not exist, e.g. a URL location.
    """


class InputError(Exception):
    """ Input Error
    Base input error exception.
    Wrong input to a method.
    """


class DisplayInputError(InputError):
    """ Display Input Error
    The input to display method cannot be used.
    If 'all' is True, 'part' must be None.
    """
