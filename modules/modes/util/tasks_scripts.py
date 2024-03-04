from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.tasks import get_global_script_context, task_is_active


@debug.track
def wait_until_task_is_active(function_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an in-game task starts, optionally mashing a particular button
    the entire time.
    :param function_name: Function name of the task to wait for.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while not task_is_active(function_name):
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_until_task_is_not_active(function_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an in-game task finishes (i.e. is no longer part of the task list, or
    has its 'active' bit set to zero.)
    If the task is not running to begin with, this will return immediately.
    :param function_name: Function name of the task to wait for.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while task_is_active(function_name):
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_for_task_to_start_and_finish(function_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an in-game task starts (if it is not yet running) and finishes (i.e.
    is no longer part of the task list, or has its 'active' bit set to zero.)
    :param function_name: Function name of the task to wait for.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    yield from wait_until_task_is_active(function_name, button_to_press)
    yield from wait_until_task_is_not_active(function_name, button_to_press)


@debug.track
def wait_until_script_is_active(function_name: str, button_to_press: str | None = None) -> Generator:
    while not get_global_script_context().is_active or function_name not in get_global_script_context().stack:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_until_script_is_no_longer_active(function_name: str, button_to_press: str | None = None) -> Generator:
    while get_global_script_context().is_active and function_name in get_global_script_context().stack:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_for_script_to_start_and_finish(function_name: str, button_to_press: str | None = None) -> Generator:
    yield from wait_until_script_is_active(function_name, button_to_press)
    yield from wait_until_script_is_no_longer_active(function_name, button_to_press)


@debug.track
def wait_for_no_script_to_run(button_to_press: str | None = None) -> Generator:
    while get_global_script_context().is_active:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield
