from typing import Generator

from modules.battle_state import BattleOutcome
from modules.menuing import use_field_move
from modules.player import get_player_avatar
from ._asserts import assert_player_has_poke_balls
from ._interface import BotMode


class SweetScentMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Sweet Scent"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if not outcome == BattleOutcome.Lost:
            assert_player_has_poke_balls()

    def run(self) -> Generator:
        assert_player_has_poke_balls()
        yield from use_field_move("Sweet Scent")
