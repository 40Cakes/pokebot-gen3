"""
This file contains helper functions that can be used by bot modes to handle common tasks.

The functions inhere are all Generator functions and can be called from within bot modes
with the `yield from` keyword. This keyword hands over control to another Generator
function until it finishes.

For example: `yield from utils.navigate_to((3, 3))`
"""

import queue
import random
from functools import wraps
from typing import Generator, Union

from modules.context import context
from modules.files import get_rng_state_history, save_rng_state_history
from modules.items import get_item_bag, Item, ItemPocket, get_item_by_name
from modules.map import get_map_objects, get_map_all_tiles, MapLocation
from modules.memory import (
    read_symbol,
    write_symbol,
    pack_uint32,
    unpack_uint32,
    get_game_state,
    get_game_state_symbol,
    GameState,
    get_event_flag,
    get_event_flag_by_number,
)
from modules.menu_parsers import CursorOptionEmerald, CursorOptionRS, CursorOptionFRLG
from modules.menuing import StartMenuNavigator, PokemonPartyMenuNavigator, scroll_to_item_in_bag as real_scroll_to_item
from modules.player import get_player, get_player_avatar, TileTransitionState, RunningState
from modules.pokemon import get_party
from modules.region_map import get_map_region, get_map_cursor, FlyDestinationRSE, FlyDestinationFRLG
from modules.tasks import task_is_active, get_global_script_context
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
        raise RuntimeError("The game is currently not in the overworld. Cannot navigate.")

    # Make sure that the player avatar can actually be controlled/moved right now.
    if "heldMovementActive" not in get_map_objects()[0].flags:
        raise RuntimeError("The player avatar is currently not controllable. Cannot navigate.")

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
            if (
                map_object.current_coords == destination.local_position
                or map_object.previous_coords == destination.local_position
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
        if tile_blocked_by_object:
            return False
        return True

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
        get_game_state() != GameState.OVERWORLD
        or "heldMovementFinished" not in get_map_objects()[0].flags
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
                while "heldMovementActive" not in get_map_objects()[0].flags:
                    yield
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

    previously_registerd_item = get_player().registered_item
    if previously_registerd_item is not None and previously_registerd_item.index == item.index:
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
