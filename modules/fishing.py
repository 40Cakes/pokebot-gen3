from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, Optional

from modules.context import context
from modules.map import get_map_data
from modules.map_data import MapRSE
from modules.memory import get_save_block, unpack_uint16

if TYPE_CHECKING:
    from modules.pokemon import Pokemon


class FishingRod(Enum):
    OldRod = 0
    GoodRod = 1
    SuperRod = 2


class FishingResult(Enum):
    Encounter = auto()
    GotAway = auto()
    Unsuccessful = auto()


@dataclass
class FishingAttempt:
    rod: FishingRod
    result: FishingResult
    encounter: Optional["Pokemon"] = None

    def __eq__(self, other):
        if other is None:
            return False
        elif isinstance(other, FishingAttempt):
            return other.rod is self.rod and other.result is self.result and other.encounter == self.encounter
        else:
            return NotImplemented

    def to_dict(self) -> dict:
        return {
            "rod": self.rod.name,
            "result": self.result.name,
            "encounter": self.encounter.to_dict() if self.encounter is not None else None,
        }


_route119_fishing_spots = []


def get_feebas_tiles() -> list[tuple[int, int]]:
    if context.rom.is_emerald:
        offset = 0x2E68
    elif context.rom.is_rs:
        offset = 0x2DD4
    else:
        return []

    global _route119_fishing_spots
    if len(_route119_fishing_spots) == 0:
        route119 = get_map_data(MapRSE.ROUTE119, (0, 0))
        route119_tiles = route119.all_tiles()
        for y in range(139):
            for x in range(route119.map_size[0]):
                tile = route119_tiles[x][y]
                if tile.is_surfable and tile.tile_type != "Waterfall":
                    _route119_fishing_spots.append((x, y))

    seed = unpack_uint16(get_save_block(1, offset + 2, size=2))
    feebas_tiles = []
    n = 0
    while n < 6:
        seed = (1103515245 * seed + 12345) & 0xFFFF_FFFF
        spot_index = (seed >> 16) % len(_route119_fishing_spots)

        if spot_index == 0:
            spot_index = len(_route119_fishing_spots)

        if spot_index >= 4:
            feebas_tiles.append(_route119_fishing_spots[spot_index - 1])
            n += 1

    return feebas_tiles
