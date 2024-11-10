from typing import Generator

from modules.context import context
from modules.player import get_player_avatar
from modules.map_data import is_safari_map
from modules.items import get_item_bag
from modules.safari_strategy import get_safari_balls_left
from modules.battle_state import BattleOutcome
from ._interface import BotMode
from .util import apply_white_flute_if_available, spin


class SpinMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Spin"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if is_safari_map():
            balls_left = get_safari_balls_left()
            if balls_left <= 15:
                context.message = "You have less than 15 balls left, switching to manual mode..."
                return context.set_manual_mode()
        else:
            if not outcome == BattleOutcome.Lost and get_item_bag().number_of_balls_except_master_ball == 0:
                context.message = "Out of Poké Balls! Better grab more before the next shiny slips away..."
                return context.set_manual_mode()

    def run(self) -> Generator:
        if get_item_bag().number_of_balls_except_master_ball == 0:
            context.message = "Out of Poké Balls! Better grab more before the next shiny slips away..."
            return context.set_manual_mode()
        yield from apply_white_flute_if_available()
        yield from spin()
