from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter
from modules.items import get_item_by_name
from modules.map_data import MapRSE
from modules.player import get_player, get_player_avatar
from modules.pokemon import get_opponent, get_party
from . import BattleAction
from ._asserts import assert_item_exists_in_bag
from ._interface import BotMode, BotModeError
from ._util import (
    ensure_facing_direction,
    fish,
    get_closest_surrounding_tile,
    get_closest_tile,
    get_tile_direction,
    deprecated_navigate_to_on_current_map,
    register_key_item,
)
from ..console import console
from ..map import get_map_all_tiles

# Bad tiles such as cliffs marked as surfable, but can't surf or fish on it
bad_tiles = [(19, 44), (20, 45), (23, 46), (27, 47)]


class FeebasMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Feebas"

    @staticmethod
    def is_selectable() -> bool:
        if not context.rom.is_rse:
            return False

        return (
            get_player_avatar().map_group_and_number in (MapRSE.ROUTE119,)
            and get_player_avatar().flags.Surfing
            and get_player_avatar().map_location_in_front.is_surfable
            and get_player_avatar().map_location_in_front.local_position not in bad_tiles
        )

    def __init__(self):
        self.feebas_found: bool = False
        self.feebas_moved: int = 0
        self.tile_threshold: int = 3
        self.tile_checked: int = 0
        self.checked_tiles: list[tuple[int, int]] = bad_tiles
        self.surfable_tiles: list[tuple[int, int]] = [
            tile.local_position for tile in get_map_all_tiles() if (tile.is_surfable and tile.local_position[1] > 28)
        ]
        super().__init__()

    def on_battle_started(self) -> BattleAction | None:
        return handle_encounter(get_opponent(), disable_auto_battle=True)

    def run(self) -> Generator:
        from ..stats import total_stats

        if not get_player_avatar().flags.Surfing:
            raise BotModeError("Player is not surfing, only start this mode while surfing in any water at Route 119.")

        if context.rom.is_emerald and get_party()[0].ability.name not in ["Sticky Hold", "Suction Cups"]:
            console.print("[bold yellow]WARNING: First Pokemon in party does not have Sticky Hold / Suction Cups.")
            console.print(
                "[bold yellow]It is highly recommended to lead with these abilities to increase fishing bite rate."
            )

        # The Old Rod has the advantage of immediately giving you an encounter as soon as you get a bite
        assert_item_exists_in_bag("Old Rod", "You do not own the Old Rod, so you cannot fish.")
        if get_player().registered_item is None or get_player().registered_item.name != "Old Rod":
            yield from register_key_item(get_item_by_name("Old Rod"))

        while True:
            if self.feebas_moved >= 20:
                self.feebas_found = False

            if self.tile_checked < self.tile_threshold or self.feebas_found:
                total_encounters = total_stats.get_total_stats()["totals"]["encounters"]
                while total_encounters == total_stats.get_total_stats()["totals"]["encounters"]:
                    yield from fish()
                if get_opponent().species.name == "Feebas":
                    self.checked_tiles = bad_tiles
                    self.feebas_found = True
                    self.feebas_moved = 0
                self.tile_checked += 1

            else:
                self.feebas_moved += 1
                self.tile_checked = 0
                self.checked_tiles.append(get_player_avatar().map_location_in_front.local_position)

                closest_tile = get_closest_tile(
                    list(
                        filter(
                            lambda x: x not in self.checked_tiles,
                            self.surfable_tiles,
                        )
                    )
                )

                if not closest_tile:
                    return BotModeError(
                        "Feebas could not be found in this water, please move to a different body of water."
                    )

                closest_surrounding_tile = get_closest_surrounding_tile(closest_tile)
                try:
                    yield from deprecated_navigate_to_on_current_map(
                        closest_surrounding_tile[0], closest_surrounding_tile[1], run=False
                    )
                    yield from ensure_facing_direction(get_tile_direction(closest_tile))
                except BotModeError:
                    self.checked_tiles.append(closest_tile)
