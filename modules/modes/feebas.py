import math
from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter
from modules.items import get_item_bag, get_item_by_name
from modules.map_data import MapRSE
from modules.player import get_player, get_player_avatar
from modules.pokemon import get_opponent
from . import BattleAction
from ._asserts import assert_item_exists_in_bag
from ._interface import BotMode, BotModeError
from ._util import (
    navigate_to,
    ensure_facing_direction,
    register_key_item,
    fish,
)
from ..console import console
from ..map import get_map_all_tiles, get_map_data

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
        self.tile_threshold: int = 3
        self.tile_checked: int = 0
        self.checked_tiles: list[tuple[int, int]] = bad_tiles
        self.surfable_tiles: list[tuple[int, int]] = [
            tile.local_position for tile in get_map_all_tiles() if (tile.is_surfable and tile.local_position[1] > 28)
        ]
        super().__init__()

    def on_battle_started(self) -> BattleAction | None:
        return handle_encounter(get_opponent(), disable_auto_battle=True)

    def get_closest_tile(self, tiles: list[tuple[int, int]]) -> tuple[int, int] | None:
        console.print("Finding closest tile...")
        closest = min(
            tiles,
            key=lambda tile: math.hypot(
                get_player_avatar().local_coordinates[1] - tile[1],
                get_player_avatar().local_coordinates[0] - tile[0],
            ),
        )
        console.print(f"Closest tile is: ({closest[0]}, {closest[1]})")
        return closest

    def get_closest_surrounding_tile(self, tile: tuple[int, int]) -> tuple[int, int] | None:
        console.print(f"Finding surfable, surrounding tiles for tile: {tile}...")
        if valid_surrounding_tiles := [
            get_map_data(
                get_player_avatar().map_group_and_number[0], get_player_avatar().map_group_and_number[1], check
            ).local_position
            for check in [
                (tile[0] + 1, tile[1]),
                (tile[0], tile[1] + 1),
                (tile[0] - 1, tile[1]),
                (tile[0], tile[1] - 1),
            ]
            if get_map_data(
                get_player_avatar().map_group_and_number[0], get_player_avatar().map_group_and_number[1], check
            ).is_surfable
        ]:
            for surrounding_tile in valid_surrounding_tiles:
                console.print(f"Found valid surrounding tile: {surrounding_tile}")
            return self.get_closest_tile(valid_surrounding_tiles)
        else:
            return None

    def get_tile_direction(self, tile: tuple[int, int]) -> str | None:
        tile_coords = tile
        player_coords = get_player_avatar().local_coordinates

        direction = None
        if tile_coords[0] < player_coords[0]:
            direction = "Left"
        if tile_coords[1] < player_coords[1]:
            direction = "Up"
        if tile_coords[0] > player_coords[0]:
            direction = "Right"
        if tile_coords[1] > player_coords[1]:
            direction = "Down"

        console.print(f"The player needs to look {direction} to face {tile_coords} from {player_coords}...")
        return direction

    def run(self) -> Generator:
        from ..stats import total_stats

        if not get_player_avatar().flags.Surfing:
            raise BotModeError("Player is not surfing, only start this mode while surfing in any water at Route 119.")

        rod_names = ("Old Rod", "Good Rod", "Super Rod")
        assert_item_exists_in_bag(rod_names, "You do not own any fishing rod, so you cannot fish.")
        # Register any rod, doesn't matter with Feebas
        if get_player().registered_item is None or get_player().registered_item.name not in rod_names:
            for rod_name in rod_names:
                if get_item_bag().quantity_of(get_item_by_name(rod_name)) > 0:
                    yield from register_key_item(get_item_by_name(rod_name))
                    break

        total_stats.remove_session_pokemon("Feebas")

        while True:
            if self.tile_checked < self.tile_threshold or self.feebas_found:
                total_encounters = total_stats.get_total_stats()["totals"]["encounters"]
                while total_encounters == total_stats.get_total_stats()["totals"]["encounters"]:
                    yield from fish()
                self.tile_checked += 1

            elif "Feebas" in total_stats.get_session_pokemon():
                console.print("Found a Feebas tile!")
                self.feebas_found = True

            else:
                self.tile_checked = 0
                console.print(f"Feebas not on tile: {get_player_avatar().map_location_in_front.local_position}")
                self.checked_tiles.append(get_player_avatar().map_location_in_front.local_position)

                closest_tile = self.get_closest_tile(
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

                closest_surrounding_tile = self.get_closest_surrounding_tile(closest_tile)
                try:
                    yield from navigate_to(closest_surrounding_tile[0], closest_surrounding_tile[1], run=False)
                    yield from ensure_facing_direction(self.get_tile_direction(closest_tile))
                except BotModeError:
                    self.checked_tiles.append(closest_tile)
