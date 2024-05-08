from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter
from modules.map_data import MapRSE
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon import get_opponent, get_party
from modules.save_data import get_last_heal_location
from . import BattleAction
from ._asserts import (
    assert_has_pokemon_with_move,
)
from ._interface import BotMode, BotModeError
from .util import ensure_facing_direction, navigate_to


class KecleonMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Kecleon"

    @staticmethod
    def is_selectable() -> bool:
        if not context.rom.is_emerald:
            return False
        targeted_tile = get_player_avatar().map_location_in_front
        return targeted_tile in MapRSE.ROUTE119 and targeted_tile.local_position == (31, 6)

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
        if not (get_event_flag("RECEIVED_DEVON_SCOPE")):
            raise BotModeError("This mode requires the Devon Scope.")
        if get_event_flag("HIDE_ROUTE_119_KECLEON_1"):
            raise BotModeError("This Kecleon has already been encountered.")
        if get_last_heal_location() != MapRSE.FORTREE_CITY:
            raise BotModeError("This mode requires the last heal location to be Fortree City.")
        if len(get_party()) > 1:
            raise BotModeError("This mode requires only one Pokémon in the party.")

        while context.bot_mode != "Manual":
            self._has_whited_out = False
            yield from navigate_to(MapRSE.ROUTE119, (31, 7))
            yield from ensure_facing_direction("Up")
            while not self._has_whited_out:
                context.emulator.press_button("A")
                yield
