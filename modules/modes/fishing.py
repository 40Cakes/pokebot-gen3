from typing import Generator

from modules.context import context
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.items import get_item_bag, get_item_by_name
from modules.player import get_player, get_player_avatar
from modules.runtime import get_sprites_path
from modules.map_data import is_safari_map
from modules.battle_state import BattleOutcome
from modules.safari_strategy import get_safari_balls_left
from ._asserts import assert_item_exists_in_bag
from ._interface import BotMode
from .util import fish, register_key_item


class FishingMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Fishing"

    @staticmethod
    def is_selectable() -> bool:
        player = get_player_avatar()
        targeted_tile = player.map_location_in_front
        return targeted_tile is not None and targeted_tile.is_surfable

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

        # Ask player to register a rod if they have one
        rod_names = ["Old Rod", "Good Rod", "Super Rod"]
        assert_item_exists_in_bag(rod_names, "You do not own any fishing rod, so you cannot fish.")

        if get_player().registered_item is None or get_player().registered_item.name not in rod_names:
            possible_rods = [
                rod_name for rod_name in rod_names if get_item_bag().quantity_of(get_item_by_name(rod_name)) > 0
            ]
            if len(possible_rods) == 1:
                rod_to_use = get_item_by_name(possible_rods[0])
            else:
                choices = [Selection(rod, get_sprites_path() / "items" / f"{rod}.png") for rod in possible_rods]
                rod_to_use = get_item_by_name(ask_for_choice(choices, window_title="Choose which rod to use"))

            yield from register_key_item(rod_to_use)

        while True:
            yield from fish()
