from modules.map import MapLocation
from modules.map_data import MapFRLG, PokemonCenter, MapRSE, get_map_enum
from modules.map_path import calculate_path, PathFindingError
from modules.modes import BotModeError
from modules.player import get_player_location

_closest_pokemon_centers: dict[MapFRLG | MapRSE, list[PokemonCenter]] = {
    # Hoenn
    MapRSE.ROUTE101: [PokemonCenter.OldaleTown],
    MapRSE.ROUTE102: [PokemonCenter.OldaleTown, PokemonCenter.PetalburgCity],
    MapRSE.ROUTE103: [PokemonCenter.OldaleTown],
    MapRSE.ROUTE104: [PokemonCenter.PetalburgCity, PokemonCenter.RustboroCity],
    MapRSE.ROUTE105: [PokemonCenter.PetalburgCity, PokemonCenter.DewfordTown],
    MapRSE.ROUTE106: [PokemonCenter.DewfordTown],
    MapRSE.ROUTE107: [PokemonCenter.DewfordTown],
    MapRSE.ROUTE108: [PokemonCenter.DewfordTown],
    MapRSE.ROUTE109: [PokemonCenter.SlateportCity],
    MapRSE.ROUTE110: [PokemonCenter.SlateportCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE111: [PokemonCenter.MauvilleCity, PokemonCenter.MauvilleCity, PokemonCenter.FallarborTown],
    MapRSE.ROUTE112: [PokemonCenter.LavaridgeTown, PokemonCenter.MauvilleCity, PokemonCenter.FallarborTown],
    MapRSE.ROUTE113: [PokemonCenter.FallarborTown],
    MapRSE.ROUTE114: [PokemonCenter.FallarborTown],
    MapRSE.ROUTE115: [PokemonCenter.RustboroCity],
    MapRSE.ROUTE116: [PokemonCenter.RustboroCity],
    MapRSE.ROUTE117: [PokemonCenter.MauvilleCity, PokemonCenter.VerdanturfTown],
    MapRSE.ROUTE118: [PokemonCenter.MauvilleCity],
    MapRSE.ROUTE119: [PokemonCenter.FortreeCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE120: [PokemonCenter.FortreeCity],
    MapRSE.ROUTE121: [PokemonCenter.LilycoveCity],
    MapRSE.ROUTE122: [PokemonCenter.LilycoveCity],
    MapRSE.ROUTE123: [PokemonCenter.LilycoveCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE124: [PokemonCenter.LilycoveCity, PokemonCenter.MossdeepCity],
    MapRSE.ROUTE125: [PokemonCenter.MossdeepCity],
    MapRSE.ROUTE126: [PokemonCenter.MossdeepCity],
    MapRSE.ROUTE127: [PokemonCenter.MossdeepCity],
    MapRSE.ROUTE128: [PokemonCenter.EvergrandeCity],
    MapRSE.ROUTE129: [PokemonCenter.EvergrandeCity],
    MapRSE.ROUTE130: [PokemonCenter.PacifidlogTown],
    MapRSE.ROUTE131: [PokemonCenter.PacifidlogTown],
    MapRSE.ROUTE132: [PokemonCenter.PacifidlogTown],
    MapRSE.ROUTE133: [PokemonCenter.PacifidlogTown, PokemonCenter.SlateportCity],
    MapRSE.ROUTE134: [PokemonCenter.SlateportCity],
    MapRSE.PETALBURG_CITY: [PokemonCenter.PetalburgCity],
    MapRSE.SLATEPORT_CITY: [PokemonCenter.SlateportCity],
    MapRSE.MAUVILLE_CITY: [PokemonCenter.MauvilleCity],
    MapRSE.RUSTBORO_CITY: [PokemonCenter.RustboroCity],
    MapRSE.FORTREE_CITY: [PokemonCenter.FortreeCity],
    MapRSE.LILYCOVE_CITY: [PokemonCenter.LilycoveCity],
    MapRSE.MOSSDEEP_CITY: [PokemonCenter.MossdeepCity],
    MapRSE.EVER_GRANDE_CITY: [PokemonCenter.EvergrandeCity],
    MapRSE.OLDALE_TOWN: [PokemonCenter.OldaleTown],
    MapRSE.DEWFORD_TOWN: [PokemonCenter.DewfordTown],
    MapRSE.LAVARIDGE_TOWN: [PokemonCenter.LavaridgeTown],
    MapRSE.FALLARBOR_TOWN: [PokemonCenter.FallarborTown],
    MapRSE.VERDANTURF_TOWN: [PokemonCenter.VerdanturfTown],
    MapRSE.PACIFIDLOG_TOWN: [PokemonCenter.PacifidlogTown],
    # Kanto
    MapFRLG.ROUTE1: [PokemonCenter.PalletTown, PokemonCenter.ViridianCity],
    MapFRLG.ROUTE2: [PokemonCenter.ViridianCity, PokemonCenter.PewterCity],
    MapFRLG.ROUTE3: [PokemonCenter.PewterCity, PokemonCenter.Route4],
    MapFRLG.ROUTE4: [PokemonCenter.Route4, PokemonCenter.CeruleanCity],
    MapFRLG.ROUTE6: [PokemonCenter.VermilionCity],
    MapFRLG.ROUTE7: [PokemonCenter.CeladonCity],
    MapFRLG.ROUTE9: [PokemonCenter.Route10],
    MapFRLG.ROUTE10: [PokemonCenter.Route10],
    MapFRLG.ROUTE11: [PokemonCenter.VermilionCity],
    MapFRLG.ROUTE18: [PokemonCenter.FuchsiaCity],
    MapFRLG.ROUTE19: [PokemonCenter.FuchsiaCity],
    MapFRLG.ROUTE20: [PokemonCenter.CinnabarIsland, PokemonCenter.FuchsiaCity],
    MapFRLG.ROUTE21_NORTH: [PokemonCenter.PalletTown, PokemonCenter.CinnabarIsland],
    MapFRLG.ROUTE21_SOUTH: [PokemonCenter.PalletTown, PokemonCenter.CinnabarIsland],
    MapFRLG.ROUTE22: [PokemonCenter.ViridianCity],
    MapFRLG.ROUTE24: [PokemonCenter.CeruleanCity],
    MapFRLG.VIRIDIAN_CITY: [PokemonCenter.ViridianCity],
    MapFRLG.PEWTER_CITY: [PokemonCenter.PewterCity],
    MapFRLG.CERULEAN_CITY: [PokemonCenter.CeruleanCity],
    MapFRLG.LAVENDER_TOWN: [PokemonCenter.LavenderTown],
    MapFRLG.VERMILION_CITY: [PokemonCenter.VermilionCity],
    MapFRLG.CELADON_CITY: [PokemonCenter.CeladonCity],
    MapFRLG.FUCHSIA_CITY: [PokemonCenter.FuchsiaCity],
    MapFRLG.CINNABAR_ISLAND: [PokemonCenter.CinnabarIsland],
    MapFRLG.SAFFRON_CITY: [PokemonCenter.SaffronCity],
}


def find_closest_pokemon_center(
    location: MapLocation | tuple[MapFRLG | MapRSE, tuple[int, int]] | None = None,
) -> PokemonCenter:
    if isinstance(location, MapLocation):
        training_spot_map = location.map_group_and_number
    elif location is not None:
        training_spot_map = location[0]
    else:
        training_spot_map = get_player_location()[0]
    pokemon_center = None
    path_length_to_pokemon_center = None

    if training_spot_map in _closest_pokemon_centers:
        for pokemon_center_candidate in _closest_pokemon_centers[training_spot_map]:
            try:
                path_to = calculate_path(location, pokemon_center_candidate.value)
                path_from = calculate_path(pokemon_center_candidate.value, location)
                path_length = len(path_to) + len(path_from)
                if path_length_to_pokemon_center is None or path_length < path_length_to_pokemon_center:
                    pokemon_center = pokemon_center_candidate
                    path_length_to_pokemon_center = path_length
            except PathFindingError:
                pass

    if pokemon_center is None:
        raise BotModeError("Could not find a suitable oath from here to a Pokemon Center nearby.")

    return pokemon_center


def map_has_pokemon_center_nearby(map_enum: MapFRLG | MapRSE | tuple[int, int]) -> bool:
    if isinstance(map_enum, tuple):
        map_enum = get_map_enum(map_enum)
    return map_enum in _closest_pokemon_centers
