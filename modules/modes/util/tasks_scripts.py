from typing import Generator, Literal

from modules.context import context
from modules.debug import debug
from modules.tasks import get_global_script_context, task_is_active, get_task, is_waiting_for_input
from .sleep import wait_for_n_frames


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
def wait_for_yes_no_question(answer_to_give: Literal["Yes", "No"]) -> Generator:
    """
    Waits for a Yes/No question to pop up and answers it.
    :param answer_to_give: The answer to give. Must be 'Yes' or 'No' (capitalisation is important.)
    """
    if answer_to_give not in ("Yes", "No"):
        raise ValueError(
            f"The response to a Yes/No question needs to be 'Yes' or 'No'. Instead, '{answer_to_give}' was given."
        )

    # Most Yes/No questions in the game are handled through a dedicated task (`Task_YesNoMenu_HandleInput` or
    # `Task_HandleYesNoInput`), but in a few cases the game uses the 'Multi Choice' task with just 'Yes' and
    # 'No' as options. One example for that is the Pokémon Center confirmation question on FR/LG.
    #
    # There are some variants of that where apart from 'Yes' and 'No' there is also an 'Info' option.
    # We support those as well.
    #
    # The choices given can be identified by the 'multichoice ID', which is the 7th value in the multi choice
    # task's data.
    if context.rom.is_frlg:
        yes_no_task = "Task_YesNoMenu_HandleInput"
        multi_choice_task = "Task_MultichoiceMenu_HandleInput"
        multi_choice_ids = (0, 16, 18)
    else:
        yes_no_task = "Task_HandleYesNoInput"
        multi_choice_task = "Task_HandleMultichoiceInput"
        multi_choice_ids = (17, 20, 94)

    while True:
        if task_is_active(yes_no_task):
            active_task = yes_no_task
            break

        if task_is_active(multi_choice_task):
            task = get_task(multi_choice_task)
            print(task.data_value(7))
            if task.data_value(7) in multi_choice_ids:
                active_task = multi_choice_task
                break

        # On FR/LG, the choice selection dialogue will accept inputs _immediately_, i.e. even
        # before the task shows up in the task list. So if we just spam A/B as we usually do
        # in order to skip through the text dialogue, this would be considered a response to
        # the Yes/No question by the games.
        #
        # In order to prevent that, we wait for certain events that signify that the game is
        # waiting for an input in order to advance some dialogue.
        if is_waiting_for_input():
            context.emulator.press_button("A")
        yield

    if answer_to_give == "No":
        yield from wait_for_n_frames(4)
        context.emulator.press_button("Down")
        yield from wait_for_n_frames(2)

    yield from wait_until_task_is_not_active(active_task, "A")


def wait_for_multiple_choice_question(choice_index: int) -> Generator:
    task_name = "Task_MultichoiceMenu_HandleInput" if context.rom.is_frlg else "Task_HandleMultichoiceInput"
    while not task_is_active(task_name):
        # This is necessary because FR/LG will accept input to the multiple choice dialogue as soon
        # as the task starts. See comment in `wait_for_yes_no_question()` for more details.
        if is_waiting_for_input():
            context.emulator.press_button("A")
        yield

    if choice_index > 0:
        yield from wait_for_n_frames(4)
        for _ in range(choice_index):
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(2)

    yield from wait_until_task_is_not_active(task_name, "A")


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
