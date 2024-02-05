from enum import Enum

from modules.context import context
from modules.memory import read_symbol, unpack_uint32, unpack_uint16


def get_map_cursor() -> tuple[int, int] | None:
    if context.rom.is_frlg:
        symbol_name = "sMapCursor"
        offset = 0
    elif context.rom.is_emerald:
        symbol_name = "sRegionMap"
        offset = 0x54
    else:
        symbol_name = "gRegionMap"
        offset = 0x54

    pointer = unpack_uint32(read_symbol(symbol_name))
    if pointer == 0:
        return None

    data = context.emulator.read_bytes(pointer + offset, 4)
    return unpack_uint16(data[0:2]), unpack_uint16(data[2:4])


def get_map_region() -> int:
    if context.rom.is_rse:
        return 0

    offset = 19 + 19 + 3000 + 2048 * 3 + 4
    pointer = unpack_uint32(read_symbol("sRegionMap"))
    if pointer == 0:
        return 0

    return context.emulator.read_bytes(pointer + offset, 1)[0]


class FlyDestinationRSE(Enum):
    LittlerootTown = (5, 13)
    OldaleTown = (5, 11)
    PetalburgCity = (2, 11)
    DewfordTown = (3, 16)
    SlateportCity = (9, 12)
    MauvilleCity = (9, 8)
    VerdanturfTown = (5, 8)
    RustboroCity = (1, 8)
    FallarborTown = (4, 2)
    LavaridgeTown = (6, 5)
    FortreeCity = (13, 2)
    LilycoveCity = (19, 5)
    MossdeepCity = (25, 7)
    SootopolisCity = (22, 9)
    PokemonLeague = (28, 10)
    EverGrandeCity = (28, 11)
    PacifidlogTown = (18, 12)

    def get_flag_name(self) -> str:
        return {
            self.LittlerootTown: "VISITED_LITTLEROOT_TOWN",
            self.OldaleTown: "VISITED_OLDALE_TOWN",
            self.PetalburgCity: "VISITED_PETALBURG_CITY",
            self.DewfordTown: "VISITED_DEWFORD_TOWN",
            self.SlateportCity: "VISITED_SLATEPORT_CITY",
            self.MauvilleCity: "VISITED_MAUVILLE_CITY",
            self.VerdanturfTown: "VISITED_VERDANTURF_TOWN",
            self.RustboroCity: "VISITED_RUSTBORO_CITY",
            self.FallarborTown: "VISITED_FALLARBOR_TOWN",
            self.LavaridgeTown: "VISITED_LAVARIDGE_TOWN",
            self.FortreeCity: "VISITED_FORTREE_CITY",
            self.LilycoveCity: "VISITED_LILYCOVE_CITY",
            self.MossdeepCity: "VISITED_MOSSDEEP_CITY",
            self.SootopolisCity: "VISITED_SOOTOPOLIS_CITY",
            self.PokemonLeague: "LANDMARK_POKEMON_LEAGUE" if context.rom.is_emerald else "SYS_POKEMON_LEAGUE_FLY",
            self.EverGrandeCity: "VISITED_EVER_GRANDE_CITY",
            self.PacifidlogTown: "VISITED_PACIFIDLOG_TOWN",
        }[self]

    def get_map_region(self) -> int:
        return 0


class FlyDestinationFRLG(Enum):
    PalletTown = (4, 11)
    ViridianCity = (4, 8)
    PewterCity = (4, 4)
    MtMoon = (8, 3)
    CeruleanCity = (14, 3)
    VermilionCity = (14, 9)
    RockTunnel = (18, 3)
    LavenderTown = (18, 6)
    CeladonCity = (11, 6)
    SaffronCity = (14, 6)
    FuchsiaCity = (12, 12)
    CinnabarIsland = (4, 14)
    IndigoPlateau = (2, 3)

    OneIsland = (1, 8)
    TwoIsland = (9, 9)
    ThreeIsland = (18, 12)
    FourIsland = (3, 4)
    FiveIsland = (16, 11)
    SixIsland = (17, 5)
    SevenIsland = (5, 8)

    def get_flag_name(self) -> str:
        return {
            self.PalletTown: "WORLD_MAP_PALLET_TOWN",
            self.ViridianCity: "WORLD_MAP_VIRIDIAN_CITY",
            self.PewterCity: "WORLD_MAP_PEWTER_CITY",
            self.MtMoon: "WORLD_MAP_ROUTE4_POKEMON_CENTER_1F",
            self.CeruleanCity: "WORLD_MAP_CERULEAN_CITY",
            self.VermilionCity: "WORLD_MAP_VERMILION_CITY",
            self.RockTunnel: "WORLD_MAP_ROUTE10_POKEMON_CENTER_1F",
            self.LavenderTown: "WORLD_MAP_LAVENDER_TOWN",
            self.CeladonCity: "WORLD_MAP_CELADON_CITY",
            self.SaffronCity: "WORLD_MAP_SAFFRON_CITY",
            self.FuchsiaCity: "WORLD_MAP_FUCHSIA_CITY",
            self.CinnabarIsland: "WORLD_MAP_CINNABAR_ISLAND",
            self.IndigoPlateau: "WORLD_MAP_INDIGO_PLATEAU_EXTERIOR",
            self.OneIsland: "WORLD_MAP_ONE_ISLAND",
            self.TwoIsland: "WORLD_MAP_TWO_ISLAND",
            self.ThreeIsland: "WORLD_MAP_THREE_ISLAND",
            self.FourIsland: "WORLD_MAP_FOUR_ISLAND",
            self.FiveIsland: "WORLD_MAP_FIVE_ISLAND",
            self.SixIsland: "WORLD_MAP_SIX_ISLAND",
            self.SevenIsland: "WORLD_MAP_SEVEN_ISLAND",
        }[self]

    def get_map_region(self) -> int:
        if self in (self.OneIsland, self.TwoIsland, self.ThreeIsland):
            return 1
        elif self in (self.FourIsland, self.FiveIsland):
            return 2
        elif self in (self.SixIsland, self.SevenIsland):
            return 3
        else:
            return 0
