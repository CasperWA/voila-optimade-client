from typing import Any


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


class NotOkResponse(Exception):
    """Did not receive a `200 OK` response"""


class ParserError(Exception):
    """Error during FilterInputParser parsing"""

    def __init__(self, field: str = None, value: Any = None, msg: str = None):
        self.field = field if field is not None else "General"
        self.value = value if value is not None else ""
        self.msg = msg if msg is not None else "A general error occured during parsing."
        super().__init__(
            f"Field: {self.field}, Value: {self.value}, Message: {self.msg}"
        )
