import yaml
from enum import Enum
from modules.roms import ROM
from dataclasses import dataclass
from typing import Union, Tuple, Optional, Callable, List
from modules.context import context
from modules.battle_strategies import SafariTurnAction
from modules.pokemon import Pokemon
from modules.runtime import get_data_path
from modules.memory import read_symbol
from modules.files import make_string_safe_for_file_name
from modules.map_data import MapFRLG, MapRSE


class SafariHuntingMode(Enum):
    FISHING = "Fishing"
    SPIN = "Spin"
    SWEET_SCENT = "Sweet Scent"
    SURF = "Surf"


class SafariHuntingObject:
    OLD_ROD = "Old Rod"
    GOOD_ROD = "Good Rod"
    SUPER_ROD = "Super Rod"


@dataclass(frozen=True)
class SafariCatchingLocation:
    name: str
    map_location: Union[MapFRLG, MapRSE]
    tile_location: Tuple[int, int]
    mode: SafariHuntingMode
    hunting_object: SafariHuntingObject = None
    availability: Callable[[object], bool] = lambda context: True


class SafariPokemon(Enum):
    """Enum for Pokémon locations and strategies in the Safari Zone."""

    NIDORAN_F = SafariCatchingLocation("Nidoran♀", MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN)
    NIDORINA = SafariCatchingLocation("Nidorina", MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN)
    NIDORAN_M = SafariCatchingLocation("Nidoran♂", MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN)
    NIDORINO = SafariCatchingLocation("Nidorino", MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN)
    PARAS = SafariCatchingLocation("Paras", MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN)
    PARASECT = SafariCatchingLocation("Parasect", MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN)
    VENONAT = SafariCatchingLocation("Venonat", MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN)
    VENOMOTH = SafariCatchingLocation("Venomoth", MapFRLG.SAFARI_ZONE_NORTH, (35, 30), SafariHuntingMode.SPIN)
    DODUO = SafariCatchingLocation("Doduo", MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN)
    RHYHORN = SafariCatchingLocation("Rhyhorn", MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN)
    EXEGGCUTE = SafariCatchingLocation("Exeggcute", MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN)
    TAUROS = SafariCatchingLocation("Tauros", MapFRLG.SAFARI_ZONE_WEST, (15, 27), SafariHuntingMode.SPIN)
    CHANSEY = SafariCatchingLocation("Chansey", MapFRLG.SAFARI_ZONE_NORTH, (35, 30), SafariHuntingMode.SPIN)
    KANGASKHAN = SafariCatchingLocation("Kangaskhan", MapFRLG.SAFARI_ZONE_EAST, (8, 9), SafariHuntingMode.SPIN)
    PINSIR = SafariCatchingLocation(
        "Pinsir",
        MapFRLG.SAFARI_ZONE_CENTER,
        (24, 27),
        SafariHuntingMode.SPIN,
        availability=lambda rom: context.rom.is_lg,
    )
    SCYTHER = SafariCatchingLocation(
        "Scyther",
        MapFRLG.SAFARI_ZONE_CENTER,
        (24, 27),
        SafariHuntingMode.SPIN,
        availability=lambda rom: context.rom.is_fr,
    )

    POLIWAG = SafariCatchingLocation(
        "Poliwag", MapFRLG.SAFARI_ZONE_CENTER, (32, 19), SafariHuntingMode.FISHING, SafariHuntingObject.GOOD_ROD
    )
    MAGIKARP = SafariCatchingLocation(
        "Magikarp", MapFRLG.SAFARI_ZONE_CENTER, (32, 19), SafariHuntingMode.FISHING, SafariHuntingObject.OLD_ROD
    )
    GOLDEEN = SafariCatchingLocation(
        "Goldeen", MapFRLG.SAFARI_ZONE_CENTER, (32, 19), SafariHuntingMode.FISHING, SafariHuntingObject.GOOD_ROD
    )
    SEAKING = SafariCatchingLocation(
        "Seaking", MapFRLG.SAFARI_ZONE_CENTER, (32, 19), SafariHuntingMode.FISHING, SafariHuntingObject.SUPER_ROD
    )
    DRATINI = SafariCatchingLocation(
        "Dratini", MapFRLG.SAFARI_ZONE_CENTER, (32, 19), SafariHuntingMode.FISHING, SafariHuntingObject.SUPER_ROD
    )
    DRAGONAIR = SafariCatchingLocation(
        "Dragonair", MapFRLG.SAFARI_ZONE_CENTER, (32, 19), SafariHuntingMode.FISHING, SafariHuntingObject.SUPER_ROD
    )
    PSYDUCK = SafariCatchingLocation(
        "Psyduck",
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 18),
        SafariHuntingMode.SURF,
        availability=lambda rom: context.rom.is_fr,
    )
    SLOWPOKE = SafariCatchingLocation(
        "Slowpoke",
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 18),
        SafariHuntingMode.SURF,
        availability=lambda rom: context.rom.is_lg,
    )

    @staticmethod
    def available_pokemon(rom: ROM) -> list:
        return [pokemon for pokemon in SafariPokemon if pokemon.value.availability(rom)]


