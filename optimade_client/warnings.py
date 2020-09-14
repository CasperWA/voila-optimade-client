from typing import Tuple, Any

from optimade_client.logger import LOGGER


class OptimadeClientWarning(Warning):
    """Top-most warning class for OPTIMADE Client"""

    def __init__(self, *args: Tuple[Any]):
        LOGGER.warning(
            "%s warned.\nWarning message: %s\nAbout this warning: %s",
            args[0].__class__.__name__
            if args and isinstance(args[0], Exception)
            else self.__class__.__name__,
            str(args[0]) if args else "",
            args[0].__doc__
            if args and isinstance(args[0], Exception)
            else self.__doc__,
        )
        super().__init__(*args)
