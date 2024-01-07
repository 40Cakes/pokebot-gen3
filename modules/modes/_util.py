"""
This file contains helper functions that can be used by bot modes to handle common tasks.

The functions inhere are all Generator functions and can be called from within bot modes
with the `yield from` keyword. This keyword hands over control to another Generator
function until it finishes.

For example: `yield from utils.navigate_to((3, 3))`
"""

import queue
import random
from typing import Generator

from modules.context import context
from modules.files import get_rng_state_history, save_rng_state_history
from modules.map import get_map_objects, get_map_all_tiles
from modules.memory import (
    read_symbol,
    write_symbol,
    pack_uint32,
    unpack_uint32,
    get_game_state,
    GameState,
    get_event_flag,
    get_event_flag_by_number,
)
from modules.player import get_player, get_player_avatar, TileTransitionState, RunningState
from modules.tasks import task_is_active
from ._interface import BotModeError


def walk_to(destination_coordinates: tuple[int, int], run: bool = True) -> Generator:
    """
    Moves the player to a set of coordinates on the same map. Does absolutely no
    collision checking and _will_ get stuck all the time.
    This returns control back to the calling functions _while the player is still moving_.
    To prevent this, you might want to use the `follow_path()` utility function instead.
    :param destination_coordinates: Tuple (x, y) of map-local coordinates of the destination
    :param run: Whether the player should run (hold down B)
    """

    if get_game_state() != GameState.OVERWORLD:
        return

    if run:
        context.emulator.hold_button("B")
    else:
        context.emulator.release_button("B")

    initial_map = get_player_avatar().map_group_and_number
    while True:
        avatar = get_player_avatar()
        if avatar.local_coordinates == destination_coordinates:
            break
        if avatar.map_group_and_number != initial_map:
            while get_game_state() != GameState.OVERWORLD:
                yield
            break

        # Check whether there is a PokéNav call active and close it.
        while task_is_active("Task_SpinPokenavIcon"):
            context.emulator.release_button("B")
            context.emulator.press_button("B")
            yield
            if run:
                context.emulator.hold_button("B")

        context.emulator.release_button("Up")
        context.emulator.release_button("Down")
        context.emulator.release_button("Left")
        context.emulator.release_button("Right")
        if destination_coordinates[0] < avatar.local_coordinates[0]:
            context.emulator.hold_button("Left")
        elif destination_coordinates[0] > avatar.local_coordinates[0]:
            context.emulator.hold_button("Right")
        elif destination_coordinates[1] < avatar.local_coordinates[1]:
            context.emulator.hold_button("Up")
        elif destination_coordinates[1] > avatar.local_coordinates[1]:
            context.emulator.hold_button("Down")

        yield

    context.emulator.release_button("Up")
    context.emulator.release_button("Down")
    context.emulator.release_button("Left")
    context.emulator.release_button("Right")
    context.emulator.release_button("B")


def follow_path(waypoints: list[tuple[int, int]], run: bool = True) -> Generator:
    """
    Moves the player along a given path.

    There is no collision checking, so the path needs to be chosen carefully to ensure it
    doesn't get stuck.

    :param waypoints: List of tuples (x, y) of map-local coordinates of the destination
    :param run: Whether the player should run (hold down B)
    """
    if get_game_state() != GameState.OVERWORLD:
        return

    # Make sure that the player avatar can actually be controlled/moved right now.
    if "heldMovementActive" not in get_map_objects()[0].flags:
        return

    for waypoint in waypoints:
        yield from walk_to(waypoint, run)

    # Wait for player to come to a full stop.
    while get_player_avatar().running_state != RunningState.NOT_MOVING:
        yield


