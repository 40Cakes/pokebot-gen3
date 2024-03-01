"""
This file contains helper functions that can be used by bot modes to handle common tasks.

The functions inhere are all Generator functions and can be called from within bot modes
with the `yield from` keyword. This keyword hands over control to another Generator
function until it finishes.

For example: `yield from utils.navigate_to((3, 3))`
"""

import math
import queue
import random
from enum import Enum
from functools import wraps
from typing import Generator, Iterable, Union

from modules.context import context
from modules.files import get_rng_state_history, save_rng_state_history
from modules.items import Item, ItemPocket, get_item_bag, get_item_by_name
from modules.map import (
    MapLocation,
    get_map_data_for_current_position,
    get_map_all_tiles,
    get_map_data,
    get_map_objects,
    get_player_map_object,
)
from modules.map_data import MapFRLG, MapRSE
from modules.map_path import calculate_path, Waypoint, PathFindingError
from modules.memory import (
    GameState,
    get_event_flag,
    get_event_flag_by_number,
    get_game_state,
    get_game_state_symbol,
    pack_uint32,
    read_symbol,
    unpack_uint16,
    unpack_uint32,
    write_symbol,
)
from modules.menu_parsers import CursorOptionEmerald, CursorOptionFRLG, CursorOptionRS
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator, scroll_to_item_in_bag as real_scroll_to_item
from modules.player import (
    RunningState,
    AcroBikeState,
    TileTransitionState,
    get_player,
    get_player_avatar,
    player_avatar_is_controllable,
    player_avatar_is_standing_still,
    player_is_at,
)
from modules.pokemon import get_party
from modules.region_map import FlyDestinationFRLG, FlyDestinationRSE, get_map_cursor, get_map_region
from modules.tasks import get_global_script_context, get_task, task_is_active
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
        raise BotModeError("Game is not currently in overworld mode. Cannot walk.")

    context.emulator.reset_held_buttons()

    initial_map = get_player_avatar().map_group_and_number
    while True:
        context.emulator.reset_held_buttons()
        if run:
            context.emulator.hold_button("B")

        avatar = get_player_avatar()
        if avatar.local_coordinates == destination_coordinates:
            break
        if avatar.map_group_and_number != initial_map:
            while get_game_state() != GameState.OVERWORLD:
                yield
            break

        if (avatar.running_state == RunningState.NOT_MOVING and avatar.acro_bike_state == AcroBikeState.NORMAL) or (
            context.rom.is_frlg
            and avatar.tile_transition_state in [TileTransitionState.CENTERING, TileTransitionState.NOT_MOVING]
            and "Std_MsgboxSign" in get_global_script_context().stack
        ):
            if destination_coordinates[0] < avatar.local_coordinates[0]:
                context.emulator.hold_button("Left")
            elif destination_coordinates[0] > avatar.local_coordinates[0]:
                context.emulator.hold_button("Right")
            elif destination_coordinates[1] < avatar.local_coordinates[1]:
                context.emulator.hold_button("Up")
            elif destination_coordinates[1] > avatar.local_coordinates[1]:
                context.emulator.hold_button("Down")

        yield

    context.emulator.reset_held_buttons()


def follow_path(waypoints: Iterable[tuple[int, int]], run: bool = True) -> Generator:
    """
    Moves the player along a given path.

    There is no collision checking, so the path needs to be chosen carefully to ensure it
    doesn't get stuck.

    :param waypoints: List of tuples (x, y) of map-local coordinates of the destination
    :param run: Whether the player should run (hold down B)
    """
    if get_game_state() != GameState.OVERWORLD:
        raise RuntimeError("The game is currently not in the overworld. Cannot navigate.")

    # Make sure that the player avatar can actually be controlled/moved right now.
    if not player_avatar_is_controllable():
        raise RuntimeError("The player avatar is currently not controllable. Cannot navigate.")

    for waypoint in waypoints:
        yield from walk_to(waypoint, run)

    # Wait for player to come to a full stop.
    while not player_avatar_is_standing_still() or get_player_avatar().running_state != RunningState.NOT_MOVING:
        yield


