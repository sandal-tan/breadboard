"""Logging"""

import time

from io import StringIO

LOGGING_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARN": 2,
    "ERROR": 3,
}

REV_LOGGING_LEVELS = {v: k for k, v in LOGGING_LEVELS.items()}

LOG_MSG_TEMPLATE = "[%(level)s - %(time)s] %(message)s"


def _curry(func, **params):
    def __inner(*args, **kwargs):
        return func(*args, **kwargs, **params)

    return __inner


class Logger:
    """A logger.

    Args:
        serial_log: Whether or not to log to the serial console
        file_log: Whether or not to log to an API-accessible "file"
        level: The level below which logs are surpressed

    """

    def __init__(self, serial_log=True, file_log=True, level="INFO"):
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

    def _print_log(self, message, *params, requested_level):
        message = message % params
        if requested_level >= self._level:
            message = LOG_MSG_TEMPLATE % {
                "time": time.time(),
                "level": requested_level,
                "message": message,
            }

            if self.serial_log:
                print(message)

            if self.file_log:
                self.log_buffer.write(message + "\n")

    def exception(self, e):
        self.error(e)  # TODO get nice text or stacktrace of exception
