from typing import Generator

from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.items import get_item_bag, get_item_by_name
from modules.player import get_player, get_player_avatar
from modules.runtime import get_sprites_path
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

    def run(self) -> Generator:
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
                choices = [Selection(rod, get_sprites_path() / "items" / f"{rod} III.png") for rod in possible_rods]
                rod_to_use = get_item_by_name(ask_for_choice(choices, window_title="Choose which rod to use"))

            yield from register_key_item(rod_to_use)

        while True:
            yield from fish()
