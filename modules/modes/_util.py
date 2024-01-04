"""
This file contains helper functions that can be used by bot modes to handle common tasks.

The functions inhere are all Generator functions and can be called from within bot modes
with the `yield from` keyword. This keyword hands over control to another Generator
function until it finishes.

For example: `yield from utils.navigate_to((3, 3))`
"""

import random
from typing import Generator

from modules.context import context
from modules.files import get_rng_state_history, save_rng_state_history
from modules.memory import (
    read_symbol,
    write_symbol,
    pack_uint32,
    unpack_uint32,
    get_game_state,
    GameState,
    get_event_flag,
)
from modules.player import get_player, get_player_avatar, TileTransitionState, RunningState
from modules.tasks import task_is_active


def navigate_to(destination_coordinates: tuple[int, int]) -> Generator:
    """
    Moves the player to a set of coordinates on the same map. Does absolutely no
    collision checking and _will_ get stuck.
    :param destination_coordinates: Tuple (x, y) of map-local coordinates of the destination
    """

    if get_game_state() != GameState.OVERWORLD:
        return

    while True:
        avatar = get_player_avatar()
        if avatar.local_coordinates == destination_coordinates:
            return

        if avatar.tile_transition_state != TileTransitionState.TRANSITIONING:
            if destination_coordinates[0] < avatar.local_coordinates[0]:
                context.emulator.press_button("Left")
            elif destination_coordinates[0] > avatar.local_coordinates[0]:
                context.emulator.press_button("Right")
            elif destination_coordinates[1] < avatar.local_coordinates[1]:
                context.emulator.press_button("Up")
            elif destination_coordinates[1] > avatar.local_coordinates[1]:
                context.emulator.press_button("Down")

        yield


def ensure_facing_direction(facing_direction: str) -> Generator:
    """
    If the player avatar is not already facing a certain direction this will make it turn
    around, so that afterwards it definitely faces the desired direction.
    :param facing_direction: One of "Up", "Down", "Left", or "Right"
    """
    while True:
        avatar = get_player_avatar()
        if avatar.facing_direction == facing_direction:
            return

        if (
            avatar.tile_transition_state == TileTransitionState.NOT_MOVING
            and avatar.running_state == RunningState.NOT_MOVING
        ):
            context.emulator.press_button(facing_direction)

        yield


def soft_reset(mash_random_keys: bool = True) -> Generator:
    """
    Soft-resets the emulation. This only works if there is a save game, otherwise it will
    get stuck in the main menu.
    :param mash_random_keys: Whether to press random keys while on the title screen, which
                             will advance the RNG value and so result in unique RNG values
                             faster (on FRLG.)
    """
    context.emulator.reset()
    yield

    while True:
        match get_game_state():
            case GameState.TITLE_SCREEN:
                if mash_random_keys:
                    context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))
            case GameState.MAIN_MENU:
                context.emulator.press_button("A")
            case GameState.QUEST_LOG:
                context.emulator.press_button("B")
            case GameState.OVERWORLD:
                if context.rom.is_frlg:
                    while read_symbol("gQuestLogState") != b"\x00":
                        context.emulator.press_button("B")
                        yield
                    yield from wait_until_task_is_active("Task_EndQuestLog", "B")
                    yield from wait_until_task_is_no_longer_active("Task_EndQuestLog", "B")
                return

        yield


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
            rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
            write_symbol("gRngValue", pack_uint32(rng_value))
        else:
            rng_value = unpack_uint32(read_symbol("gRngValue"))
            yield
    context.message = ""

    rng_history.append(rng_value)
    save_rng_state_history(rng_history)


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


def wait_until_task_is_no_longer_active(function_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an in-game task finishes (i.e. is no longer part of the task list, or
    has its 'active' bit set to zero.)
    :param function_name: Function name of the task to wait for.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    while task_is_active(function_name):
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


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


_guaranteed_shiny_rng_seed: str | None = None


def set_guaranteed_shiny_rng_seed() -> None:
    """
    This can be used for testing purposes, and if used in the frame before an encounter
    it will seed the RNG in a way that guarantees a shiny for the current player.
    """

    global _guaranteed_shiny_rng_seed
    if _guaranteed_shiny_rng_seed is None:
        player = get_player()
        while _guaranteed_shiny_rng_seed is None:
            seed = random.randint(0, 0xFFFF_FFFF)

            rng_value = seed
            rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
            rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
            personality_value_upper = rng_value >> 16
            rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
            personality_value_lower = rng_value >> 16

            if player.trainer_id ^ player.secret_id ^ personality_value_upper ^ personality_value_lower < 8:
                _guaranteed_shiny_rng_seed = pack_uint32(seed)

    write_symbol("gRngValue", _guaranteed_shiny_rng_seed)