def navigate_to(x: int, y: int, run: bool = True) -> Generator:
    """
    Tries to walk the player to a given location while circumventing obstacles.

    This is a pretty primitive implementation and only works within a map. If you need to cross
    maps, you have to use this to get to the edge of the first map, then use `walk_one_tile()`
    to cross the map border, and then call this function again to navigate within the second map.

    It attempts to avoid tiles that have encounters (tall grass etc.) but does not currently
    avoid trainers.

    It only works _either_ on land _or_ on water, but won't start or stop to surf.

    :param x: Map-local X coordinate of the destination
    :param y: Map-local Y coordinate of the destination
    :param run: Whether the player should run (hold down B)
    """
    destination_coordinates = x, y
    tiles = get_map_all_tiles()
    map_width, map_height = tiles[0].map_size

    starting_point = get_player_avatar().local_coordinates
    visited_nodes: dict[tuple[int, int], tuple[int, tuple[int, int]]] = {starting_point: (0, starting_point)}
    node_queue = queue.SimpleQueue()
    node_queue.put(starting_point)

    while not node_queue.empty():
        coords = node_queue.get()
        tile = tiles[coords[1] * map_width + coords[0]]
        potential_neighbours = {
            "North": (coords[0], coords[1] - 1),
            "West": (coords[0] + 1, coords[1]),
            "South": (coords[0], coords[1] + 1),
            "East": (coords[0] - 1, coords[1]),
        }
        for direction in potential_neighbours:
            n_coords = potential_neighbours[direction]
            if 0 <= n_coords[0] < map_width and 0 <= n_coords[1] < map_height:
                neighbour = tiles[n_coords[1] * map_width + n_coords[0]]
                if neighbour.collision:
                    may_pass = False
                    if (
                        neighbour.tile_type.startswith("Jump ")
                        or neighbour.tile_type.startswith("Walk ")
                        or neighbour.tile_type.startswith("Slide ")
                    ):
                        _, passable_direction = neighbour.tile_type.split(" ")
                        if direction in passable_direction.split("/"):
                            may_pass = True
                    if not may_pass:
                        continue
                if neighbour.elevation not in (0, 15) and tile.elevation != 0 and tile.elevation != neighbour.elevation:
                    continue
                tile_blocked_by_object = False
                object_event_ids = []
                for map_object in get_map_objects():
                    object_event_ids.append(map_object.local_id)
                    if map_object.current_coords == n_coords:
                        tile_blocked_by_object = True
                        break
                for object_template in tiles[0].objects:
                    if object_template.local_id in object_event_ids:
                        continue
                    if object_template.flag_id != 0 and get_event_flag_by_number(object_template.flag_id):
                        continue
                    if object_template.local_coordinates == n_coords:
                        tile_blocked_by_object = True
                        break
                if tile_blocked_by_object:
                    continue

                if neighbour.has_encounters:
                    distance = visited_nodes[coords][0] + 1000
                else:
                    distance = visited_nodes[coords][0] + 1

                if n_coords not in visited_nodes or visited_nodes[n_coords][0] > distance:
                    visited_nodes[n_coords] = (distance, coords)
                    node_queue.put(n_coords)
                    if n_coords == destination_coordinates:
                        break

    if destination_coordinates not in visited_nodes:
        raise BotModeError(f"Could not find a path to ({destination_coordinates[0]}, {destination_coordinates[1]}).")

    current_node = visited_nodes[destination_coordinates]
    waypoints = [destination_coordinates]
    while current_node[1] != starting_point:
        waypoints.append(current_node[1])
        current_node = visited_nodes[current_node[1]]

    yield from follow_path(list(reversed(waypoints)), run)


def walk_one_tile(direction: str, run: bool = True) -> Generator:
    if run:
        context.emulator.hold_button("B")

    starting_position = get_player_avatar().local_coordinates
    context.emulator.hold_button(direction)
    while get_player_avatar().local_coordinates == starting_position:
        yield
    context.emulator.release_button(direction)
    context.emulator.release_button("B")

    if get_game_state() == GameState.CHANGE_MAP:
        while get_game_state() == GameState.CHANGE_MAP:
            yield
        while "heldMovementFinished" not in get_map_objects()[0].flags:
            yield

    # Wait for player to come to a full stop.
    while get_player_avatar().running_state != RunningState.NOT_MOVING:
        yield

    if get_game_state() == GameState.CHANGE_MAP:
        while get_game_state() == GameState.CHANGE_MAP:
            yield
        while "heldMovementFinished" not in get_map_objects()[0].flags:
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
                    yield from wait_for_task_to_start_and_finish("Task_EndQuestLog", "B")
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


def wait_for_task_to_start_and_finish(function_name: str, button_to_press: str | None = None) -> Generator:
    """
    This will wait until an in-game task starts (if it is not yet running) and finishes (i.e.
    is no longer part of the task list, or has its 'active' bit set to zero.)
    :param function_name: Function name of the task to wait for.
    :param button_to_press: (Optional) A button that will be continuously mashed while waiting.
    """
    yield from wait_until_task_is_active(function_name, button_to_press)
    yield from wait_until_task_is_not_active(function_name, button_to_press)


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
