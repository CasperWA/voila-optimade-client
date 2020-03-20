from typing import Any, List, Union

from optimade.models import Resource


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
            "ParserError\n"
            f"  Field: {self.field}, Value: {self.value}, Message: {self.msg}"
        )


class ImplementationError(Exception):
    """Base error related to the current OPTIMADE implementation being handled/queried"""


class BadResource(ImplementationError):
    """Resource does not fulfill requirements from supported version of the OPTIMADE API spec"""

    def __init__(  # pylint: disable=too-many-arguments
        self, resource: Resource, fields: Union[List[str], str] = None, msg: str = None,
    ):
        self.resource = resource
        self.fields = fields if fields is not None else []
        self.msg = (
            msg
            if msg is not None
            else f"A bad resource broke my flow: <id: {self.resource.id}, type: {self.resource.type}>"
        )

        if not isinstance(self.fields, list):
            self.fields = [self.fields]

        self.values = []
        for field in self.fields:
            value = getattr(self.resource, field, None)

            if value is None:
                value = getattr(self.resource.attributes, field, None)

            if value is None:
                # Cannot find value for field
                value = f"<Cannot be retrieved based on given field: {field}>"

            self.values.append(value)

        super().__init__(
            f"BadResource <id: {self.resource.id}, type: {self.resource.type}>\n"
            f"Message: {self.msg}\n"
            f"\n".join(
                [
                    f"  Field: {field}, Value: {value}"
                    for field, value in zip(self.fields, self.values)
                ]
            )
        )