class FRLGSafariStrategy:
    NO_STRATEGY = {
        SafariPokemon.MAGIKARP,
        SafariPokemon.NIDORAN_F,
        SafariPokemon.NIDORAN_M,
        SafariPokemon.PARAS,
        SafariPokemon.VENONAT,
        SafariPokemon.PSYDUCK,
        SafariPokemon.POLIWAG,
        SafariPokemon.SLOWPOKE,
        SafariPokemon.DODUO,
        SafariPokemon.GOLDEEN,
        SafariPokemon.NIDORINO,
        SafariPokemon.NIDORINA,
        SafariPokemon.EXEGGCUTE,
        SafariPokemon.RHYHORN,
    }
    LOOKUP_4_OR_6 = {SafariPokemon.SEAKING}
    LOOKUP_5_OR_6 = {SafariPokemon.PARASECT, SafariPokemon.VENOMOTH}
    LOOKUP_3 = {SafariPokemon.DRATINI}
    LOOKUP_1_OR_2 = {SafariPokemon.CHANSEY}
    LOOKUP_2 = {
        SafariPokemon.KANGASKHAN,
        SafariPokemon.SCYTHER,
        SafariPokemon.PINSIR,
        SafariPokemon.TAUROS,
        SafariPokemon.DRAGONAIR,
    }

    @classmethod
    def get_strategy_file(cls, pokemon: Pokemon, has_been_baited: bool) -> Union[str, None]:
        """
        Determines the strategy file based on the Pokémon name and baited status.
        """
        safari_pokemon = get_safari_pokemon(pokemon.species.name)
        match safari_pokemon:
            case safari_pokemon if safari_pokemon in cls.NO_STRATEGY:
                return None
            case safari_pokemon if safari_pokemon in cls.LOOKUP_4_OR_6:
                file_name = "lookup-4.yml" if not has_been_baited else "lookup-6.yml"
            case safari_pokemon if safari_pokemon in cls.LOOKUP_5_OR_6:
                file_name = "lookup-5.yml" if not has_been_baited else "lookup-6.yml"
            case safari_pokemon if safari_pokemon in cls.LOOKUP_3:
                file_name = "lookup-3.yml"
            case safari_pokemon if safari_pokemon in cls.LOOKUP_1_OR_2:
                file_name = "lookup-1.yml" if not has_been_baited else "lookup-2.yml"
            case safari_pokemon if safari_pokemon in cls.LOOKUP_2:
                file_name = "lookup-2.yml"
            case _:
                raise RuntimeError(f"Pokemon `{safari_pokemon.name}` doesn't have a safari strategy.")

        return get_data_path() / "frlg_safari_catch_strategies" / file_name

    @staticmethod
    def convert_action_to_turn_action(action: str) -> Tuple["SafariTurnAction", bool]:
        """
        Converts a string action into a SafariTurnAction and additional context if needed.
        """
        match action:
            case "bait":
                return SafariTurnAction.Bait, False
            case "ball":
                return SafariTurnAction.ThrowBall, False
            case "rock":
                return SafariTurnAction.Rock, True
            case _:
                raise ValueError(f"Invalid action '{action}' returned from strategy.")


