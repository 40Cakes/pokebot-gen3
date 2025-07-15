from dataclasses import dataclass
from enum import Enum
from typing import Union, Tuple, Optional, Callable, List, Dict

import yaml

from modules.battle_strategies import SafariTurnAction
from modules.context import context
from modules.files import make_string_safe_for_file_name
from modules.map_data import MapFRLG, MapRSE
from modules.memory import read_symbol, get_event_flag
from modules.modes._interface import BotModeError
from modules.player import get_player_avatar
from modules.pokemon import Pokemon, Species, get_species_by_name, get_opponent
from modules.pokemon_party import get_party
from modules.roms import ROM
from modules.runtime import get_data_path
from modules.tasks import get_global_script_context
from modules.items import Pokeblock, PokeblockType, get_pokeblocks
from collections import Counter


class SafariHuntingMode(Enum):
    FISHING = "Fishing"
    SPIN = "Spin"
    SWEET_SCENT = "Sweet Scent"
    SURF = "Surf"
    ROCK_SMASH = "Rock Smash"


class SafariHuntingObject:
    OLD_ROD = "Old Rod"
    GOOD_ROD = "Good Rod"
    SUPER_ROD = "Super Rod"


class PokeblockState(Enum):
    IGNORED = 1
    ENTHRALLED = 2
    CURIOUS = 3


@dataclass(frozen=True)
class SafariCatchingLocation:
    species: Species
    map_location: Union[MapFRLG, MapRSE]
    tile_location: Tuple[int, int]
    mode: SafariHuntingMode
    hunting_object: SafariHuntingObject = None
    availability: Callable[[], bool] = lambda: True

    def is_available(self) -> bool:
        return self.availability()


