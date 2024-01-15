"""Custom exception handlers."""

from __future__ import annotations

import sys

from modules.console import console
from modules.context import context


class PrettyException(Exception):
    """Base class for all exceptions with rich print methods."""

    exit_code: int | None = 1
    message_template: str = "{}"
    message_color = "[bold red]"
    recommendation: str = ""
    recommendation_color = "[bold yellow]"

    def bare_message(self) -> PrettyException:
        """Create an exception to raise without pretty formatting."""
        message = self.message_template.format(self.args)
        message = f"{message}\n{self.recommendation}"
        return PrettyException(message)


class PrettyValueError(PrettyException):
    """Exception to print a rich message whenever a ValueError would be raised."""


class CriticalDirectoryMissing(PrettyException):
    """Exception for whenever a core file is missing."""

    message_template = "Could not load {}, the directory does not exist or is not readable."
    recommendation = "Make sure the directory exists and the user has read access."


class CriticalFileMissing(PrettyException):
    """Exception for whenever a core file is missing."""

    message_template = "Could not load {}, file does not exist."
    recommendation = "Please re-download the program or restore the missing file."


class InvalidConfigData(PrettyException):
    """Exception for whenever config file validation fails."""

    message_template = "Config file {} is invalid!"
    recommendation = "Please re-download the program or restore/amend the file contents."


def exception_hook(exc_type: type[Exception], exc_instance: Exception, traceback) -> None:
    """General handler for exceptions to remove tracebacks and highlight messages if debug is off.

    :param exc_type: Base Exception type, kept for parity with the overridden hook.
    :param exc_instance: Instanced exception object being raised.
    :param traceback: Traceback object, kept for parity with the overridden hook.
    """
    if not isinstance(exc_instance, PrettyException):
        raise exc_instance
    if context.debug:
        raise exc_instance.bare_message()
    message = exc_instance.message_template.format(*exc_instance.args)
    message = f"{exc_instance.message_color}{message}[/]"
    if exc_instance.recommendation:
        recommendation = f"{exc_instance.recommendation_color}{exc_instance.recommendation}[/]"
        message = f"{message}\n{recommendation}"
    console.print(message)
    exit_code = exc_instance.exit_code
    if exit_code is not None:
        sys.exit(exit_code)


sys.excepthook = exception_hook
