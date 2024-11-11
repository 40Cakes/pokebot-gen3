from typing import Generator

from modules.context import context
from modules.player import get_player_avatar
from modules.battle_state import BattleOutcome
from ._interface import BotMode
from ._asserts import assert_player_has_poke_balls
from .util import apply_white_flute_if_available, spin


class SpinMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Spin"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if not outcome == BattleOutcome.Lost:
            assert_player_has_poke_balls()

    def run(self) -> Generator:
        assert_player_has_poke_balls()
        yield from apply_white_flute_if_available()
        yield from spin()
