from dataclasses import dataclass
from typing import Generator

from modules.context import context
from modules.items import get_item_by_name, get_item_bag
from modules.map import get_map_data
from modules.map_data import MapRSE
from modules.player import get_player, get_player_avatar, AvatarFlags
from modules.pokemon import get_party
from . import BattleAction
from ._interface import BotMode, BotModeError
from .util import (
    ensure_facing_direction,
    fish,
    navigate_to,
    register_key_item,
    wait_for_task_to_start_and_finish,
    walk_one_tile,
)
from ..clock import ClockTime, get_clock_time
from ..encounter import EncounterInfo
from ..memory import get_event_flag

# How many times the bot tries to fish on the same tile before it deems it
# a non-Feebas tile and moves on.
maximum_number_of_fishing_attempts_per_tile = 3


@dataclass
class FishingSpot:
    id: int
    coordinates: tuple[int, int]
    fishing_attempts: int


class FishingSpotList:
    def __init__(self, map_height: int):
        self._fishing_spots: dict[int, FishingSpot] = {}
        self._next_id: int = 0
        self._map_height: int = map_height

    def __contains__(self, item):
        if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], int) and isinstance(item[1], int):
            return self._index(item) in self._fishing_spots
        else:
            return NotImplemented

    def add(self, coordinates: tuple[int, int]):
        self._fishing_spots[self._index(coordinates)] = FishingSpot(self._next_id, coordinates, 0)
        self._next_id += 1

    def get_by_coordinates(self, coordinates: tuple[int, int]) -> FishingSpot | None:
        index = self._index(coordinates)
        if index in self._fishing_spots:
            return self._fishing_spots[index]
        else:
            return None

    def get_next_untested(self) -> FishingSpot | None:
        for index in self._fishing_spots:
            if self._fishing_spots[index].fishing_attempts < maximum_number_of_fishing_attempts_per_tile:
                return self._fishing_spots[index]
        return None

    def reset(self, can_use_waterfall: bool) -> None:
        for index in self._fishing_spots:
            if not can_use_waterfall and self._fishing_spots[index].coordinates[1] < 28:
                self._fishing_spots[index].fishing_attempts = maximum_number_of_fishing_attempts_per_tile
            else:
                self._fishing_spots[index].fishing_attempts = 0

    def _index(self, coordinates: tuple[int, int]) -> int:
        return coordinates[1] * self._map_height + coordinates[0]


def _tile_is_accessible(x: int, y: int) -> bool:
    tile = get_map_data(MapRSE.ROUTE119, (x, y))
    return tile.is_surfable and not tile.collision and tile.tile_type != "Waterfall" and tile.has_encounters


def _get_fishing_spots() -> FishingSpotList:
    route_119_map = get_map_data(MapRSE.ROUTE119, (0, 0))
    result = FishingSpotList(route_119_map.map_size[1])
    for y in range(18, route_119_map.map_size[1]):
        for x in range(route_119_map.map_size[0]):
            if _tile_is_accessible(x, y):
                result.add((x, y))
    return result


def _get_nearest_accessible_neighbour(
    target_coordinates: tuple[int, int], current_position: tuple[int, int]
) -> tuple[tuple[int, int], str]:
    candidates = (
        (target_coordinates[0], target_coordinates[1] - 1, "Down"),
        (target_coordinates[0] + 1, target_coordinates[1], "Left"),
        (target_coordinates[0], target_coordinates[1] + 1, "Up"),
        (target_coordinates[0] - 1, target_coordinates[1], "Right"),
    )

    shortest_distance = 9999
    shortest_distance_tile = (0, 0)
    shortest_distance_direction = ""
    for x, y, direction in candidates:
        if _tile_is_accessible(x, y):
            distance = abs(current_position[0] - x) + abs(current_position[1] - y)
            if distance < shortest_distance:
                shortest_distance = distance
                shortest_distance_tile = (x, y)
                shortest_distance_direction = direction
    return shortest_distance_tile, shortest_distance_direction


class FeebasMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Feebas"

    @staticmethod
    def is_selectable() -> bool:
        return (
            context.rom.is_rse
            and get_player_avatar().map_group_and_number in (MapRSE.ROUTE119,)
            and AvatarFlags.Surfing in get_player_avatar().flags
        )

    def __init__(self):
        self._found_feebas: ClockTime | None = None
        self._fishing_spots: FishingSpotList = _get_fishing_spots()
        self._can_use_waterfall: bool = False
        super().__init__()

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        if encounter.type.is_fishing:
            # Feebas tiles change each in-game day (based on RTC)
            if self._found_feebas is not None and self._found_feebas.days != get_clock_time().days:
                self._found_feebas = None
                self._fishing_spots.reset(self._can_use_waterfall)

            if encounter.pokemon.species.name == "Feebas":
                self._found_feebas = get_clock_time()
            else:
                spot = self._fishing_spots.get_by_coordinates(get_player_avatar().map_location_in_front.local_position)
                if spot is not None:
                    spot.fishing_attempts += 1

        return None

    def run(self) -> Generator:
        if not get_player_avatar().flags.Surfing:
            raise BotModeError("Player is not surfing, only start this mode while surfing in any water at Route 119.")

        if context.rom.is_emerald and get_party()[0].ability.name not in ["Sticky Hold", "Suction Cups"]:
            context.message = "Warning: It is recommended to put a Pokémon with the ability Sticky Hold or Suction Cups as the first Pokémon in your party."

        item_bag = get_item_bag()
        if item_bag.quantity_of(get_item_by_name("Old Rod")) == 0:
            context.message = "Warning: It is recommended that you get the Old Rod to fish."
        elif get_player().registered_item is None or get_player().registered_item.name != "Old Rod":
            yield from register_key_item(get_item_by_name("Old Rod"))

        if (
            item_bag.quantity_of(get_item_by_name("Old Rod")) == 0
            and item_bag.quantity_of(get_item_by_name("Good Rod")) == 0
            and get_item_by_name("Super Rod") == 0
        ):
            raise BotModeError("Error: You cannot use this mode without having a fishing rod.")

        if get_event_flag("BADGE08_GET"):
            for pokemon in get_party():
                for learned_move in pokemon.moves:
                    if learned_move.move.name == "Waterfall":
                        self._can_use_waterfall = True
                        break

        if not self._can_use_waterfall:
            if not get_event_flag("BADGE08_GET"):
                context.message = "Warning: You do not have the Rain Badge, so you cannot use Waterfall. There will be some water tiles that we cannot reach."
            else:
                context.message = "Warning: You do not have a Pokémon that knows Waterfall. There will be some water tiles that we cannot reach."

        self._fishing_spots.reset(self._can_use_waterfall)

        # Mark all fishing spots before the player as tested. This means that we will always
        # start with the tile that the player is facing -- in case the player already knows
        # which tile is the Feebas tile, for example because they just used the mode and
        # briefly switched back to Manual mode.
        player_location = get_player_avatar().map_location_in_front.local_position
        if player_location in self._fishing_spots:
            while True:
                spot = self._fishing_spots.get_next_untested()
                if spot is None or spot.coordinates == player_location:
                    break
                else:
                    spot.fishing_attempts = maximum_number_of_fishing_attempts_per_tile

        while True:
            if not self._found_feebas:
                player_location = get_player_avatar().map_location_in_front.local_position
                target_spot = self._fishing_spots.get_next_untested()

                # This might happen if all tiles have been checked and no Feebas has been found.
                # Since there's no guarantee that we will get a Feebas encounter on a Feebas tile
                # within the threshold, this could happen.
                if target_spot is None:
                    self._fishing_spots.reset(self._can_use_waterfall)
                    continue

                if target_spot.coordinates != player_location:
                    # Move from the lower lake to the upper lake.
                    if target_spot.coordinates[1] < 98 <= player_location[1]:
                        yield from navigate_to(MapRSE.ROUTE119, (25, 107))
                        yield from walk_one_tile("Right")
                        yield from navigate_to(MapRSE.ROUTE119, (24, 42))
                        yield from ensure_facing_direction("Left")
                        yield from wait_for_task_to_start_and_finish("Task_SurfFieldEffect", "A")
                        yield

                    # Move from upper lake to the lower lake.
                    if target_spot.coordinates[1] >= 98 > player_location[1]:
                        yield from navigate_to(MapRSE.ROUTE119, (25, 43))
                        yield from walk_one_tile("Up")
                        yield from navigate_to(MapRSE.ROUTE119, (26, 107))
                        yield from ensure_facing_direction("Left")
                        yield from wait_for_task_to_start_and_finish("Task_SurfFieldEffect", "A")
                        yield

                    # Swim up the waterfall is necessary.
                    if target_spot.coordinates[1] < 28 < player_location[1]:
                        yield from navigate_to(MapRSE.ROUTE119, (18, 29))
                        yield from ensure_facing_direction("Up")
                        context.emulator.press_button("A")
                        yield from wait_for_task_to_start_and_finish("Task_UseWaterfall", "A")
                        yield

                    # Surf to the closest tile next to the target.
                    target_tile, direction = _get_nearest_accessible_neighbour(target_spot.coordinates, player_location)
                    yield from navigate_to(MapRSE.ROUTE119, target_tile)
                    yield from ensure_facing_direction(direction)

            yield from fish()
