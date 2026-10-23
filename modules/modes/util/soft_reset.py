import random
from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.files import get_rng_state_history, save_rng_state_history
from modules.memory import (
    GameState,
    get_game_state,
    get_game_state_symbol,
    pack_uint32,
    read_symbol,
    unpack_uint32,
    write_symbol,
)
from modules.tasks import get_task
from .tasks_scripts import wait_for_task_to_start_and_finish
from .walking import wait_for_player_avatar_to_be_controllable


class _FrlgTitleScreenInputs:
    """
    Picks the buttons to press on FRLG's copyright screen, intro and title screen.

    The intro is skipped as soon as possible, because waiting there doesn't change
    the seed. On the title screen, it waits for a random number of frames, split
    randomly between the title animation and the 'Press Start' screen. The presses
    that skip something always use a different button than the previous frame, so
    the game sees them as new presses even right after another press.
    """

    # FR/LG seed their RNG with the number of CPU cycles between the title screen being
    # set up and the end of the fade after the title cry. Every frame spent on the title
    # screen in between gives a new range of seeds. Button presses only shift the seed
    # by a few cycles (about 60 possible seeds for a given number of frames.) Waiting
    # for a random 0 to 30 frames costs 15.7 frames per reset on average and gives about
    # 1,300 equally likely seeds instead of about 400.
    _MAX_TITLE_SCREEN_DELAY = 30

    # `tSceneNum` of `Task_TitleScreenMain`
    _TITLE_SCENE_RUN = 3
    _TITLE_SCENE_RESTART = 4
    _TITLE_SCENE_CRY = 5

    # Buttons that can be pressed without changing the course of the intro/title screen.
    # L and R are never pressed: on the title screen they open the help system.
    _HARMLESS_BUTTONS = ["A", "B", "Select", "Start", "Up", "Down", "Left", "Right"]
    _HARMLESS_BUTTONS_DURING_TITLE_ANIMATION = ["Select", "Up", "Down", "Left", "Right"]
    _HARMLESS_BUTTONS_DURING_PRESS_START = ["B", "Select", "Up", "Down", "Left", "Right"]

    def __init__(self):
        delay = random.randint(0, self._MAX_TITLE_SCREEN_DELAY)
        self._frames_before_skipping_animation = random.randint(0, delay)
        self._frames_before_pressing_start = delay - self._frames_before_skipping_animation
        self._last_button: str | None = None

    def press_next_button(self) -> None:
        button = self._choose_button()
        if button is not None:
            context.emulator.press_button(button)
        self._last_button = button

    def _choose_button(self) -> str | None:
        match get_game_state_symbol():
            case "CB2_INTRO":
                return self._new_press("A", "Start", "Select")
            case "CB2_TITLESCREENRUN":
                task = get_task("Task_TitleScreenMain")
                scene = task.data_value(0) if task is not None else None
                if scene is None or scene == self._TITLE_SCENE_RESTART:
                    return None
                elif scene < self._TITLE_SCENE_RUN:
                    if self._frames_before_skipping_animation > 0:
                        self._frames_before_skipping_animation -= 1
                        return self._mash(self._HARMLESS_BUTTONS_DURING_TITLE_ANIMATION)
                    return self._new_press("A", "B", "Start")
                elif scene == self._TITLE_SCENE_RUN:
                    if self._frames_before_pressing_start > 0:
                        self._frames_before_pressing_start -= 1
                        return self._mash(self._HARMLESS_BUTTONS_DURING_PRESS_START)
                    return self._new_press("Start", "A")
                elif scene == self._TITLE_SCENE_CRY:
                    return self._mash(self._HARMLESS_BUTTONS)
                return None
            case "CB2_INITMAINMENU":
                # Don't press anything, so that the main menu sees the next A press as a new one.
                return None
            case _:
                # Copyright screen and the frames between the screens.
                return self._mash(self._HARMLESS_BUTTONS)

    def _new_press(self, *buttons: str) -> str:
        return next(button for button in buttons if button != self._last_button)

    def _mash(self, buttons: list[str]) -> str:
        return random.choice(buttons)


@debug.track
def soft_reset() -> Generator:
    """
    Soft-resets the emulation. This only works if there is a save game, otherwise it will
    get stuck in the main menu.

    On FR/LG, this waits for a random number of frames on the title screen and presses
    random buttons there, so that the game ends up with a different RNG seed. R/S/E don't
    seed their RNG from the title screen timing, so there it just skips the title screen.
    """
    context.emulator.reset()
    yield

    frlg_title_screen_inputs = _FrlgTitleScreenInputs() if context.rom.is_frlg else None
    was_in_title_screen = False
    while True:
        match get_game_state():
            case GameState.TITLE_SCREEN:
                was_in_title_screen = True
                if frlg_title_screen_inputs is not None:
                    frlg_title_screen_inputs.press_next_button()
                else:
                    context.emulator.press_button("A")
            case GameState.MAIN_MENU:
                context.emulator.press_button("A")
            case GameState.QUEST_LOG:
                context.emulator.press_button("B")
            case GameState.OVERWORLD:
                if was_in_title_screen:
                    if context.rom.is_frlg:
                        while read_symbol("gQuestLogState") != b"\x00":
                            context.emulator.press_button("B")
                            yield
                        yield from wait_for_task_to_start_and_finish("Task_EndQuestLog", "B")
                    yield from wait_for_player_avatar_to_be_controllable()
                    return

        yield


def advance_rng_sequence(steps: int = 1) -> int:
    """
    Sets the game's RNG to the value it would have after `steps` more calls to `Random()`,
    without emulating any frames. Most of the time the RNG advances once per frame, so this
    can be used to skip waiting if the `random_soft_reset_rng` cheat is enabled.

    :param steps: Number of RNG advances to skip.
    :return: The new RNG value.
    """
    rng_value = unpack_uint32(read_symbol("gRngValue"))
    for _ in range(steps):
        rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
    write_symbol("gRngValue", pack_uint32(rng_value))
    return rng_value


@debug.track
def wait_for_unique_rng_value() -> Generator:
    """
    Wait until the RNG value is unique. This is faster if the `random_soft_reset_rng`
    is enabled.
    """
    rng_history = get_rng_state_history()
    rng_value = unpack_uint32(read_symbol("gRngValue"))

    context.message = "Waiting for a unique frame before continuing..."
    while rng_value in rng_history:
        if context.config.cheats.random_soft_reset_rng:
            rng_value = advance_rng_sequence()
        else:
            rng_value = unpack_uint32(read_symbol("gRngValue"))
            yield
    context.message = ""

    rng_history.add(rng_value)
    save_rng_state_history(rng_history)