def deprecated_navigate_to_on_current_map(x: int, y: int, run: bool = True) -> Generator:
    """
    (This is an older, now deprecated implementation of a pathfinding navigation function.
    For new code, use `navigate_to()` instead.)

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
    tiles = get_map_all_tiles()
    map_width, map_height = tiles[0].map_size

    def is_tile_accessible(destination: MapLocation, source: MapLocation) -> bool:
        if source.local_position[0] < destination.local_position[0]:
            direction = "East"
        elif source.local_position[0] > destination.local_position[0]:
            direction = "West"
        elif source.local_position[1] < destination.local_position[1]:
            direction = "South"
        else:
            direction = "North"

        if destination.collision:
            may_pass = False
            if (
                destination.tile_type.startswith("Jump ")
                or destination.tile_type.startswith("Walk ")
                or destination.tile_type.startswith("Slide ")
            ):
                _, passable_direction = destination.tile_type.split(" ")
                if direction in passable_direction.split("/"):
                    may_pass = True
            if not may_pass:
                return False
        if source.tile_type.startswith("Impassable "):
            impassable_directions = source.tile_type[11:].split(" and ")
            if direction in impassable_directions:
                return False
        if destination.elevation not in (0, 15) and source.elevation != 0 and source.elevation != destination.elevation:
            return False
        if destination.tile_type == "Door Warp":
            return False
        tile_blocked_by_object = False
        object_event_ids = []
        for map_object in get_map_objects():
            object_event_ids.append(map_object.local_id)
            if "player" not in map_object.flags and destination.local_position in (
                map_object.current_coords,
                map_object.previous_coords,
            ):
                tile_blocked_by_object = True
                break
        for object_template in tiles[0].objects:
            if object_template.local_id in object_event_ids:
                continue
            if object_template.flag_id != 0 and get_event_flag_by_number(object_template.flag_id):
                continue
            if object_template.local_coordinates == destination.local_position:
                tile_blocked_by_object = True
                break
        return not tile_blocked_by_object

    def calculate_path(end_point: tuple[int, int], starting_point: tuple[int, int]) -> list[tuple[int, int]]:
        visited_nodes: dict[tuple[int, int], tuple[int, tuple[int, int]]] = {starting_point: (0, starting_point)}
        node_queue = queue.SimpleQueue()
        node_queue.put(starting_point)

        while not node_queue.empty() and end_point not in visited_nodes:
            coords = node_queue.get()
            tile = tiles[coords[1] * map_width + coords[0]]
            potential_neighbours = {
                "North": (coords[0], coords[1] - 1),
                "West": (coords[0] - 1, coords[1]),
                "South": (coords[0], coords[1] + 1),
                "East": (coords[0] + 1, coords[1]),
            }
            for direction in potential_neighbours:
                n_coords = potential_neighbours[direction]
                if 0 <= n_coords[0] < map_width and 0 <= n_coords[1] < map_height:
                    neighbour = tiles[n_coords[1] * map_width + n_coords[0]]
                    if not is_tile_accessible(neighbour, tile):
                        continue

                    if neighbour.has_encounters:
                        distance = visited_nodes[coords][0] + 1000
                    else:
                        distance = visited_nodes[coords][0] + 1

                    if n_coords not in visited_nodes or visited_nodes[n_coords][0] > distance:
                        visited_nodes[n_coords] = (distance, coords)
                        node_queue.put(n_coords)
                        if n_coords == end_point:
                            break

        if end_point not in visited_nodes:
            raise BotModeError(f"Could not find a path to ({end_point[0]}, {end_point[1]}).")

        current_node = visited_nodes[end_point]
        waypoints = [end_point]
        while current_node[1] != starting_point:
            waypoints.append(current_node[1])
            current_node = visited_nodes[current_node[1]]

        return list(reversed(waypoints))

    while get_player_avatar().local_coordinates != (x, y):
        timeout = 60
        last_known_location = get_player_avatar().local_coordinates
        for _ in follow_path(calculate_path((x, y), last_known_location), run):
            timeout -= 1
            if timeout <= 0 and get_game_state() == GameState.OVERWORLD:
                current_location = get_player_avatar().local_coordinates
                if current_location == last_known_location:
                    for __ in range(16):
                        yield
                    break
                else:
                    last_known_location = current_location
                    timeout += 60
            yield

    context.emulator.reset_held_buttons()
    yield from wait_for_player_avatar_to_be_controllable()


class TimedOutTryingToReachWaypointError(BotModeError):
    def __init__(self, waypoint: Waypoint):
        self.waypoint = waypoint
        if context.rom.is_rse:
            map_name = MapRSE(waypoint.map).name
        else:
            map_name = MapFRLG(waypoint.map).name
        message = f"Did not reach waypoint ({waypoint.coordinates}) @ {map_name} in time."
        super().__init__(message)


def follow_waypoints(path: Iterable[Waypoint], run: bool = True) -> Generator:
    """
    Follows a given set of waypoints.

    Since the `path` parameter can also be a generator function, this function can be used to follow
    looping or dynamically calculated paths.

    This function does not check for obstacles, but if it takes too long to reach a waypoint it will
    fire a `TimedOutTryingToReachWaypointError` exception (which is a child class of `BotModeError`,
    so if unhandled it will just show as a message and put the bot back into manual mode.)

    :param path: A list (or generator) of waypoints to follow.
    :param run: Whether to run (hold `B`.) This is ignored when on a bicycle, since it would be either
                meaningless or actively detrimental (Acro Bike, where it would initiate wheelie mode.)
    """

    if get_game_state() != GameState.OVERWORLD:
        raise BotModeError("The game is currently not in the overworld. Cannot navigate.")

    # Make sure that the player avatar can actually be controlled/moved right now.
    if not player_avatar_is_controllable():
        raise BotModeError("The player avatar is currently not controllable. Cannot navigate.")

    # 'Running' means holding B, which on the Acro Bike leads to doing a Wheelie which is actually
    # slower than normal riding. On other bikes it just doesn't do anything, so if we are riding one,
    # this flag will just be ignored.
    if run and get_player_avatar().is_on_bike:
        run = False

    # For each waypoint (i.e. each step of the path) we set a timeout. If the player avatar does not reach the
    # expected location within that time, we stop the walking. The calling code could use that event to
    # recalculate a new path.
    #
    # Regular steps usually take 16 frames, so the 20-frame timeout should be enough. For warps (walking into doors
    # etc.) a 'step' may take a bit longer due to the map transition. Which is why there is an extra allowance for
    # those cases.
    timeout_in_frames = 20
    extra_timeout_in_frames_for_warps = 280

    current_position = get_map_data_for_current_position()
    for waypoint in path:
        timeout_exceeded = False
        frames_remaining_until_timeout = timeout_in_frames
        if waypoint.is_warp:
            frames_remaining_until_timeout += extra_timeout_in_frames_for_warps

        while not timeout_exceeded and not player_is_at(waypoint.map, waypoint.coordinates):
            player_object = get_player_map_object()

            if get_game_state() == GameState.OVERWORLD:
                frames_remaining_until_timeout -= 1

            if frames_remaining_until_timeout <= 0:
                if player_is_at(current_position.map_group_and_number, current_position.local_position):
                    context.emulator.reset_held_buttons()
                    yield from wait_for_n_frames(16)
                    raise TimedOutTryingToReachWaypointError(waypoint)
                else:
                    current_position = get_map_data_for_current_position()
                    frames_remaining_until_timeout += timeout_in_frames

            # Only pressing the direction keys during the frame where movement is actually registered can help
            # preventing weird overshoot issues in cases where a listener handles an event (like a battle, PokeNav
            # call, ...)
            if player_object is not None and "heldMovementFinished" in player_object.flags:
                context.emulator.hold_button(waypoint.walking_direction)
                if run:
                    context.emulator.hold_button("B")
            else:
                context.emulator.reset_held_buttons()

            yield

    # Wait for player to come to a full stop.
    context.emulator.reset_held_buttons()
    while not player_avatar_is_standing_still() or get_player_avatar().running_state != RunningState.NOT_MOVING:
        yield


def navigate_to(
    map: tuple[int, int] | MapFRLG | MapRSE,
    coordinates: tuple[int, int],
    run: bool = True,
    avoid_encounters: bool = True,
    avoid_scripted_events: bool = True,
) -> Generator:
    """
    Tries to walk the player to a given location while circumventing obstacles.

    It works across different maps, but only if they are directly connected. Warps (doors, cave entrances, ...) will not
    be used automatically -- but a door can be used as a destination.

    It will also not attempt to start or stop surfing, i.e. transitions between land and water need to be handled
    separately.

    :param map: Destination map. This can either be a `MapFRLG`/`MapRSE` instance, or a map group/number tuple.
    :param coordinates: Local coordinates on the destination map that should be navigated to.
    :param run: Whether to sprint (hold B.) This is ignored when riding a bicycle.
    :param avoid_encounters: Prefer navigating via tiles that do not have encounters (i.e. try to avoid tall grass etc.)
                             This will still navigate via tiles with encounters if there is no other option.
                             It will also not avoid the activation range of unbattled trainers.
    :param avoid_scripted_events: Try to avoid tiles that would trigger a scripted event when moving onto them. It will
                                  still navigate via those tiles of there is no other option.
    """

    def waypoint_generator():
        destination_map = map
        destination_coordinates = coordinates

        while not player_is_at(destination_map, destination_coordinates):
            current_position = get_map_data_for_current_position()
            try:
                waypoints = calculate_path(
                    current_position,
                    get_map_data(map, coordinates),
                    avoid_encounters=avoid_encounters,
                    avoid_scripted_events=avoid_scripted_events,
                )
            except PathFindingError as e:
                raise BotModeError(str(e))

            # If the final destination turns out to be a warp, we are not going to end up in the place specified by
            # the `map` and `coordinates` parameters, but rather on another map. Because that would lead to this
            # function thinking we've missed the target, we will override the destination with the warp destination
            # in those cases.
            if waypoints[-1].is_warp:
                destination_map = waypoints[-1].map
                destination_coordinates = waypoints[-1].coordinates

            yield from waypoints

    while True:
        try:
            yield from follow_waypoints(waypoint_generator(), run)
            break
        except TimedOutTryingToReachWaypointError:
            # If we run into a timeout while trying to follow the waypoints, this is likely because of either of
            # these two reasons:
            #
            # (a) For some weird reason the player avatar moved to an unexpected location (for example due to forced
            #     movement, or due to overshooting on the Mach Bike.)
            # (b) Since the path is calculated in the beginning and then just followed, there's a chance that an NPC
            #     moves and gets in our way, in which case we would just keep running into them until they finally move
            #     out of the way again.
            #
            # In these cases, the `follow_waypoints()` function will trigger this timeout exception. We will just
            # calculate a new path (from the new location, or taking into account the new location of obstacles) and
            # try pathing again.
            pass


def walk_one_tile(direction: str, run: bool = True) -> Generator:
    """
    Moves the player one tile in a given direction, and then waiting for the movement
    to finish and any map transitions to complete before returning.

    Note that this will not check whether the destination tile is actually accessible
    so making sure of that is the responsibility of the calling code. It will create
    an endless loop if trying to run into a wall because the player's coordinates will
    never change.

    :param direction: One of "Up", "Down", "Left", "Right"
    :param run: Whether the player should run (hold down B)
    """
    if direction not in ("Up", "Down", "Left", "Right"):
        raise ValueError(f"'{direction}' is not a valid direction.")

    if run:
        context.emulator.hold_button("B")

    starting_position = get_player_avatar().local_coordinates
    context.emulator.hold_button(direction)
    while get_player_avatar().local_coordinates == starting_position:
        yield
    context.emulator.release_button(direction)
    context.emulator.release_button("B")

    # Wait for player to come to a full stop.
    while (
        not player_avatar_is_standing_still()
        or get_player_avatar().running_state != RunningState.NOT_MOVING
        or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
    ):
        yield


def ensure_facing_direction(facing_direction: str | tuple[int, int]) -> Generator:
    """
    If the player avatar is not already facing a certain direction this will make it turn
    around, so that afterwards it definitely faces the desired direction.
    :param facing_direction: One of "Up", "Down", "Left", or "Right"
    """
    if isinstance(facing_direction, tuple):
        x, y = get_player_avatar().local_coordinates
        if (x - 1, y) == facing_direction:
            facing_direction = "Left"
        elif (x + 1, y) == facing_direction:
            facing_direction = "Right"
        elif (x, y - 1) == facing_direction:
            facing_direction = "Up"
        elif (x, y + 1) == facing_direction:
            facing_direction = "Down"
        else:
            raise BotModeError(f"Tile ({x}, {y}) is not adjacent to the player.")

    while True:
        avatar = get_player_avatar()
        if avatar.facing_direction == facing_direction:
            return

        if (
            get_game_state() == GameState.OVERWORLD
            and avatar.tile_transition_state == TileTransitionState.NOT_MOVING
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
                yield from wait_for_player_avatar_to_be_controllable()
                return

        yield


def wait_for_player_avatar_to_be_controllable(button_to_press: str | None = None) -> Generator:
    while not player_avatar_is_controllable():
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


def wait_for_player_avatar_to_be_standing_still(button_to_press: str | None = None) -> Generator:
    while not player_avatar_is_standing_still():
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
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


def wait_until_script_is_active(function_name: str, button_to_press: str | None = None) -> Generator:
    while not get_global_script_context().is_active or function_name not in get_global_script_context().stack:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


def wait_until_script_is_no_longer_active(function_name: str, button_to_press: str | None = None) -> Generator:
    while get_global_script_context().is_active and function_name in get_global_script_context().stack:
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


def wait_for_script_to_start_and_finish(function_name: str, button_to_press: str | None = None) -> Generator:
    yield from wait_until_script_is_active(function_name, button_to_press)
    yield from wait_until_script_is_no_longer_active(function_name, button_to_press)


def wait_for_no_script_to_run(button_to_press: str | None = None) -> Generator:
    while get_global_script_context().is_active:
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


def wait_for_n_frames(number_of_frames: int) -> Generator:
    """
    This will wait for a certain number of frames to pass.
    """
    for _ in range(number_of_frames):
        yield


def scroll_to_item_in_bag(item: Item) -> Generator:
    """
    This will select the correct bag pocket and scroll to the correct position therein.

    It will _not_ activate the item (pressing A) and it does _not_ open the bag menu.
    It is assumed that the bag menu is already open.

    :param item: Item to scroll to
    """
    if get_item_bag().quantity_of(item) == 0:
        raise BotModeError(f"Cannot use {item.name} because there is none in the item bag.")

    yield from real_scroll_to_item(item)


def isolate_inputs(generator_function):
    @wraps(generator_function)
    def wrapper_function(*args, **kwargs):
        previous_inputs = context.emulator.reset_held_buttons()
        yield from generator_function(*args, **kwargs)
        context.emulator.restore_held_buttons(previous_inputs)

    return wrapper_function


class RanOutOfRepels(BotModeError):
    pass


@isolate_inputs
def use_item_from_bag(item: Item) -> Generator:
    yield from StartMenuNavigator("BAG").step()
    yield from scroll_to_item_in_bag(item)

    if context.rom.is_rs:
        confirmation_after_use_item_task = "sub_80F9090"
        start_menu_task = "sub_80712B4"
    elif context.rom.is_emerald:
        confirmation_after_use_item_task = "Task_ContinueTaskAfterMessagePrints"
        start_menu_task = "Task_ShowStartMenu"
    else:
        confirmation_after_use_item_task = "Task_ContinueTaskAfterMessagePrints"
        start_menu_task = "Task_StartMenuHandleInput"

    yield from wait_for_task_to_start_and_finish(confirmation_after_use_item_task, "A")
    yield from wait_for_task_to_start_and_finish(start_menu_task, "B")
    yield


def register_key_item(item: Item) -> Generator:
    """
    Ensures that a Key Item is registered to the Select button.
    :param item: The item to register
    """
    if item.pocket != ItemPocket.KeyItems:
        raise BotModeError(f"Cannot register {item.name} as it is not a Key Item.")

    if get_item_bag().quantity_of(item) <= 0:
        raise BotModeError(f"Cannot register {item.name} as it is not in the item bag.")

    previously_registered_item = get_player().registered_item
    if previously_registered_item is not None and previously_registered_item.index == item.index:
        return

    yield from StartMenuNavigator("BAG").step()
    yield from scroll_to_item_in_bag(item)
    context.emulator.press_button("A")
    if context.rom.is_rs:
        yield from wait_for_n_frames(4)
        context.emulator.press_button("Right")
        yield from wait_for_n_frames(3)
    elif context.rom.is_emerald:
        yield from wait_for_n_frames(3)
        context.emulator.press_button("Right")
        yield from wait_for_n_frames(3)
    else:
        yield from wait_for_n_frames(6)
        context.emulator.press_button("Down")
        yield from wait_for_n_frames(2)

    context.emulator.press_button("A")

    if context.rom.is_rs:
        start_menu_task = "sub_80712B4"
    elif context.rom.is_emerald:
        start_menu_task = "Task_ShowStartMenu"
    else:
        start_menu_task = "Task_StartMenuHandleInput"

    yield from wait_for_task_to_start_and_finish(start_menu_task, "B")
    yield


def apply_white_flute_if_available() -> Generator:
    if context.rom.is_frlg and get_event_flag("SYS_WHITE_FLUTE_ACTIVE"):
        return
    elif context.rom.is_rse and get_event_flag("SYS_ENC_UP_ITEM"):
        return

    white_flute = get_item_by_name("White Flute")
    if get_item_bag().quantity_of(white_flute) > 0:
        yield from use_item_from_bag(white_flute)


@isolate_inputs
def apply_repel() -> Generator:
    """
    Tries to use the strongest Repel available in the player's item bag (i.e. it will
    prefer Max Repel over Super Repel over Repel.)

    If the player does not have any Repel items, it raises a `RanOutOfRepels` error.
    """
    item_bag = get_item_bag()
    repel_item = get_item_by_name("Max Repel")
    repel_slot = item_bag.first_slot_index_for(repel_item)
    if repel_slot is None:
        repel_item = get_item_by_name("Super Repel")
        repel_slot = item_bag.first_slot_index_for(repel_item)
    if repel_slot is None:
        repel_item = get_item_by_name("Repel")
        repel_slot = item_bag.first_slot_index_for(repel_item)
    if repel_slot is None:
        raise RanOutOfRepels("Player is out or Repels.")

    yield from use_item_from_bag(repel_item)


def replenish_repel() -> None:
    """
    This can be used in a bot mode's `on_repel_effect_ended()` callback to re-enable the repel
    effect as soon as it expires.

    It should not be used anywhere else.
    """

    if get_item_bag().number_of_repels == 0:
        raise RanOutOfRepels("Player ran out of repels")
    else:
        context.controller_stack.insert(len(context.controller_stack) - 1, apply_repel())


@isolate_inputs
def fly_to(destination: Union[FlyDestinationRSE, FlyDestinationFRLG]) -> Generator:
    if context.rom.is_frlg:
        has_necessary_badge = get_event_flag("BADGE03_GET")
        menu_index = CursorOptionFRLG.FLY
    else:
        has_necessary_badge = get_event_flag("BADGE03_GET")
        if context.rom.is_rs:
            menu_index = CursorOptionRS.FLY
        else:
            menu_index = CursorOptionEmerald.FLY

    if not has_necessary_badge:
        raise BotModeError("Player does not have the badge required for flying.")

    if not get_event_flag(destination.get_flag_name()):
        raise BotModeError(f"Player cannot fly to {destination.name} because that location is not yet available.")

    flying_pokemon_index = -1
    for index in range(len(get_party())):
        pokemon = get_party()[index]
        for learned_move in pokemon.moves:
            if learned_move is not None and learned_move.move.name == "Fly":
                flying_pokemon_index = index
                break
        if flying_pokemon_index > -1:
            break
    if flying_pokemon_index == -1:
        raise BotModeError("Player does not have any Pokémon that knows Fly in their party.")

    # Select field move FLY
    yield from StartMenuNavigator("POKEMON").step()
    yield from PokemonPartyMenuNavigator(flying_pokemon_index, "", menu_index).step()

    # Wait for region map to load.
    while get_game_state_symbol() not in ("CB2_FLYMAP", "CB2_REGIONMAP") or get_map_cursor() is None:
        yield

    destination_region = destination.get_map_region()
    if get_map_region() != destination_region:
        raise BotModeError(f"Player cannot fly to {destination.name} because they are in the wrong region.")

    # Select destination on the region map
    x, y = destination.value
    while get_map_cursor() != (x, y):
        context.emulator.reset_held_buttons()
        if get_map_cursor()[0] < x:
            context.emulator.hold_button("Right")
        elif get_map_cursor()[0] > x:
            context.emulator.hold_button("Left")
        elif get_map_cursor()[1] < y:
            context.emulator.hold_button("Down")
        elif get_map_cursor()[1] > y:
            context.emulator.hold_button("Up")
        yield
    context.emulator.reset_held_buttons()

    # Wait for journey to finish
    yield from wait_for_task_to_start_and_finish("Task_FlyIntoMap", "A")
    yield


def teach_hm_or_tm(hm_or_tm: Item, party_index: int, move_index_to_replace: int = 3) -> Generator:
    """
    Attempts to teach an HM or TM move to a party Pokémon.

    This assumes that the game is currently in the overworld and the player is controllable.

    :param hm_or_tm: Item reference of the HM/TM to teach.
    :param party_index: Party index (0-5) of the Pokémon that this move should be taught to.
    :param move_index_to_replace: Index of a move (0-3) that should be replaced. If the
                                  Pokémon still has an empty move slot, this is not used.
    """

    yield from StartMenuNavigator("BAG").step()

    if context.rom.is_rse:
        yield from scroll_to_item_in_bag(hm_or_tm)
    else:
        # On FR/LG, there is a special 'TM Case' item which contains the actual HM/TM bag.
        # Open it, then scroll to the right position.
        yield from scroll_to_item_in_bag(get_item_by_name("TM Case"))
        yield from wait_until_task_is_active("Task_HandleListInput", "A")
        yield from wait_for_n_frames(25)
        target_slot_index = get_item_bag().first_slot_index_for(hm_or_tm)
        while True:
            tm_case_state = read_symbol("sTMCaseStaticResources", offset=8, size=4)
            cursor_offset = unpack_uint16(tm_case_state[:2])
            scroll_offset = unpack_uint16(tm_case_state[2:4])
            current_slot_index = cursor_offset + scroll_offset
            if current_slot_index < target_slot_index:
                context.emulator.press_button("Down")
                yield
            elif current_slot_index > target_slot_index:
                context.emulator.press_button("Up")
                yield
            else:
                break

    while get_game_state() != GameState.PARTY_MENU:
        context.emulator.press_button("A")
        yield

    # Select the target Pokémon in Party Menu
    while True:
        if context.rom.is_rs:
            current_slot_index = context.emulator.read_bytes(0x0202002F + len(get_party()) * 136 + 3, length=1)[0]
        else:
            current_slot_index = read_symbol("gPartyMenu", offset=9, size=1)[0]
        if current_slot_index < party_index:
            context.emulator.press_button("Down")
            yield
        elif current_slot_index > party_index:
            context.emulator.press_button("Up")
            yield
        else:
            break

    # Wait for either the 'Which move should be replaced' screen or for being
    # back at the item bag screen (if no move needed to be replaced, or if an
    # 'Pokémon already knows this move' error appeared.)
    press_a = True
    while (
        not task_is_active("Task_DuckBGMForPokemonCry")
        and get_game_state() != GameState.BAG_MENU
        and not task_is_active("Task_HandleListInput")
    ):
        if press_a:
            context.emulator.press_button("A")
        if task_is_active("sub_809E260"):
            press_a = False
        yield

    # Handle move replacing.
    if task_is_active("Task_DuckBGMForPokemonCry"):
        for _ in range(move_index_to_replace):
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(3 if context.rom.is_rse else 15)
        context.emulator.press_button("A")
        yield

    # Back to overworld.
    if context.rom.is_rs:
        yield from wait_for_task_to_start_and_finish("sub_80712B4", "B")
    elif context.rom.is_frlg:
        yield from wait_for_task_to_start_and_finish("Task_StartMenuHandleInput", "B")
    else:
        yield from wait_for_task_to_start_and_finish("Task_ShowStartMenu", "B")
    yield


class TaskFishing(Enum):
    INIT = 0
    GET_ROD_OUT = 1
    WAIT_BEFORE_DOTS = 2
    INIT_DOTS = 3
    SHOW_DOTS = 4
    CHECK_FOR_BITE = 5
    GOT_BITE = 6
    WAIT_FOR_A = 7
    CHECK_MORE_DOTS = 8
    MON_ON_HOOK = 9
    START_ENCOUNTER = 10
    NOT_EVEN_NIBBLE = 11
    GOT_AWAY = 12
    NO_MON = 13
    PUT_ROD_AWAY = 14
    END_NO_MON = 15


def fish() -> Generator:
    task_fishing = get_task("Task_Fishing")
    if task_fishing is not None:
        match task_fishing.data[0]:
            case TaskFishing.WAIT_FOR_A.value | TaskFishing.END_NO_MON.value:
                context.emulator.press_button("A")
            case TaskFishing.NOT_EVEN_NIBBLE.value:
                context.emulator.press_button("B")
            case TaskFishing.START_ENCOUNTER.value:
                context.emulator.press_button("A")
    else:
        context.emulator.press_button("Select")
    yield


def get_closest_tile(tiles: list[tuple[int, int]]) -> tuple[int, int] | None:
    return min(
        tiles,
        key=lambda tile: math.hypot(
            get_player_avatar().local_coordinates[1] - tile[1],
            get_player_avatar().local_coordinates[0] - tile[0],
        ),
    )


def get_closest_surrounding_tile(tile: tuple[int, int]) -> tuple[int, int] | None:
    if valid_surrounding_tiles := [
        get_map_data(get_player_avatar().map_group_and_number, check).local_position
        for check in [
            (tile[0] + 1, tile[1]),
            (tile[0], tile[1] + 1),
            (tile[0] - 1, tile[1]),
            (tile[0], tile[1] - 1),
        ]
        if get_map_data(get_player_avatar().map_group_and_number, check).is_surfable
    ]:
        return get_closest_tile(valid_surrounding_tiles)
    else:
        return None


def get_tile_direction(tile: tuple[int, int]) -> str | None:
    tile_coords = tile
    player_coords = get_player_avatar().local_coordinates

    direction = None
    if tile_coords[0] < player_coords[0]:
        direction = "Left"
    if tile_coords[1] < player_coords[1]:
        direction = "Up"
    if tile_coords[0] > player_coords[0]:
        direction = "Right"
    if tile_coords[1] > player_coords[1]:
        direction = "Down"

    return direction
