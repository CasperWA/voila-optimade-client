from typing import Any, List, Union, Tuple, Sequence

from optimade.models import Resource

from optimade_client.logger import LOGGER


class OptimadeClientError(Exception):
    """Top-most exception class for OPTIMADE Client"""

    def __init__(self, *args: Tuple[Any]):
        LOGGER.error(
            "%s raised.\nError message: %s\nAbout this exception: %s",
            args[0].__class__.__name__
            if args and isinstance(args[0], Exception)
            else self.__class__.__name__,
            str(args[0]) if args else "",
            args[0].__doc__
            if args and isinstance(args[0], Exception)
            else self.__doc__,
        )
        super().__init__(*args)


class ApiVersionError(OptimadeClientError):
    """API Version Error
    The API version does not have the correct semantic.
    The API version cannot be recognized.
    """


class NonExistent(OptimadeClientError):
    """Non Existent
    An entity does not exist, e.g. a URL location.
    """


class InputError(OptimadeClientError):
    """Input Error
    Base input error exception.
    Wrong input to a method.
    """


class DisplayInputError(InputError):
    """Display Input Error
    The input to display method cannot be used.
    If 'all' is True, 'part' must be None.
    """


class NotOkResponse(OptimadeClientError):
    """Did not receive a `200 OK` response"""


class OptimadeToolsError(OptimadeClientError):
    """Base error related to `optimade-python-tools` (`optimade` package)"""


class AdaptersError(OptimadeToolsError):
    """Base error related to `optimade.adapters` module"""


class WrongPymatgenType(AdaptersError):
    """Wrong `pymatgen` type, either `Structure` or `Molecule` was needed instead"""


class ParserError(OptimadeClientError):
    """Error during FilterInputParser parsing"""

    def __init__(
        self,
        msg: str = None,
        field: str = None,
        value: Any = None,
        extras: Union[Sequence[Tuple[str, Any]], Tuple[str, Any]] = None,
    ):
        self.field = field if field is not None else "General (no field given)"
        self.value = value if value is not None else ""
        self.extras = extras if extras is not None else []
        self.msg = msg if msg is not None else "A general error occured during parsing."

        super().__init__(
            f"""
{self.__class__.__name__}
  Message: {self.msg}
  Field: {self.field!r}, Value: {self.value!r}
  Extras: {self.extras!r}"""
        )


class ImplementationError(OptimadeClientError):
    """Base error related to the current OPTIMADE implementation being handled/queried"""


class BadResource(ImplementationError):
    """Resource does not fulfill requirements from supported version of the OPTIMADE API spec"""

    def __init__(  # pylint: disable=too-many-arguments
        self, resource: Resource, msg: str = None, fields: Union[List[str], str] = None
    ):
        self.resource = resource
        self.fields = fields if fields is not None else []
        self.msg = (
            msg
            if msg is not None
            else (
                "A bad resource broke my flow: "
                f"<id: {self.resource.id}, type: {self.resource.type}>"
            )
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

        fields_msg = "\n".join(
            [
                f"    Field: {field!r}, Value: {value!r}"
                for field, value in zip(self.fields, self.values)
            ]
        )
        super().__init__(
            f"""
{self.__class__.__name__}
  <id: {self.resource.id!r}, type: {self.resource.type!r}>
  Message: {self.msg}
{fields_msg}"""
        )


class QueryError(ImplementationError):
    """Error while querying specific implementation (or provider)"""

    def __init__(self, msg: str = None, remove_target: bool = False):
        msg = msg if msg is not None else ""
        self.remove_target = remove_target

        super().__init__(
            f"""
{self.__class__.__name__}
  Message: {msg}
  Remove target: {self.remove_target!r}"""
        )
