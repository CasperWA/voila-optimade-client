"""Logging to both file and widget"""
import logging
import os

import ipywidgets as ipw

# This coloring formatter is inspired heavily from:
# https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# ANSI escape sequences.
# The color is set with 30 plus the number of the color above.
# The addition is done in the Formatter.
# See https://en.wikipedia.org/wiki/ANSI_escape_code#SGR_parameters for more info.
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[%dm"  # Can instead be "\033[<FOREGROUND (+30)>;<BACKGROUND (+40)>m"
BOLD_SEQ = "\033[1m"

COLORS = {
    "CRITICAL": YELLOW,
    "ERROR": RED,
    "WARNING": MAGENTA,
    "INFO": GREEN,
    "DEBUG": BLUE,
    "NOTSET": BLACK,
}


def apply_correct_formatter_sequences(message: str):
    """Replace human-readable bash-like variables with correct sequences"""
    mapping = {
        "$RESET": RESET_SEQ,
        "$COLOR": COLOR_SEQ,
        "$BOLD": BOLD_SEQ,
    }
    for variable in mapping:
        message = message.replace(variable, mapping[variable])
    return message


class ColoredFormatter(logging.Formatter):
    """Formatter used for widget outputs"""

    def __init__(self, fmt=None, datefmt=None, style="%"):
        if fmt and isinstance(fmt, str):
            fmt = apply_correct_formatter_sequences(fmt)
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)

    def format(self, record: logging.LogRecord):
        """Overrule the same logging.Formatter method

        In order to avoid changing the record, for other logger instances,
        the record is restored to its original state before returning.
        """
        levelname = record.levelname
        if levelname in COLORS:
            levelname_color = (
                COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            )
            record.levelname = levelname_color

        colored_record = super().format(record=record)
        record.levelname = levelname

        return colored_record


class OutputLogger(ipw.Output):
    """The widget to go with the handler"""

    def __init__(self, **kwargs):
        layout = {
            "width": "auto",
            "min_height": "160px",
            "max_height": "240px",
            "border": "1px solid black",
            "overflow_y": "auto",  # "Internal" scrolling
        }
        super().__init__(layout=layout)

    def freeze(self):
        """Disable widget"""

    def unfreeze(self):
        """Activate widget (in its current state)"""

    def reset(self):
        """Reset widget"""
        self.clear_output()


class OutputLoggerHandler(logging.Handler):
    """Custom logging handler sending logs to an output widget
    Inspired by:
    https://ipywidgets.readthedocs.io/en/latest/examples/Output%20Widget.html#Integrating-output-widgets-with-the-logging-module
    """

    def __init__(self):
        super().__init__()
        self.out = OutputLogger()

    def emit(self, record: logging.LogRecord):
        """Overrule the same logging.Handler method"""
        formatted_record = self.format(record)
        new_output = {
            "name": "stdout",
            "output_type": "stream",
            "text": f"{formatted_record}\n",
        }
        self.out.outputs = (new_output,) + self.out.outputs

    def get_widget(self):
        """Return the IPyWidget"""
        return self.out


# Instantiate LOGGER
LOGGER = logging.getLogger("OPTIMADE_Client")
LOGGER.setLevel(logging.DEBUG)

# Save a file with all messages (DEBUG level)
FILE_HANDLER = logging.FileHandler("optimade_client.log")
FILE_HANDLER.setLevel(logging.DEBUG)

# Write to Output widget (INFO level is default, overrideable with environment variable)
WIDGET_HANDLER = OutputLoggerHandler()
if os.environ.get("OPTIMADE_CLIENT_DEBUG", None) is None:
    # Default - INFO
    WIDGET_HANDLER.setLevel(logging.INFO)
else:
    # OPTIMADE_CLIENT_DEBUG set - DEBUG
    WIDGET_HANDLER.setLevel(logging.DEBUG)

# Set formatters
FILE_FORMATTER = logging.Formatter(
    "[%(levelname)-8s %(asctime)s %(filename)s:%(lineno)d] %(message)s",
    "%d-%m-%Y %H:%M:%S",
)
FILE_HANDLER.setFormatter(FILE_FORMATTER)

WIDGET_FORMATTER = ColoredFormatter(
    "$BOLD[%(asctime)s %(levelname)-5s]$RESET %(message)s", "%H:%M:%S"
)
WIDGET_HANDLER.setFormatter(WIDGET_FORMATTER)

# Finalize LOGGER
LOGGER.addHandler(WIDGET_HANDLER)
LOGGER.addHandler(FILE_HANDLER)
