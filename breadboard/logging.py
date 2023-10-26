"""Logging"""

import time
import sys

from io import StringIO

LOGGING_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARN": 2,
    "ERROR": 3,
}

REV_LOGGING_LEVELS = {v: k for k, v in LOGGING_LEVELS.items()}

LOG_MSG_TEMPLATE = '{"timestamp": "%(time)s", "level": "%(level)s"%(custom_entries)s, "message": "%(message)s"}'  # TODO how to include message source? __file__?

# TODO: make alert class dynamic
HTML_LOG_MSG_TEMPLATE = '<div class="row"><div class="col"><div class="alert alert-primary text-wrap" role="alert"><pre><code>' + LOG_MSG_TEMPLATE + '</code></pre></div></div></div>'  # TODO how to include message source? __file__?


def _curry(func, **params):
    def __inner(*args, **kwargs):
        return func(*args, **kwargs, **params)

    return __inner


def _exception_to_str(e):
    """Convert en exception into a string message."""
    exception_message = StringIO()
    sys.print_exception(e, exception_message)
    return exception_message.getvalue()


def format_time_tuple(t):
    year, month, day, hour, minute, second = (
        str(v) if v > 2000 else str(v) if v >= 10 else f"0{v}" for v in t[:6]
    )
    return f"{year}-{month}-{day} {hour}:{minute}:{second}"


class Logger:
    """A logger.

    Args:
        serial_log: Whether or not to log to the serial console
        file_log: Whether or not to log to an API-accessible "file"
        level: The level below which logs are surpressed

    """

    def __init__(self, serial_log=True, file_log=True, level="DEBUG"):
        self.serial_log = serial_log
        self.file_log = file_log
        if self.file_log:
            self.log_buffer = StringIO()

        self._level = LOGGING_LEVELS[level]
        self.debug = _curry(self._print_log, requested_level=LOGGING_LEVELS["DEBUG"])
        self.info = _curry(self._print_log, requested_level=LOGGING_LEVELS["INFO"])
        self.warn = _curry(self._print_log, requested_level=LOGGING_LEVELS["WARN"])
        self.error = _curry(self._print_log, requested_level=LOGGING_LEVELS["ERROR"])

    @property
    def level(self):
        return self._level

    @level.setter
    def level(self, value):
        if value not in LOGGING_LEVELS:
            raise Exception(f"Unknown logging level: {value}")
        self._level = value

    def _print_log(self, message, *params, requested_level, **kwargs):
        if isinstance(message, Exception):
            message = _exception_to_str(message)
        else:
            message = message % params

        if kwargs:
            custom_entries = "".join(f', "{k}": "{str(v).replace('"', '\\"')}"' for k, v in kwargs.items())
        else:
            custom_entries = ""

        if requested_level >= self._level:
            for requested, dest, template in [
                (self.serial_log, sys.stdout, LOG_MSG_TEMPLATE),
                (self.file_log, self.log_buffer, HTML_LOG_MSG_TEMPLATE),
            ]:
                if requested:
                    dest.write(
                        template
                        % {
                            "time": format_time_tuple(time.localtime(time.time())),
                            "level": REV_LOGGING_LEVELS[requested_level].lower(),
                            "message": message.replace("\n", " "),
                            "custom_entries": custom_entries,
                        } + "\n"
                    )


logger = Logger()
