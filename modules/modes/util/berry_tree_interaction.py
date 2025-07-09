from typing import Generator

from modules.berry_trees import get_berry_tree_by_id, BerryTreeStage
from modules.context import context
from modules.items import Item, ItemPocket, get_item_bag, get_item_by_name
from modules.memory import get_game_state, GameState
from modules.menuing import is_fade_active, scroll_to_item_in_bag
from modules.modes._interface import BotModeError
from modules.modes.util import (
    wait_for_player_avatar_to_be_controllable,
    wait_for_no_script_to_run,
)
from modules.player import player_avatar_is_controllable, get_player_avatar
from modules.tasks import get_global_script_context


def plant_berry(berry: Item) -> Generator:
    if berry.pocket is not ItemPocket.Berries:
        raise BotModeError(f"Item '{berry.name}' is not a berry.")
    slot_index = get_item_bag().first_slot_index_for(berry)
    if slot_index is None:
        raise BotModeError(f"The player does not have '{berry.name}' in their inventory.")
    if not player_avatar_is_controllable():
        raise BotModeError("Cannot plant a berry while the player is not controllable.")
    tile_in_front_of_player = get_player_avatar().map_location_in_front
    map_object = tile_in_front_of_player.object_by_coordinates(tile_in_front_of_player.local_position)
    if map_object is None or map_object.movement_type != "BERRY_TREE_GROWTH":
        raise BotModeError("Player is not facing a berry patch. Cannot plant.")
    berry_tree = get_berry_tree_by_id(map_object.berry_tree_id)
    if berry_tree.stage is not BerryTreeStage.Empty:
        raise BotModeError("There is already a berry planted in this spot.")

    while get_game_state() is not GameState.BAG_MENU or is_fade_active():
        context.emulator.press_button("A")
        yield
    yield from scroll_to_item_in_bag(berry)
    while get_game_state() is not GameState.OVERWORLD or get_global_script_context().is_active:
        context.emulator.press_button("A")
        yield
    yield from wait_for_player_avatar_to_be_controllable()


def water_berry() -> Generator:
    if not player_avatar_is_controllable():
        raise BotModeError("Cannot water a berry while the player is not controllable.")
    tile_in_front_of_player = get_player_avatar().map_location_in_front
    map_object = tile_in_front_of_player.object_by_coordinates(tile_in_front_of_player.local_position)
    if map_object is None or map_object.movement_type != "BERRY_TREE_GROWTH":
        raise BotModeError("Player is not facing a berry patch. Cannot water.")
    berry_tree = get_berry_tree_by_id(map_object.berry_tree_id)
    if berry_tree.stage is BerryTreeStage.Empty:
        raise BotModeError("There is no berry planted in this spot. Cannot water.")
    if get_item_bag().quantity_of(get_item_by_name("Wailmer Pail")) == 0:
        raise BotModeError("Cannot water berry because the player does not have the Wailmer Pail.")

    if berry_tree.stage is BerryTreeStage.Berries or not berry_tree.current_stage_is_unwatered:
        return

    context.emulator.press_button("A")
    yield
    yield from wait_for_no_script_to_run("A")
    yield from wait_for_player_avatar_to_be_controllable()


def harvest_berry() -> Generator:
    if not player_avatar_is_controllable():
        raise BotModeError("Cannot harvest a berry while the player is not controllable.")
    tile_in_front_of_player = get_player_avatar().map_location_in_front
    map_object = tile_in_front_of_player.object_by_coordinates(tile_in_front_of_player.local_position)
    if map_object is None or map_object.movement_type != "BERRY_TREE_GROWTH":
        raise BotModeError("Player is not facing a berry patch. Cannot harvest.")
    berry_tree = get_berry_tree_by_id(map_object.berry_tree_id)
    if berry_tree.stage is not BerryTreeStage.Berries:
        raise BotModeError("There are no berries to harvest in this patch.")
    if not get_item_bag().has_space_for(berry_tree.berry, berry_tree.berry_yield):
        raise BotModeError("The player's inventory does not have space for these berries.")

    context.emulator.press_button("A")
    yield
    yield from wait_for_no_script_to_run("A")
    yield from wait_for_player_avatar_to_be_controllable()