def get_safari_strategy_action(
    pokemon: Pokemon, number_of_balls: int, index: int, has_been_baited: bool
) -> Tuple["SafariTurnAction", Union[bool, None]]:
    """
    Get the safari strategy action based on the number of balls and an action index.
    """
    file_path = FRLGSafariStrategy.get_strategy_file(pokemon, has_been_baited)

    if file_path is None:
        return SafariTurnAction.ThrowBall, None

    safari_data = load_safari_data(file_path)

    if number_of_balls not in safari_data:
        raise ValueError(f"No strategy found for {number_of_balls} balls.")

    actions = safari_data[number_of_balls]
    action_str = actions[index]

    return FRLGSafariStrategy.convert_action_to_turn_action(action_str)


def load_safari_data(file_path: str) -> dict:
    """
    Loads the safari strategy data from a YAML file.
    """
    try:
        with open(file_path, "r") as f:
            safari_data = yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"The file {file_path} was not found.")
    except yaml.YAMLError as e:
        raise RuntimeError(f"Failed to parse YAML file {file_path}: {e}")

    return safari_data


def is_watching_carefully() -> bool:
    """
    We do not intentionally check on the bait count to mimic a real user behavior
    We juste check it to know if the monster was watching carefully or eating the previous turn
    This information is displayed on the player screen
    """
    return context.emulator.read_bytes(0x0200008A, length=1)[0] == 0


def get_safari_balls_left() -> int:
    return read_symbol("gNumSafariBalls")[0]


def get_safari_pokemon(name: str) -> Optional[SafariPokemon]:
    name = make_string_safe_for_file_name(name).upper()
    for safari_pokemon in SafariPokemon:
        if safari_pokemon.name == name:
            return safari_pokemon

    return None


def get_navigation_path(
    target_map: MapFRLG, tile_location: Tuple[int, int]
) -> List[Tuple[MapFRLG, Tuple[int, int], Optional[str]]]:
    """
    Returns the navigation path for a given target map.

    Args:
        target_map (MapFRLG): The target map for which the navigation path is required.

    Returns:
        List[Tuple[MapFRLG, Tuple[int, int], Optional[str]]]: A list of tuples, where each tuple represents a step
        in the navigation path. Each tuple contains:
        - A MapFRLG enum value for the destination map.
        - A tuple of (x, y) coordinates for the target location.
        - An optional string for the direction to move.
    """
    navigation_paths = {
        MapFRLG.SAFARI_ZONE_CENTER: [
            (MapFRLG.SAFARI_ZONE_CENTER, tile_location, None),
        ],
        MapFRLG.SAFARI_ZONE_EAST: [
            (MapFRLG.SAFARI_ZONE_CENTER, (42, 16), "Right"),
            (MapFRLG.SAFARI_ZONE_EAST, tile_location, None),
        ],
        MapFRLG.SAFARI_ZONE_NORTH: [
            (MapFRLG.SAFARI_ZONE_CENTER, (42, 16), "Right"),
            (MapFRLG.SAFARI_ZONE_EAST, (9, 9), "Left"),
            (MapFRLG.SAFARI_ZONE_NORTH, tile_location, None),
        ],
        MapFRLG.SAFARI_ZONE_WEST: [
            (MapFRLG.SAFARI_ZONE_CENTER, (42, 16), "Right"),
            (MapFRLG.SAFARI_ZONE_EAST, (9, 9), "Left"),
            (MapFRLG.SAFARI_ZONE_NORTH, (21, 33), "Down"),
            (MapFRLG.SAFARI_ZONE_WEST, tile_location, None),
        ],
    }

    path = navigation_paths.get(target_map)
    if path is None:
        console.print(f"Error: No navigation path defined for {target_map}.")
        return []

    return path
