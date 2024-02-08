from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.encounter import handle_encounter
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon import get_opponent, get_party
from modules.save_data import get_save_data
from . import BattleAction
from ._asserts import (
    assert_has_pokemon_with_move,
)
from ._interface import BotMode, BotModeError
from ._util import (
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

    def __init__(self):
        super().__init__()
        self._has_whited_out = False

    def on_battle_started(self) -> BattleAction | None:
        handle_encounter(get_opponent(), disable_auto_catch=True)
        return BattleAction.CustomAction

    def on_whiteout(self) -> bool:
        self._has_whited_out = True
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
            self._has_whited_out = False
            if get_player_avatar().map_group_and_number == MapRSE.ROUTE_119.value:
                yield from navigate_to(31, 7)
                while get_player_avatar().facing_direction != "Up":
                    context.emulator.press_button("Up")
                    yield
                while not self._has_whited_out:
                    context.emulator.press_button("A")
                    yield
            if get_player_avatar().map_group_and_number == MapRSE.FORTREE_CITY.value:
                yield from navigate_to(0, 7)
                yield from walk_one_tile("Left")
                yield
