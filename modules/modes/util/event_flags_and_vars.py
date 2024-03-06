from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.memory import get_event_flag, get_event_var


@debug.track
def wait_until_event_flag_is_true(flag_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an event flag in is set to true.
    :param flag_name: Name of the flag to check (see possible values in `modules/data/event_flags/*.txt`)
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while not get_event_flag(flag_name):
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_until_event_flag_is_false(flag_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an event flag in is set to false.
    :param flag_name: Name of the flag to check (see possible values in `modules/data/event_flags/*.txt`)
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while get_event_flag(flag_name):
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_until_event_var_equals(var_name: str, expected_value: int, button_to_press: str | None = None) -> Generator:
    """
    Wait until an event var has a particular value.
    :param var_name: Name of the event variable to check (see possible values in `modules/data/event_vars/*.txt`)
    :param expected_value: Value that the event var should have before returning.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while get_event_var(var_name) != expected_value:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_until_event_var_not_equals(var_name: str, avoid_value: int, button_to_press: str | None = None) -> Generator:
    """
    Wait until an event var does NOT have a particular value.
    :param var_name: Name of the event variable to check (see possible values in `modules/data/event_vars/*.txt`)
    :param avoid_value: Value that the event var should not have when returning.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while get_event_var(var_name) == avoid_value:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield
