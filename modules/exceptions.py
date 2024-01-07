"""Custom exception handlers."""

from __future__ import annotations


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
