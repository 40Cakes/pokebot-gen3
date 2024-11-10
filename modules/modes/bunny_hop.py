from typing import Generator

from modules.context import context
from modules.items import get_item_by_name, get_item_bag
from modules.player import AcroBikeState, TileTransitionState, get_player_avatar
from modules.battle_state import BattleOutcome
from modules.safari_strategy import get_safari_balls_left
from modules.map_data import is_safari_map
from ._asserts import assert_item_exists_in_bag
from ._interface import BotMode
from .util import apply_white_flute_if_available, register_key_item


class BunnyHopMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Acro Bike Bunny Hop"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            return get_player_avatar().map_location.has_encounters
        else:
            return False

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

        assert_item_exists_in_bag(("Acro Bike",), "You need to have the Acro Bike in order to use this mode.")
        yield from register_key_item(get_item_by_name("Acro Bike"))

        yield from apply_white_flute_if_available()
        while True:
            player = get_player_avatar()

            if not player.is_on_bike:
                context.emulator.press_button("Select")
            elif (
                player.acro_bike_state == AcroBikeState.HOPPING_WHEELIE
                and player.tile_transition_state == TileTransitionState.CENTERING
            ):
                context.emulator.release_button("B")
            elif (
                player.acro_bike_state == AcroBikeState.STANDING_WHEELIE
                and player.tile_transition_state == TileTransitionState.NOT_MOVING
            ):
                context.emulator.hold_button("B")
            else:
                context.emulator.press_button("B")

            yield
