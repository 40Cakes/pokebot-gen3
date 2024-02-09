from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon import get_opponent, get_party
from modules.save_data import get_save_data
from ._asserts import (
    assert_has_pokemon_with_move,
    assert_item_exists_in_bag,
)
from ._interface import BotMode, BotModeError
from ._util import (
    wait_until_script_is_no_longer_active,
    wait_for_task_to_start_and_finish,
    walk_one_tile,
    navigate_to,
)


def _get_targeted_encounter() -> tuple[tuple[int, int], tuple[int, int], str] | None:
    if context.rom.is_emerald:
        encounters = ((MapRSE.ROUTE_119.value, (31, 6), "Kecleon"),)
    else:
        encounters = []

    targeted_tile = get_player_avatar().map_location_in_front
    for entry in encounters:
        if entry[0] == (targeted_tile.map_group, targeted_tile.map_number) and entry[1] == targeted_tile.local_position:
            return entry
    return None


class KecleonMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Kecleon"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    @staticmethod
    def disable_default_battle_handler() -> bool:
        return True

    def run(self) -> Generator:
        assert_has_pokemon_with_move("Selfdestruct", "This mode requires a Pokémon with the move Selfdestruct.")
        if (get_event_flag("RECEIVED_DEVON_SCOPE")) == False:
            raise BotModeError("This mode requires the Devon Scope.")
        if get_event_flag("HIDE_ROUTE_119_KECLEON_1"):
            raise BotModeError("This Kecleon has already been encountered.")
        last_heal_group, last_heal_map = get_save_data().get_last_heal_location()
        if (last_heal_group, last_heal_map) != (MapRSE.FORTREE_CITY.value):
            raise BotModeError("This mode requires the last heal location to be Fortree City.")
        if len(get_party()) > 1:
            raise BotModeError("This mode requires only one Pokémon in the party.")

        while context.bot_mode != "Manual":
            if get_player_avatar().map_group_and_number == MapRSE.ROUTE_119.value:
                yield from navigate_to(31, 7)
                while get_player_avatar().facing_direction != "Up":
                    context.emulator.press_button("Up")
                    yield
                yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", "A")
                yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", "A")
                encounter_pokemon(get_opponent())
                yield from wait_until_script_is_no_longer_active("EventScript_BattleKecleon", "A")
                yield from wait_for_task_to_start_and_finish("Task_ExitNonDoor")
            if get_player_avatar().map_group_and_number == MapRSE.FORTREE_CITY.value:
                yield from navigate_to(0, 7)
                yield from walk_one_tile("Left")
                yield
