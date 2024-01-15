import sys

from modules.console import console
from modules.context import context
from modules.exceptions import PrettyException


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


def register_exception_hook():
    sys.excepthook = exception_hook