class SafariPokemon(Enum):
    """Enum for Pokémon locations and strategies in the Safari Zone."""

    def is_leaf_green() -> bool:
        return context.rom.is_lg

    def is_fire_red() -> bool:
        return context.rom.is_fr

    NIDORAN_F = SafariCatchingLocation(
        get_species_by_name("Nidoran♀"), MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN
    )
    NIDORINA = SafariCatchingLocation(
        get_species_by_name("Nidorina"), MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN
    )
    NIDORAN_M = SafariCatchingLocation(
        get_species_by_name("Nidoran♂"), MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN
    )
    NIDORINO = SafariCatchingLocation(
        get_species_by_name("Nidorino"), MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN
    )
    PARAS = SafariCatchingLocation(
        get_species_by_name("Paras"), MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN
    )
    PARASECT = SafariCatchingLocation(
        get_species_by_name("Parasect"), MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN
    )
    VENONAT = SafariCatchingLocation(
        get_species_by_name("Venonat"), MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN
    )
    VENOMOTH = SafariCatchingLocation(
        get_species_by_name("Venomoth"), MapFRLG.SAFARI_ZONE_NORTH, (35, 30), SafariHuntingMode.SPIN
    )
    DODUO = SafariCatchingLocation(
        get_species_by_name("Doduo"), MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN
    )
    RHYHORN = SafariCatchingLocation(
        get_species_by_name("Rhyhorn"), MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN
    )
    EXEGGCUTE = SafariCatchingLocation(
        get_species_by_name("Exeggcute"), MapFRLG.SAFARI_ZONE_CENTER, (24, 27), SafariHuntingMode.SPIN
    )
    TAUROS = SafariCatchingLocation(
        get_species_by_name("Tauros"), MapFRLG.SAFARI_ZONE_WEST, (15, 27), SafariHuntingMode.SPIN
    )
    CHANSEY = SafariCatchingLocation(
        get_species_by_name("Chansey"), MapFRLG.SAFARI_ZONE_NORTH, (35, 30), SafariHuntingMode.SPIN
    )
    KANGASKHAN = SafariCatchingLocation(
        get_species_by_name("Kangaskhan"), MapFRLG.SAFARI_ZONE_EAST, (29, 28), SafariHuntingMode.SPIN
    )
    PINSIR = SafariCatchingLocation(
        get_species_by_name("Pinsir"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (24, 27),
        SafariHuntingMode.SPIN,
        availability=is_leaf_green,
    )
    SCYTHER = SafariCatchingLocation(
        get_species_by_name("Scyther"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (24, 27),
        SafariHuntingMode.SPIN,
        availability=is_fire_red,
    )

    POLIWAG = SafariCatchingLocation(
        get_species_by_name("Poliwag"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 19),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.GOOD_ROD,
    )
    MAGIKARP = SafariCatchingLocation(
        get_species_by_name("Magikarp"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 19),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.OLD_ROD,
    )
    GOLDEEN = SafariCatchingLocation(
        get_species_by_name("Goldeen"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 19),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.GOOD_ROD,
    )
    SEAKING = SafariCatchingLocation(
        get_species_by_name("Seaking"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 19),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
    )
    DRATINI = SafariCatchingLocation(
        get_species_by_name("Dratini"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 19),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
    )
    DRAGONAIR = SafariCatchingLocation(
        get_species_by_name("Dragonair"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 19),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
    )
    PSYDUCK = SafariCatchingLocation(
        get_species_by_name("Psyduck"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 18),
        SafariHuntingMode.SURF,
        availability=is_fire_red,
    )
    SLOWPOKE = SafariCatchingLocation(
        get_species_by_name("Slowpoke"),
        MapFRLG.SAFARI_ZONE_CENTER,
        (32, 18),
        SafariHuntingMode.SURF,
        availability=is_leaf_green,
    )

    @staticmethod
    def available_pokemon() -> list:
        return [pokemon for pokemon in SafariPokemon if pokemon.value.availability()]


class SafariPokemonRSE(Enum):
    """Enum for Pokémon locations and strategies in the Safari Zone."""

    def emerald_and_elite_four_defeated() -> bool:
        elite_four_defeated = not get_event_flag("HIDE_SAFARI_ZONE_SOUTH_EAST_EXPANSION")
        return context.rom.is_emerald and elite_four_defeated

    PIKACHU = SafariCatchingLocation(
        get_species_by_name("Pikachu"),
        MapRSE.SAFARI_ZONE_SOUTH,
        (25, 30),
        SafariHuntingMode.SPIN,
    )
    ODDISH = SafariCatchingLocation(
        get_species_by_name("Oddish"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (5, 7),
        SafariHuntingMode.SPIN,
    )
    GLOOM = SafariCatchingLocation(
        get_species_by_name("Gloom"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (5, 7),
        SafariHuntingMode.SPIN,
    )
    DODUO = SafariCatchingLocation(
        get_species_by_name("Doduo"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (5, 7),
        SafariHuntingMode.SPIN,
    )
    DODRIO = SafariCatchingLocation(
        get_species_by_name("Dodrio"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (5, 7),
        SafariHuntingMode.SPIN,
    )
    RHYHORN = SafariCatchingLocation(
        get_species_by_name("Rhyhorn"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (5, 7),
        SafariHuntingMode.SPIN,
    )
    PINSIR = SafariCatchingLocation(
        get_species_by_name("Pinsir"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (5, 7),
        SafariHuntingMode.SPIN,
    )
    NATU = SafariCatchingLocation(
        get_species_by_name("Natu"),
        MapRSE.SAFARI_ZONE_NORTH,
        (5, 33),
        SafariHuntingMode.SPIN,
    )
    GIRAFARIG = SafariCatchingLocation(
        get_species_by_name("Girafarig"),
        MapRSE.SAFARI_ZONE_SOUTH,
        (25, 30),
        SafariHuntingMode.SPIN,
    )
    WOBBUFFET = SafariCatchingLocation(
        get_species_by_name("Wobbuffet"),
        MapRSE.SAFARI_ZONE_SOUTH,
        (25, 30),
        SafariHuntingMode.SPIN,
    )
    XATU = SafariCatchingLocation(
        get_species_by_name("Xatu"),
        MapRSE.SAFARI_ZONE_NORTH,
        (5, 33),
        SafariHuntingMode.SPIN,
    )
    HERACROSS = SafariCatchingLocation(
        get_species_by_name("Heracross"),
        MapRSE.SAFARI_ZONE_NORTH,
        (5, 33),
        SafariHuntingMode.SPIN,
    )
    PHANPY = SafariCatchingLocation(
        get_species_by_name("Phanpy"),
        MapRSE.SAFARI_ZONE_NORTH,
        (5, 33),
        SafariHuntingMode.SPIN,
    )
    PSYDUCK = SafariCatchingLocation(
        get_species_by_name("Psyduck"),
        MapRSE.SAFARI_ZONE_SOUTHWEST,
        (18, 17),
        SafariHuntingMode.SURF,
    )
    GOLDUCK = SafariCatchingLocation(
        get_species_by_name("Golduck"),
        MapRSE.SAFARI_ZONE_NORTHWEST,
        (25, 13),
        SafariHuntingMode.SURF,
    )
    GOLDEEN = SafariCatchingLocation(
        get_species_by_name("Goldeen"),
        MapRSE.SAFARI_ZONE_SOUTHWEST,
        (20, 20),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
    )
    MAGIKARP = SafariCatchingLocation(
        get_species_by_name("Magikarp"),
        MapRSE.SAFARI_ZONE_SOUTHWEST,
        (20, 20),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.OLD_ROD,
    )
    SEAKING = SafariCatchingLocation(
        get_species_by_name("Seaking"),
        MapRSE.SAFARI_ZONE_SOUTHWEST,
        (20, 20),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
    )
    HOOTHOOT = SafariCatchingLocation(
        get_species_by_name("Hoothoot"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    SPINARAK = SafariCatchingLocation(
        get_species_by_name("Spinarak"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SURF,
        availability=emerald_and_elite_four_defeated,
    )
    MAREEP = SafariCatchingLocation(
        get_species_by_name("Mareep"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    AIPOM = SafariCatchingLocation(
        get_species_by_name("Aipom"),
        MapRSE.SAFARI_ZONE_NORTHEAST,
        (6, 22),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    SUNKERN = SafariCatchingLocation(
        get_species_by_name("Sunkern"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    GLIGAR = SafariCatchingLocation(
        get_species_by_name("Gligar"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    SNUBBULL = SafariCatchingLocation(
        get_species_by_name("Snubbull"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    STANTLER = SafariCatchingLocation(
        get_species_by_name("Stantler"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (18, 33),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    MARILL = SafariCatchingLocation(
        get_species_by_name("Marill"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (24, 21),
        SafariHuntingMode.SURF,
        availability=emerald_and_elite_four_defeated,
    )
    WOOPER = SafariCatchingLocation(
        get_species_by_name("Wooper"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (24, 21),
        SafariHuntingMode.SURF,
        availability=emerald_and_elite_four_defeated,
    )
    QUAGSIRE = SafariCatchingLocation(
        get_species_by_name("Quagsire"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (24, 21),
        SafariHuntingMode.SURF,
        availability=emerald_and_elite_four_defeated,
    )
    REMORAID = SafariCatchingLocation(
        get_species_by_name("Remoraid"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (20, 12),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
        availability=emerald_and_elite_four_defeated,
    )
    OCTILLERY = SafariCatchingLocation(
        get_species_by_name("Octillery"),
        MapRSE.SAFARI_ZONE_SOUTHEAST,
        (20, 12),
        SafariHuntingMode.FISHING,
        SafariHuntingObject.SUPER_ROD,
        availability=emerald_and_elite_four_defeated,
    )
    LEDYBA = SafariCatchingLocation(
        get_species_by_name("Ledyba"),
        MapRSE.SAFARI_ZONE_NORTHEAST,
        (6, 22),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    PINECO = SafariCatchingLocation(
        get_species_by_name("Pineco"),
        MapRSE.SAFARI_ZONE_NORTHEAST,
        (6, 22),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    TEDDIURSA = SafariCatchingLocation(
        get_species_by_name("Teddiursa"),
        MapRSE.SAFARI_ZONE_NORTHEAST,
        (6, 22),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )
    HOUNDOUR = SafariCatchingLocation(
        get_species_by_name("Houndour"),
        MapRSE.SAFARI_ZONE_NORTHEAST,
        (6, 22),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )

    MILTANK = SafariCatchingLocation(
        get_species_by_name("Miltank"),
        MapRSE.SAFARI_ZONE_NORTHEAST,
        (6, 22),
        SafariHuntingMode.SPIN,
        availability=emerald_and_elite_four_defeated,
    )

    #     SHUCKLE = SafariCatchingLocation(
    #         get_species_by_name("Shuckle"),
    #         MapRSE.SAFARI_ZONE_NORTHEAST,
    #         (12, 7),
    #         SafariHuntingMode.ROCK_SMASH,
    #         availability=emerald_and_elite_four_defeated,
    #     )
    ## Need to implement a rock smash route, but this is not the best location to catch it...
    #     GEODUDE = SafariCatchingLocation(
    #         get_species_by_name("Geodude"),
    #         MapRSE.SAFARI_ZONE_NORTHEAST,
    #         (12, 7),
    #         SafariHuntingMode.ROCK_SMASH,
    #         availability=emerald_and_elite_four_defeated,
    #     )

    @staticmethod
    def available_pokemon() -> list:
        return [pokemon for pokemon in SafariPokemonRSE if pokemon.value.availability()]


SAFARI_ZONE_CONFIG: Dict[str, Dict[str, object]] = {
    "FRLG": {
        "map": MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE,
        "entrance_tile": (4, 4),
        "facing_direction": "Up",
        "save_message": "In order to start the Safari mode you should save in the entrance building to the Safari Zone.",
        "ask_script": "FuchsiaCity_SafariZone_Entrance_EventScript_AskEnterSafariZone",
        "enter_script": "FuchsiaCity_SafariZone_Entrance_EventScript_TryEnterSafariZone",
        "exit_script": "FuchsiaCity_SafariZone_Entrance_EventScript_ExitWarpIn",
        "is_at_entrance_door": lambda: (
            get_player_avatar().map_group_and_number == MapFRLG.SAFARI_ZONE_CENTER
            and get_player_avatar().local_coordinates == (26, 30)
        ),
        "safari_pokemon_list": SafariPokemon,
    },
    "E": {
        "map": MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE,
        "entrance_tile": (8, 4),
        "facing_direction": "Left",
        "save_message": "In order to start the Safari mode you should save in the entrance building to the Safari Zone.",
        "ask_script": "Route121_SafariZoneEntrance_EventScript_EntranceCounterTrigger",
        "enter_script": "Route121_SafariZoneEntrance_EventScript_TryEnterSafariZone",
        "exit_script": "Route121_SafariZoneEntrance_EventScript_ExitSafariZone",
        "is_at_entrance_door": lambda: (
            get_player_avatar().map_group_and_number == MapRSE.SAFARI_ZONE_SOUTH
            and get_player_avatar().local_coordinates in ((32, 33), (32, 34))
        ),
        "is_script_active": lambda: get_global_script_context().is_active,
        "safari_pokemon_list": SafariPokemonRSE,
    },
    "RS": {
        "map": MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE,
        "entrance_tile": (8, 4),
        "facing_direction": "Left",
        "save_message": "In order to start the Safari mode you should save in the entrance building to the Safari Zone.",
        "ask_script": "Route121_SafariZoneEntrance_EventScript_15C383",
        "enter_script": "Route121_SafariZoneEntrance_EventScript_15C3B3",
        "exit_script": "Route121_SafariZoneEntrance_EventScript_15C333",
        "is_at_entrance_door": lambda: (
            get_player_avatar().map_group_and_number == MapRSE.SAFARI_ZONE_SOUTH
            and get_player_avatar().local_coordinates in ((32, 33), (32, 34))
        ),
        "is_script_active": lambda: get_global_script_context().is_active,
        "safari_pokemon_list": SafariPokemonRSE,
    },
}


def get_safari_zone_config(rom: ROM) -> Dict[str, object]:
    if rom.is_frlg:
        return SAFARI_ZONE_CONFIG["FRLG"]
    elif rom.is_emerald:
        return SAFARI_ZONE_CONFIG["E"]
    elif rom.is_rs:
        return SAFARI_ZONE_CONFIG["RS"]
    else:
        raise ValueError("Unsupported ROM for Safari Mode.")


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
    We just check it to know if the monster was watching carefully or eating the previous turn
    This information is displayed on the player screen
    """
    return context.emulator.read_bytes(0x0200008A, length=1)[0] == 0


def get_safari_balls_left() -> int:
    return read_symbol("gNumSafariBalls")[0]


def get_safari_pokemon(name: str) -> Optional[Union[SafariPokemon, SafariPokemonRSE]]:
    if context.rom.is_frlg:
        rom_type = "FRLG"
    elif context.rom.is_rs:
        rom_type = "RS"
    elif context.rom.is_emerald:
        rom_type = "E"
    else:
        raise ValueError("Unknown ROM type")

    safari_pokemon_list = SAFARI_ZONE_CONFIG[rom_type]["safari_pokemon_list"]

    name = make_string_safe_for_file_name(name).upper()

    for safari_pokemon in safari_pokemon_list:
        if safari_pokemon.name == name:
            return safari_pokemon

    return None


class RSESafariStrategy:
    NO_STRATEGY = {
        SafariPokemonRSE.MAREEP,
        SafariPokemonRSE.SUNKERN,
        SafariPokemonRSE.ODDISH,
        # SafariPokemonRSE.GEODUDE,
        SafariPokemonRSE.GOLDEEN,
        SafariPokemonRSE.MAGIKARP,
        SafariPokemonRSE.HOOTHOOT,
        SafariPokemonRSE.LEDYBA,
        SafariPokemonRSE.SPINARAK,
        SafariPokemonRSE.WOOPER,
        SafariPokemonRSE.PIKACHU,
        SafariPokemonRSE.PSYDUCK,
        SafariPokemonRSE.DODUO,
        SafariPokemonRSE.NATU,
        SafariPokemonRSE.MARILL,
        SafariPokemonRSE.PINECO,
        SafariPokemonRSE.SNUBBULL,
        # SafariPokemonRSE.SHUCKLE,
        SafariPokemonRSE.REMORAID,
    }
    POKEBLOCK = {
        SafariPokemonRSE.DODRIO,
        SafariPokemonRSE.PINSIR,
        SafariPokemonRSE.AIPOM,
        SafariPokemonRSE.WOBBUFFET,
        SafariPokemonRSE.HERACROSS,
        SafariPokemonRSE.STANTLER,
        SafariPokemonRSE.MILTANK,
        SafariPokemonRSE.GOLDUCK,
        SafariPokemonRSE.XATU,
        SafariPokemonRSE.OCTILLERY,
        SafariPokemonRSE.SEAKING,
        SafariPokemonRSE.GIRAFARIG,
        SafariPokemonRSE.GLIGAR,
        SafariPokemonRSE.QUAGSIRE,
        SafariPokemonRSE.GLOOM,
        SafariPokemonRSE.RHYHORN,
        SafariPokemonRSE.TEDDIURSA,
        SafariPokemonRSE.HOUNDOUR,
        SafariPokemonRSE.PHANPY,
    }

    @classmethod
    def should_start_pokeblock_strategy(cls, pokemon: Pokemon) -> bool:
        """
        Determines if we should start a Pokéblock strategy.
        """
        safari_pokemon = get_safari_pokemon(pokemon.species.name)
        return safari_pokemon in cls.POKEBLOCK

    @staticmethod
    def get_facing_direction_for_position(position: tuple[int, int]) -> str | None:
        SAFARI_FEEDER_DIRECTIONS = {
            (25, 30): "Left",  # PIKACHU, GIRAFARIG, WOBBUFFET
            (5, 7): "Left",  # ODDISH, GLOOM, DODUO, DODRIO, RHYHORN, PINSIR
            (5, 33): "Down",  # NATU, XATU, HERACROSS, PHANPY
            (18, 17): "Up",  # PSYDUCK
            (25, 13): None,  # GOLDUCK
            (20, 20): None,  # GOLDEEN, MAGIKARP, SEAKING
            (18, 33): "Right",  # HOOTHOOT, SPINARAK, MAREEP, SUNKERN, GLIGAR, SNUBBULL, STANTLER
            (6, 22): "Left",  # AIPOM, LEDYBA, PINECO, TEDDIURSA, HOUNDOUR, MILTANK
            (24, 21): "Right",  # MARILL, WOOPER, QUAGSIRE
            (20, 12): None,  # REMORAID, OCTILLERY
        }

        return SAFARI_FEEDER_DIRECTIONS.get(position, None)


def get_baiting_state(pokeblock: Pokeblock) -> int | None:
    """
    We do not intentionally check on the Pokémon to know what Pokéblock to throw to mimic a real user behavior
    We just check it to know if the monster was watching neutral/enthralled/disliked the given Pokéblock
    This information is displayed on the player screen
    """
    pokeblock_type = pokeblock.type.value
    opponent_nature = get_opponent().nature
    liked_flavor = opponent_nature.pokeblock_preferences.get("liked")
    disliked_flavor = opponent_nature.pokeblock_preferences.get("disliked")

    # Some natures doesn't have like / disliked flavors
    if liked_flavor is None and disliked_flavor is None:
        return PokeblockState.CURIOUS

    if pokeblock_type == disliked_flavor.lower():
        return PokeblockState.IGNORED

    if pokeblock_type == liked_flavor.lower():
        return PokeblockState.ENTHRALLED

    return PokeblockState.CURIOUS


def get_lowest_feel_any_pokeblock() -> tuple[int | None, Pokeblock | None]:
    """Return the index and the Pokéblock with the lowest feel when there are no flavor preferences."""
    pokeblocks = get_pokeblocks()
    lowest_feel = float("inf")
    best_index = None
    best_pokeblock = None

    for index, pokeblock in enumerate(pokeblocks):
        if pokeblock.feel < lowest_feel:
            lowest_feel = pokeblock.feel
            best_index = index
            best_pokeblock = pokeblock

    return best_index, best_pokeblock


def get_lowest_feel_pokeblock_by_type(
    flavor_str: str,
) -> Tuple[Optional[int], Optional[Pokeblock]]:
    """
    Return the index and Pokéblock with the lowest feel among those whose type matches the given flavor string.
    """
    try:
        flavor = PokeblockType[flavor_str.capitalize()]
    except KeyError:
        raise ValueError(f"Invalid Pokéblock type: '{flavor_str}'")

    pokeblocks = get_pokeblocks()
    lowest_feel = float("inf")
    best_index = None
    best_pokeblock = None

    for index, pokeblock in enumerate(pokeblocks):
        if pokeblock.type == flavor and pokeblock.feel < lowest_feel:
            lowest_feel = pokeblock.feel
            best_index = index
            best_pokeblock = pokeblock

    return best_index, best_pokeblock


def get_lowest_feel_excluding_type(excluded_type: PokeblockType) -> tuple[int | None, Pokeblock | None]:
    """Return the index and the Pokéblock with the lowest feel that is not of the excluded PokéblockType."""
    pokeblocks = get_pokeblocks()
    lowest_feel = float("inf")
    best_index = None
    best_pokeblock = None

    for index, pokeblock in enumerate(pokeblocks):
        if pokeblock.type != excluded_type and pokeblock.feel < lowest_feel:
            lowest_feel = pokeblock.feel
            best_index = index
            best_pokeblock = pokeblock

    return best_index, best_pokeblock


def get_pokeblock_type_counts() -> list[tuple[str, int]]:
    """
    Returns a list of tuples (type_name: str, count: int)
    for each Pokéblock type present in the inventory.
    """
    pokeblocks = get_pokeblocks()
    type_counter = Counter(pokeblock.type.name for pokeblock in pokeblocks)
    return list(type_counter.items())


def get_navigation_path(
    target_map: Union[MapFRLG, MapRSE], tile_location: tuple[int, int]
) -> list[tuple[Union[MapFRLG, MapRSE], tuple[int, int]]]:
    """
    Returns the navigation path for a given target map.

    Args:
        target_map (Union[MapFRLG, MapRSE]): The target map for which the navigation path is required. This can be from either the FireRed/LeafGreen or Ruby/Sapphire/Emerald versions.
        tile_location (tuple[int, int]): Local coordinates on the destination map.

    Returns:
        List[Tuple[Union[MapFRLG, MapRSE], Tuple[int, int], Optional[str]]]: A list of tuples, where each tuple represents a step
        in the navigation path. Each tuple contains:
        - A MapFRLG or MapRSE enum value for the destination map.
        - A tuple of (x, y) coordinates for the target location.

    Raises:
        BotModeError: If no navigation path is defined for the given target map.
    """

    def can_surf():
        return get_event_flag("BADGE05_GET") and get_party().has_pokemon_with_move("Surf")

    match target_map:
        case MapFRLG.SAFARI_ZONE_CENTER:
            return [(MapFRLG.SAFARI_ZONE_CENTER, tile_location)]

        case MapFRLG.SAFARI_ZONE_EAST:
            return [
                (MapFRLG.SAFARI_ZONE_CENTER, (43, 16)),
                (MapFRLG.SAFARI_ZONE_EAST, tile_location),
            ]

        case MapFRLG.SAFARI_ZONE_NORTH:
            if can_surf():
                return [
                    (MapFRLG.SAFARI_ZONE_CENTER, (26, 5)),
                    (MapFRLG.SAFARI_ZONE_NORTH, tile_location),
                ]
            else:
                return [
                    (MapFRLG.SAFARI_ZONE_CENTER, (43, 16)),
                    (MapFRLG.SAFARI_ZONE_EAST, (8, 9)),
                    (MapFRLG.SAFARI_ZONE_NORTH, tile_location),
                ]

        case MapFRLG.SAFARI_ZONE_WEST:
            if can_surf():
                return [
                    (MapFRLG.SAFARI_ZONE_CENTER, (8, 17)),
                    (MapFRLG.SAFARI_ZONE_WEST, tile_location),
                ]
            else:
                return [
                    (MapFRLG.SAFARI_ZONE_CENTER, (43, 16)),
                    (MapFRLG.SAFARI_ZONE_EAST, (8, 9)),
                    (MapFRLG.SAFARI_ZONE_NORTH, (21, 34)),
                    (MapFRLG.SAFARI_ZONE_WEST, tile_location),
                ]
        case MapRSE.SAFARI_ZONE_NORTHWEST:
            return [
                (MapRSE.SAFARI_ZONE_NORTHWEST, tile_location),
            ]
        case MapRSE.SAFARI_ZONE_NORTH:
            return [
                (MapRSE.SAFARI_ZONE_NORTH, tile_location),
            ]
        case MapRSE.SAFARI_ZONE_NORTHEAST:
            return [
                (MapRSE.SAFARI_ZONE_NORTHEAST, tile_location),
            ]
        case MapRSE.SAFARI_ZONE_SOUTHWEST:
            return [
                (MapRSE.SAFARI_ZONE_SOUTHWEST, tile_location),
            ]
        case MapRSE.SAFARI_ZONE_SOUTH:
            return [
                (MapRSE.SAFARI_ZONE_SOUTH, tile_location),
            ]
        case MapRSE.SAFARI_ZONE_SOUTHEAST:
            return [
                (MapRSE.SAFARI_ZONE_SOUTHEAST, tile_location),
            ]
        case _:
            raise BotModeError(f"Error: No navigation path defined for {target_map}.")
