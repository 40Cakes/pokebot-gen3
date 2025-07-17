from dataclasses import dataclass

from modules.context import context
from modules.items import Pokeblock, PokeblockColour
from modules.map_data import MapRSE, MapGroupRSE
from modules.memory import read_symbol, unpack_uint16
from modules.player import get_player_location


@dataclass
class PokeblockFeeder:
    on_map: MapRSE
    coordinates: tuple[int, int]
    step_counter: int
    pokeblock: Pokeblock


def get_all_active_pokeblock_feeders() -> list[PokeblockFeeder]:
    if context.rom.is_frlg:
        return []

    data = read_symbol("sPokeblockFeeders" if context.rom.is_emerald else "gPokeblockFeeders")
    result = []
    number_of_feeders = 10
    for index in range(number_of_feeders):
        x = unpack_uint16(data[index * 0x10 + 0 : index * 0x10 + 2])
        y = unpack_uint16(data[index * 0x10 + 2 : index * 0x10 + 4])
        map_number = data[index * 0x10 + 4]
        if x == 0 and y == 0 and map_number == 0:
            continue

        block_data = data[index * 0x10 + 8 : index * 0x10 + 16]
        result.append(
            PokeblockFeeder(
                on_map=MapRSE((MapGroupRSE.SpecialArea.value, map_number)),
                coordinates=(x - 7, y - 7),
                step_counter=data[index * 0x10 + 5],
                pokeblock=Pokeblock(PokeblockColour(block_data[0]), *block_data[1:7]),
            )
        )

    return result


def get_active_pokeblock_feeder_for_location(
    location: tuple[MapRSE | tuple[int, int], tuple[int, int]] | None = None,
) -> PokeblockFeeder | None:
    if location is None:
        location = get_player_location()

    for feeder in get_all_active_pokeblock_feeders():
        if feeder.on_map != location[0]:
            continue
        if abs(feeder.coordinates[0] - location[1][0]) + abs(feeder.coordinates[1] - location[1][1]) <= 5:
            return feeder

    return None
