from dataclasses import dataclass

from modules.data.map import MapRSE, MapFRLG
from modules.context import context
from modules.items import get_item_by_name
from modules.map import ObjectEvent, calculate_targeted_coords
from modules.player import get_player
from modules.pokemon import get_party
from modules.save_data import get_save_data
from ._interface import BotModeError


def assert_no_auto_battle(error_message: str) -> None:
    """
    Raises an exception if auto battling enabled, i.e. ensures that the bot is configured
    to run away from any battle instead of fighting the opponent.
    :param error_message: Error message to display if the assertion fails.
    """
    if context.config.battle.battle:
        raise BotModeError(error_message)


def assert_no_auto_pickup(error_message: str) -> None:
    """
    Raises an exception if auto pickup enabled, which may interfere with scripted encounters.
    :param error_message: Error message to display if the assertion fails.
    """
    if context.config.battle.pickup:
        raise BotModeError(error_message)


def assert_save_game_exists(error_message: str) -> None:
    """
    Raises an exception if there is no saved game.
    :param error_message: Error message to display if the assertion fails.
    """
    save_data = get_save_data()
    if save_data is None:
        raise BotModeError(error_message)


@dataclass
class SavedMapLocation:
    map_group_and_number: tuple[int, int] | MapRSE | MapFRLG
    local_coordinates: tuple[int, int] | None = None
    facing: bool = False


def assert_saved_on_map(expected_locations: SavedMapLocation | list[SavedMapLocation], error_message: str) -> None:
    """
    Raises an exception if the game has not been saved on the given map.
    :param expected_locations: A location, or list of locations, that the player should be on.
    :param error_message: Error message to display if the assertion fails.
    """
    save_data = get_save_data()
    if save_data is None:
        raise BotModeError(error_message)

    player_object_event = None
    if context.rom.is_frlg:
        start_offset = 0x6A0
    elif context.rom.is_emerald:
        start_offset = 0xA30
    else:
        start_offset = 0x9E0
    for index in range(16):
        offset = start_offset + index * 0x24
        object_event = ObjectEvent(save_data.sections[1][offset : offset + 0x24])
        if "isPlayer" in object_event.flags:
            player_object_event = object_event
            break

    if not isinstance(expected_locations, list):
        expected_locations = [expected_locations]

    for expected_location in expected_locations:
        if isinstance(expected_location.map_group_and_number, (MapRSE, MapFRLG)):
            expected_location.map_group_and_number = expected_location.map_group_and_number.value

        if expected_location.map_group_and_number == save_data.get_map_group_and_number():
            if expected_location.local_coordinates is not None:
                if expected_location.facing:
                    saved_facing_coordinates = calculate_targeted_coords(
                        save_data.get_map_local_coordinates(), player_object_event.facing_direction
                    )
                    if expected_location.local_coordinates == saved_facing_coordinates:
                        return
                elif expected_location.local_coordinates == save_data.get_map_local_coordinates():
                    return
            else:
                return

    raise BotModeError(error_message)


def assert_registered_item(expected_items: str | list[str], error_message: str) -> None:
    """
    Raises an exception if the given item is not registered (for the Select button.)
    :param expected_items: Item name, or list of item names, that should be registered.
    :param error_message: Error message to display if the assertion fails.
    """
    if not isinstance(expected_items, list):
        expected_items = [expected_items]

    registered_item = get_player().registered_item
    if registered_item is None or registered_item.name not in expected_items:
        raise BotModeError(error_message)


def assert_has_pokemon_with_move(move: str, error_message: str) -> int:
    """
    Raises an exception if the player has no Pokemon that knows a given move in their
    party.
    :param move: Name of the move to look for.
    :param error_message: Error message to display if the assertion fails.
    :return: The party index of the first Pokemon that knows this move.
    """
    for pokemon in get_party():
        if not pokemon.is_egg and not pokemon.is_empty:
            for learned_move in pokemon.moves:
                if learned_move is not None and learned_move.move.name == move:
                    return
    raise BotModeError(error_message)


def assert_item_exists_in_bag(items: tuple, error_message: str) -> None:
    """
    Raises an exception if the player does not have the given item in their bag.
    :param items: List of item names to look for.
    :param error_message: Error message to display if the assertion fails.
    """
    item_bag = get_save_data().get_item_bag()
    total_quantity = sum(item_bag.quantity_of(get_item_by_name(item)) for item in items)
    if total_quantity == 0:
        raise BotModeError(error_message)
