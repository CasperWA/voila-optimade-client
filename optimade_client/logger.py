"""Logging to both file and widget"""
import logging
import os
from pathlib import Path
from typing import List
import urllib.parse
import warnings

import appdirs
import ipywidgets as ipw


LOG_DIR = Path(appdirs.user_log_dir("optimade-client", "CasperWA"))
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "optimade_client.log"


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
            "overflow": "hidden auto",  # "Internal" scrolling
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
            "name": "log",
            "output_type": "stream",
            "text": f"{formatted_record}\n",
        }
        self.out.outputs = (new_output,) + self.out.outputs

    def get_widget(self):
        """Return the IPyWidget"""
        return self.out


class ReportLogger(ipw.HTML):
    """The widget to go with the handler"""

    WRAPPED_LOGS = """<input type='hidden' id='{element_id}' value='{value}'></input>"""
    WRAPPED_VALUE = (  # Post-urlencoded
        "%3Cdetails%3E%0A++%3Csummary%3ELog+dump%3C%2Fsummary%3E%0A%0A++%60%60%60%0A{logs}++"
        "%60%60%60%0A%3C%2Fdetails%3E%0A%0A"
    )
    MAX_BYTES = 7400

    def __init__(self, value: str = None, **kwargs):
        self._element_id = "report_log"
        self._logs = []
        self._truncated = False
        super().__init__(self.clear_logs(), **kwargs)

    @staticmethod
    def freeze():
        """Disable widget"""
        LOGGER.debug("Freeze 'ReportLogger'.")

    @staticmethod
    def unfreeze():
        """Activate widget (in its current state)"""
        LOGGER.debug("Unfreeze 'ReportLogger'.")

    @staticmethod
    def reset():
        """Reset widget"""
        LOGGER.debug("Reset 'ReportLogger'.")

    def clear_logs(self) -> str:
        """Clear logs, i.e., input element's value attribute"""
        self._logs = []
        return self._update_logs()

    def _update_logs(self) -> str:
        """Wrap log messages, i.e., use self.wrapped_log to set self.value"""
        return self.WRAPPED_LOGS.format(
            value=self.WRAPPED_VALUE.format(logs="".join(self.logs)),
            element_id=self.element_id,
        )

    @staticmethod
    def _urlencode_string(string: str) -> str:
        """URL encode, while adding specific encoding as well

        Specific encoding:
        - GitHub wants to turn all spaces into '+'.
            This is actually already taken care of, since urlencode uses 'quote_plus'.
        """
        res = urllib.parse.urlencode({"value": string}, encoding="utf-8")
        return res[len("value=") :]

    def log(self, message: str):
        """Log a message, i.e., add it to the input element's value attribute"""
        # Remove any surrounding new-line invocations (so we can implement our own)
        while message.endswith("\n"):
            message = message[:-2]
        while message.startswith("\n"):
            message = message[2:]

        # Put all messages within the GitHub Markdown accordion
        message = self._urlencode_string(f"  {message}\n")

        # Truncate logs to not send a too long URI and receive a 414 response from GitHub
        note_truncation = self._urlencode_string("...")
        message_truncation = self._urlencode_string(f"  {note_truncation}\n")
        suggested_log = "".join(self.logs) + message
        while len(suggested_log) > self.MAX_BYTES:
            # NOTE: It is expected that the first log message will never be longer than MAX_BYTES
            if len(self.logs) == 1:
                # The single latest message is too large, cut it down
                new_line = "%0A"
                truncation_length = (
                    len(message_truncation) + len(note_truncation) + len(new_line)
                )
                message = (
                    f"{message[:self.MAX_BYTES - truncation_length]}{note_truncation}"
                    f"{new_line}"
                )
                break

            if not self._truncated:
                # Add a permanent "log" message to show the list of logs is incomplete
                self._truncated = True
                self.logs.insert(0, message_truncation)

            self.logs.pop(1)
            suggested_log = f"{''.join(self.logs)}{message}"

        self.logs.append(message)
        self.value = self._update_logs()

    @property
    def logs(self) -> List[str]:
        """Return list of currently saved log messages"""
        return self._logs

    @logs.setter
    def logs(self, _):  # pylint: disable=no-self-use
        """Do not allow adding logs this way"""
        msg = (
            "Will not change 'logs'. Logs should be added through the 'OPTIMADE_Client' logger, "
            "using the 'logging' module."
        )
        LOGGER.warning("Message: %r", msg)
        warnings.warn(msg)

    @property
    def element_id(self) -> str:
        """Return the input element's id"""
        return self._element_id

    @element_id.setter
    def element_id(self, _):
        """Do not allow changing the input element's id"""
        if self._element_id:
            msg = (
                "Can not set 'element_id', since it is already set <element_id="
                f"{self._element_id}>"
            )
            LOGGER.warning("Message: %r", msg)
            warnings.warn(msg)


class ReportLoggerHandler(logging.Handler):
    """Custom logging handler sending logs to an output widget
    Inspired by:
    https://ipywidgets.readthedocs.io/en/latest/examples/Output%20Widget.html#Integrating-output-widgets-with-the-logging-module
    """

    def __init__(self):
        super().__init__()
        self.out = ReportLogger()

    def emit(self, record: logging.LogRecord):
        """Overrule the same logging.Handler method"""
        formatted_record = self.format(record)
        self.out.log(formatted_record)

    def get_widget(self):
        """Return the IPyWidget"""
        return self.out


# Instantiate LOGGER
LOGGER = logging.getLogger("OPTIMADE_Client")
LOGGER.setLevel(logging.DEBUG)

# Save a file with all messages (DEBUG level)
FILE_HANDLER = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=1000000, backupCount=5
)
FILE_HANDLER.setLevel(logging.DEBUG)

# Write to Output widget (INFO level is default, overrideable with environment variable)
WIDGET_HANDLER = OutputLoggerHandler()
if os.environ.get("OPTIMADE_CLIENT_DEBUG", None) is None:
    # Default - INFO
    WIDGET_HANDLER.setLevel(logging.INFO)
else:
    # OPTIMADE_CLIENT_DEBUG set - DEBUG
    WIDGET_HANDLER.setLevel(logging.DEBUG)

# Write to HTML widget (DEBUG level - for bug reporting)
REPORT_HANDLER = ReportLoggerHandler()
REPORT_HANDLER.setLevel(logging.DEBUG)

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

REPORT_FORMATTER = logging.Formatter(  # Minimize and mimic FILE_FORMATTER
    "[%(levelname)s %(asctime)s %(filename)s:%(lineno)d] %(message)s", "%H:%M:%S"
)
REPORT_HANDLER.setFormatter(REPORT_FORMATTER)

# Finalize LOGGER
LOGGER.addHandler(WIDGET_HANDLER)
LOGGER.addHandler(FILE_HANDLER)
LOGGER.addHandler(REPORT_HANDLER)
