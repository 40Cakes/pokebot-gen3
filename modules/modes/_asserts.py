from dataclasses import dataclass

from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.map import ObjectEvent, calculate_targeted_coords
from modules.map_data import MapRSE, MapFRLG, is_safari_map
from modules.player import get_player
from modules.pokemon import Pokemon
from modules.pokemon_party import get_party, get_party_size
from modules.safari_strategy import get_safari_balls_left
from modules.save_data import get_save_data
from ._interface import BotModeError

_error_message_addendum_if_assert_only_failed_in_saved_game = (
    " (This is only the case in the saved game. Perhaps you just need to save again?)"
)


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
    map_group_and_number: tuple[int, int] | MapRSE | MapFRLG | None
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
        if expected_location.map_group_and_number == save_data.get_map_group_and_number():
            if expected_location.local_coordinates is None:
                return

            if expected_location.facing:
                saved_facing_coordinates = calculate_targeted_coords(
                    save_data.get_map_local_coordinates(), player_object_event.facing_direction
                )
                if expected_location.local_coordinates == saved_facing_coordinates:
                    return
            elif expected_location.local_coordinates == save_data.get_map_local_coordinates():
                return
    raise BotModeError(error_message)


def assert_registered_item(
    expected_items: str | list[str], error_message: str, check_in_saved_game: bool = False
) -> None:
    """
    Raises an exception if the given item is not registered (for the Select button.)
    :param expected_items: Item name, or list of item names, that should be registered.
    :param error_message: Error message to display if the assertion fails.
    :param check_in_saved_game: Whether to check for the registered item in the saved game, rather than the
                                currently active one.
    """
    if not isinstance(expected_items, list):
        expected_items = [expected_items]

    player = get_player() if not check_in_saved_game else get_save_data().get_player()
    registered_item = player.registered_item
    if registered_item is None or registered_item.name not in expected_items:
        if get_player().registered_item in expected_items:
            error_message += _error_message_addendum_if_assert_only_failed_in_saved_game
        raise BotModeError(error_message)


def assert_has_pokemon_with_any_move(moves: list[str], error_message: str, check_in_saved_game: bool = False) -> None:
    """
    Raises an exception if the player has no Pokémon that knows any of the given move in their
    party.
    :param moves: List of the names of moves to look for.
    :param error_message: Error message to display if the assertion fails.
    :param check_in_saved_game: Whether to get the party in the saved game, rather than th
                                currently active one.
    """
    party = get_party() if not check_in_saved_game else get_save_data().get_party()
    for move in moves:
        if party.has_pokemon_with_move(move):
            return

    if check_in_saved_game:
        # If the check has failed for the saved game, run it again for the active game -- if that fails
        # too, the following line will raise an unmodified error message and stop the execution of this
        # function. If the assertion is met in the active game but not in the saved one, the line
        # after that will add a note to the error message saying that the check only failed for the
        # saved game.
        assert_has_pokemon_with_any_move(moves, error_message)
        error_message += _error_message_addendum_if_assert_only_failed_in_saved_game
    raise BotModeError(error_message)


def assert_item_exists_in_bag(
    expected_items: str | list[str] | tuple[str], error_message: str, check_in_saved_game: bool = False
) -> None:
    """
    Raises an exception if the player does not have the given item in their bag.
    :param expected_items: Item name, or list of item names, to look for. If supplied with more
                           than one item name, this assertion checks that _at least one of them_
                           is present.
    :param error_message: Error message to display if the assertion fails.
    :param check_in_saved_game: If True, this assertion will check the saved game instead of the
                                current item bag (which is the default.)
    """
    if not isinstance(expected_items, (list, tuple)):
        expected_items = [expected_items]

    item_bag = get_item_bag() if not check_in_saved_game else get_save_data().get_item_bag()
    total_quantity = sum(item_bag.quantity_of(get_item_by_name(item)) for item in expected_items)
    if total_quantity == 0:
        if check_in_saved_game:
            item_bag = get_item_bag()
            total_quantity = sum(item_bag.quantity_of(get_item_by_name(item)) for item in expected_items)
            if total_quantity > 0:
                error_message += _error_message_addendum_if_assert_only_failed_in_saved_game
        raise BotModeError(error_message)


def assert_empty_slot_in_party(error_message: str, check_in_saved_game: bool = False) -> None:
    """
    Raises an exception if the player has a full party.
    :param error_message: Error message to display if the assertion fails.
    :param check_in_saved_game: If True, this assertion will check the saved game instead of the
                                current party (which is the default.)
    """
    party = get_party() if not check_in_saved_game else get_save_data().get_party()
    if len(party) >= 6:
        if check_in_saved_game and get_party_size() < 6:
            error_message += _error_message_addendum_if_assert_only_failed_in_saved_game
        raise BotModeError(error_message)


def assert_player_has_poke_balls() -> None:
    """
    Raises an exception if the player doesn't have any Pokeballs when starting a catching mode
    or if safari ball threshold is reached.
    """
    if is_safari_map():
        if context.rom.is_frlg and get_safari_balls_left() <= 15:
            raise BotModeError("You have less than 15 balls left, switching to manual mode...")
    else:
        if get_item_bag().number_of_balls_except_master_ball == 0:
            raise BotModeError("Out of Pokéballs! Better grab more before the next shiny slips away...")


def pokemon_has_usable_damaging_move(pokemon: Pokemon) -> bool:
    """
    Checks if the given Pokémon has at least one usable attacking move.
    Returns True if a usable move is found; otherwise, False.
    """
    return any(
        move is not None and move.move.base_power > 0 and move.move.name not in context.config.battle.banned_moves
        for move in pokemon.moves
    )


def assert_party_can_fight(error_message: str, check_in_saved_game: bool = False) -> None:
    """
    Ensures the party has at least one Pokémon with a usable attacking move.
    Raises a BotModeError if no Pokémon has any attack-capable moves.
    """
    party = get_party() if not check_in_saved_game else get_save_data().get_party()
    if any(pokemon_has_usable_damaging_move(pokemon) for pokemon in party.non_fainted_pokemon):
        return

    raise BotModeError(error_message)
