import yaml
from typing import Union, Tuple
from modules.context import context
from modules.battle_strategies import SafariTurnAction
from modules.pokemon import Pokemon
from modules.runtime import get_data_path
from modules.memory import read_symbol


class FRLGSafariStrategy:
    # Class attributes for Pokémon strategy categories
    NO_STRATEGY = {
        "MAGIKARP",
        "NIDORAN♀",
        "NIDORAN♂",
        "PARAS",
        "VENONAT",
        "PSYDUCK",
        "POLIWAG",
        "SLOWPOKE",
        "DODUO",
        "GOLDEEN",
        "NIDORINO",
        "NIDORINA",
        "EXEGGCUTE",
        "RHYHORN",
    }
    LOOKUP_4_OR_6 = {"SEAKING"}
    LOOKUP_5_OR_6 = {"PARASECT", "VENOMOTH"}
    LOOKUP_3 = {"DRATINI"}
    LOOKUP_1_OR_2 = {"CHANSEY"}
    LOOKUP_2 = {"KANGASKHAN", "SCYTHER", "PINSIR", "TAUROS", "DRAGONAIR"}

    @classmethod
    def get_strategy_file(cls, pokemon: Pokemon, has_been_baited: bool) -> Union[str, None]:
        """
        Determines the strategy file based on the Pokémon name and baited status.
        """
        name = pokemon.species.name.upper()
        match name:
            case name if name in cls.NO_STRATEGY:
                return None
            case name if name in cls.LOOKUP_4_OR_6:
                file_name = "lookup-4.yml" if not has_been_baited else "lookup-6.yml"
            case name if name in cls.LOOKUP_5_OR_6:
                file_name = "lookup-5.yml" if not has_been_baited else "lookup-6.yml"
            case name if name in cls.LOOKUP_3:
                file_name = "lookup-3.yml"
            case name if name in cls.LOOKUP_1_OR_2:
                file_name = "lookup-1.yml" if not has_been_baited else "lookup-2.yml"
            case name if name in cls.LOOKUP_2:
                file_name = "lookup-2.yml"
            case _:
                raise RuntimeError(f"Pokemon `{name}` doesn't have a safari strategy.")

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
