import random
from enum import Enum, auto
from pathlib import Path

from modules.console import console
from modules.context import context
from modules.data.map import MapRSE, MapFRLG
from modules.encounter import encounter_pokemon
from modules.files import get_rng_state_history, save_rng_state_history
from modules.gui.multi_select_window import Selection, MultiSelector, MultiSelectWindow
from modules.memory import read_symbol, get_game_state, GameState, write_symbol, unpack_uint32, pack_uint32
from modules.navigation import follow_path
from modules.player import get_player_avatar
from modules.pokemon import get_party, opponent_changed
from modules.tasks import get_task, task_is_active
from modules.menuing import StartMenuNavigator, PokemonPartyMenuNavigator


class Regions(Enum):
    KANTO_STARTERS = auto()
    JOHTO_STARTERS = auto()
    HOENN_STARTERS = auto()


class BagPositions(Enum):
    TREECKO = 0
    TORCHIC = 1
    MUDKIP = 2


class ModeStarterStates(Enum):
    RESET = auto()
    TITLE = auto()
    OVERWORLD = auto()
    BAG_MENU = auto()
    INJECT_RNG = auto()
    SELECT_STARTER = auto()
    CONFIRM_STARTER = auto()
    RNG = auto()
    STARTER_BATTLE = auto()
    THROW_BALL = auto()
    STARTER_CRY_START = auto()
    STARTER_CRY_END = auto()
    YES_NO = auto()
    EXIT_MENUS = auto()
    FOLLOW_PATH = auto()
    OPEN_START_MENU_POKEMON = auto()
    PARTY_FULL = auto()
    LOG_STARTER = auto()
    OPEN_POKEMON_SUMMARY_MENU = auto()


class ModeStarters:
    def __init__(self) -> None:
        if not context.selected_pokemon:
            context.random_starter = False
            sprites = Path(__file__).parent.parent.parent / "sprites" / "pokemon" / "normal"
            conditions = {
                "Bulbasaur": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and get_player_avatar().map_group_and_number == MapFRLG.PALLET_TOWN_D.value
                        and get_player_avatar().local_coordinates == (8, 5)
                        and get_player_avatar().facing_direction == "Up"
                    )
                ),
                "Charmander": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and get_player_avatar().map_group_and_number == MapFRLG.PALLET_TOWN_D.value
                        and get_player_avatar().local_coordinates == (10, 5)
                        and get_player_avatar().facing_direction == "Up"
                    )
                ),
                "Squirtle": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and get_player_avatar().map_group_and_number == MapFRLG.PALLET_TOWN_D.value
                        and get_player_avatar().local_coordinates == (9, 5)
                        and get_player_avatar().facing_direction == "Up"
                    )
                ),
                "Random Kanto": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and get_player_avatar().map_group_and_number == MapFRLG.PALLET_TOWN_D.value
                        and (
                            get_player_avatar().local_coordinates[0] in [8, 9, 10]
                            and get_player_avatar().local_coordinates[1] == 5
                        )
                    )
                ),
                "Chikorita": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and get_player_avatar().map_group_and_number == MapRSE.LITTLEROOT_TOWN_E.value
                        and get_player_avatar().local_coordinates == (10, 5)
                        and get_player_avatar().facing_direction == "Up"
                    )
                ),
                "Cyndaquil": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and get_player_avatar().map_group_and_number == MapRSE.LITTLEROOT_TOWN_E.value
                        and get_player_avatar().local_coordinates == (8, 5)
                        and get_player_avatar().facing_direction == "Up"
                    )
                ),
                "Totodile": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and get_player_avatar().map_group_and_number == MapRSE.LITTLEROOT_TOWN_E.value
                        and get_player_avatar().local_coordinates == (9, 5)
                        and get_player_avatar().facing_direction == "Up"
                    )
                ),
                "Random Johto": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and get_player_avatar().map_group_and_number == MapRSE.LITTLEROOT_TOWN_E.value
                        and (
                            get_player_avatar().local_coordinates[0] in [8, 9, 10]
                            and get_player_avatar().local_coordinates[1] == 5
                        )
                    )
                ),
                "Treecko": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and get_player_avatar().map_group_and_number == MapRSE.ROUTE_101.value
                        and (
                            (
                                get_player_avatar().local_coordinates == (7, 15)
                                and get_player_avatar().facing_direction == "Up"
                            )
                            or (
                                get_player_avatar().local_coordinates == (8, 14)
                                and get_player_avatar().facing_direction == "Left"
                            )
                        )
                    )
                ),
                "Torchic": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and get_player_avatar().map_group_and_number == MapRSE.ROUTE_101.value
                        and (
                            (
                                get_player_avatar().local_coordinates == (7, 15)
                                and get_player_avatar().facing_direction == "Up"
                            )
                            or (
                                get_player_avatar().local_coordinates == (8, 14)
                                and get_player_avatar().facing_direction == "Left"
                            )
                        )
                    )
                ),
                "Mudkip": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and get_player_avatar().map_group_and_number == MapRSE.ROUTE_101.value
                        and (
                            (
                                get_player_avatar().local_coordinates == (7, 15)
                                and get_player_avatar().facing_direction == "Up"
                            )
                            or (
                                get_player_avatar().local_coordinates == (8, 14)
                                and get_player_avatar().facing_direction == "Left"
                            )
                        )
                    )
                ),
                "Random Hoenn": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and get_player_avatar().map_group_and_number == MapRSE.ROUTE_101.value
                        and (
                            (
                                get_player_avatar().local_coordinates == (7, 15)
                                and get_player_avatar().facing_direction == "Up"
                            )
                            or (
                                get_player_avatar().local_coordinates == (8, 14)
                                and get_player_avatar().facing_direction == "Left"
                            )
                        )
                    )
                ),
            }

            if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
                selections = [
                    Selection(
                        button_label="Bulbasaur",
                        button_enable=conditions["Bulbasaur"],
                        button_tooltip="Select Bulbasaur"
                        if conditions["Bulbasaur"]
                        else "Invalid location:\nPlace the player facing Bulbasaur's PokéBall in Oak's lab",
                        sprite=sprites / "Bulbasaur.png",
                    ),
                    Selection(
                        button_label="Squirtle",
                        button_enable=conditions["Squirtle"],
                        button_tooltip="Select Squirtle"
                        if conditions["Squirtle"]
                        else "Invalid location:\nPlace the player facing Squirtle's PokéBall in Oak's lab",
                        sprite=sprites / "Squirtle.png",
                    ),
                    Selection(
                        button_label="Charmander",
                        button_enable=conditions["Charmander"],
                        button_tooltip="Select Charmander"
                        if conditions["Charmander"]
                        else "Invalid location:\nPlace the player facing Charmander's PokéBall in Oak's lab",
                        sprite=sprites / "Charmander.png",
                    ),
                    Selection(
                        button_label="Random Kanto",
                        button_enable=conditions["Random Kanto"],
                        button_tooltip="Select Random"
                        if conditions["Random Kanto"]
                        else "Invalid location:\nPlace the player facing any PokéBall in Oak's lab",
                        sprite=sprites / "Unown.png",
                    ),
                ]
            elif (
                context.rom.game_title == "POKEMON EMER"
                and get_player_avatar().map_group_and_number == MapRSE.LITTLEROOT_TOWN_E.value
            ):
                selections = [
                    Selection(
                        button_label="Cyndaquil",
                        button_enable=conditions["Cyndaquil"],
                        button_tooltip="Select Cyndaquil"
                        if conditions["Cyndaquil"]
                        else "Invalid location:\nPlace the player facing Cyndaquil's PokéBall in Birch's lab",
                        sprite=sprites / "Cyndaquil.png",
                    ),
                    Selection(
                        button_label="Totodile",
                        button_enable=conditions["Totodile"],
                        button_tooltip="Select Totodile"
                        if conditions["Totodile"]
                        else "Invalid location:\nPlace the player facing Totodile's PokéBall in Birch's lab",
                        sprite=sprites / "Totodile.png",
                    ),
                    Selection(
                        button_label="Chikorita",
                        button_enable=conditions["Chikorita"],
                        button_tooltip="Select Chikorita"
                        if conditions["Chikorita"]
                        else "Invalid location:\nPlace the player facing Chikorita's PokéBall in Birch's lab",
                        sprite=sprites / "Chikorita.png",
                    ),
                    Selection(
                        button_label="Random Johto",
                        button_enable=conditions["Random Johto"],
                        button_tooltip="Select Random"
                        if conditions["Random Johto"]
                        else "Invalid location:\nPlace the player facing any PokéBall in Birch's lab",
                        sprite=sprites / "Unown.png",
                    ),
                ]
            else:
                selections = [
                    Selection(
                        button_label="Treecko",
                        button_enable=conditions["Treecko"],
                        button_tooltip="Select Treecko"
                        if conditions["Treecko"]
                        else "Invalid location:\nPlace the player facing Birch's bag on Route 101",
                        sprite=sprites / "Treecko.png",
                    ),
                    Selection(
                        button_label="Torchic",
                        button_enable=conditions["Torchic"],
                        button_tooltip="Select Torchic"
                        if conditions["Torchic"]
                        else "Invalid location:\nPlace the player facing Birch's bag on Route 101",
                        sprite=sprites / "Torchic.png",
                    ),
                    Selection(
                        button_label="Mudkip",
                        button_enable=conditions["Mudkip"],
                        button_tooltip="Select Mudkip"
                        if conditions["Mudkip"]
                        else "Invalid location:\nPlace the player facing Birch's bag on Route 101",
                        sprite=sprites / "Mudkip.png",
                    ),
                    Selection(
                        button_label="Random Hoenn",
                        button_enable=conditions["Random Hoenn"],
                        button_tooltip="Select Random"
                        if conditions["Random Hoenn"]
                        else "Invalid location:\nPlace the player facing Birch's bag on Route 101",
                        sprite=sprites / "Unown.png",
                    ),
                ]

            options = MultiSelector("Select a starter...", selections)
            MultiSelectWindow(context.gui.window, options)

            if not context.selected_pokemon:
                return
            elif "Random" in context.selected_pokemon:
                context.random_starter = True

        if context.selected_pokemon in ["Bulbasaur", "Charmander", "Squirtle", "Random Kanto"]:
            if context.random_starter:
                context.selected_pokemon = random.choice(["Bulbasaur", "Charmander", "Squirtle"])
            self.region: Regions = Regions.KANTO_STARTERS

        elif context.selected_pokemon in ["Chikorita", "Cyndaquil", "Totodile", "Random Johto"]:
            if context.random_starter:
                context.selected_pokemon = random.choice(["Chikorita", "Cyndaquil", "Totodile"])
            self.region: Regions = Regions.JOHTO_STARTERS
            self.start_party_length: int = 0
            if len(get_party()) == 6:
                self.update_state(ModeStarterStates.PARTY_FULL)

        elif context.selected_pokemon in ["Treecko", "Torchic", "Mudkip", "Random Hoenn"]:
            if context.random_starter:
                context.selected_pokemon = random.choice(["Treecko", "Torchic", "Mudkip"])
            self.bag_position: int = BagPositions[context.selected_pokemon.upper()].value
            if context.rom.game_title == "POKEMON EMER":
                self.region = Regions.HOENN_STARTERS
                self.task_bag_cursor: str = "Task_HandleStarterChooseInput"
                self.task_confirm: str = "Task_HandleConfirmStarterInput"
                self.task_ball_throw: str = "Task_PlayCryWhenReleasedFromBall"
                self.task_map_popup: str = "Task_MapNamePopupWindow"
            elif context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP"]:
                self.region = Regions.HOENN_STARTERS
                self.task_bag_cursor: str = "Task_StarterChoose2"
                self.task_confirm: str = "Task_StarterChoose5"
                self.task_ball_throw: str = "PokeBallOpenParticleAnimation"
                self.task_map_popup: str = "Task_MapNamePopup"
        else:
            return

        if not context.config.cheats.random_soft_reset_rng:
            self.rng_history: list = get_rng_state_history()

        self.state: ModeStarterStates = ModeStarterStates.RESET
        self.navigator = None

    def update_state(self, state: ModeStarterStates) -> None:
        self.state: ModeStarterStates = state

    def step(self):
        while True:
            match self.region, self.state:
                # Common states
                case Regions.KANTO_STARTERS | Regions.JOHTO_STARTERS | Regions.HOENN_STARTERS, ModeStarterStates.RESET:
                    context.emulator.reset()
                    self.update_state(ModeStarterStates.TITLE)

                case Regions.KANTO_STARTERS | Regions.JOHTO_STARTERS | Regions.HOENN_STARTERS, ModeStarterStates.RNG:
                    if context.config.cheats.random_soft_reset_rng:
                        write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                        self.update_state(ModeStarterStates.CONFIRM_STARTER)
                    else:
                        rng = unpack_uint32(read_symbol("gRngValue"))
                        if rng in self.rng_history or (
                            task_is_active("Task_ExitNonDoor")
                            or task_is_active("task_map_chg_seq_0807E20C")
                            or task_is_active("task_map_chg_seq_0807E2CC")
                        ):
                            pass
                        else:
                            self.rng_history.append(rng)
                            save_rng_state_history(self.rng_history)
                            self.update_state(ModeStarterStates.CONFIRM_STARTER)
                            continue

                case Regions.KANTO_STARTERS | Regions.HOENN_STARTERS, ModeStarterStates.LOG_STARTER:
                    encounter_pokemon(get_party()[0])
                    opponent_changed()  # Prevent opponent from being logged if starter is shiny
                    return

                case Regions.KANTO_STARTERS | Regions.JOHTO_STARTERS, ModeStarterStates.OPEN_START_MENU_POKEMON:
                    if context.config.cheats.fast_check_starters:
                        self.update_state(ModeStarterStates.LOG_STARTER)
                        continue
                    elif self.navigator is None:
                        self.navigator = StartMenuNavigator("POKEMON")
                    else:
                        yield from self.navigator.step()
                        match self.navigator.current_step:
                            case "exit":
                                self.navigator = None
                                self.update_state(ModeStarterStates.OPEN_POKEMON_SUMMARY_MENU)
                                continue

                # Kanto Starters
                case Regions.KANTO_STARTERS | Regions.JOHTO_STARTERS | Regions.HOENN_STARTERS, ModeStarterStates.TITLE:
                    match get_game_state():
                        case GameState.TITLE_SCREEN:
                            context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))
                        case GameState.MAIN_MENU:
                            context.emulator.press_button("A")
                        case GameState.QUEST_LOG:
                            context.emulator.press_button("B")
                        case GameState.OVERWORLD:
                            self.update_state(ModeStarterStates.OVERWORLD)

                case Regions.KANTO_STARTERS, ModeStarterStates.OVERWORLD:
                    if (
                        get_player_avatar().local_coordinates[0]
                        != ["Bulbasaur", "Squirtle", "Charmander"].index(context.selected_pokemon) + 8
                    ):
                        follow_path([(["Bulbasaur", "Squirtle", "Charmander"].index(context.selected_pokemon) + 8, 5)])
                    elif not get_player_avatar().facing_direction == "Up":
                        context.emulator.press_button("Up")
                    else:
                        context.message = "Waiting for a unique frame before continuing..."
                        self.update_state(ModeStarterStates.RNG)
                        continue

                case Regions.KANTO_STARTERS, ModeStarterStates.CONFIRM_STARTER:
                    if not task_is_active("Task_ScriptShowMonPic"):
                        context.emulator.press_button("A")
                    elif task_is_active("Task_DrawFieldMessageBox"):
                        context.emulator.press_button("A")
                    elif not task_is_active("Task_ScriptShowMonPic"):
                        context.emulator.press_button("B")
                    else:
                        self.update_state(ModeStarterStates.EXIT_MENUS)

                case Regions.KANTO_STARTERS, ModeStarterStates.EXIT_MENUS:
                    if len(get_party()) == 0:
                        context.emulator.press_button("A")
                    if context.config.cheats.fast_check_starters:
                        self.update_state(ModeStarterStates.LOG_STARTER)
                        continue
                    else:
                        if task_is_active("ScriptMovement_MoveObjects"):
                            context.emulator.press_button("B")
                        else:
                            self.update_state(ModeStarterStates.OPEN_START_MENU_POKEMON)

                case Regions.KANTO_STARTERS, ModeStarterStates.OPEN_POKEMON_SUMMARY_MENU:  # TODO should be PokemonPartyMenuNavigator
                    context.emulator.press_button("A")
                    if task_is_active("TASK_DUCKBGMFORPOKEMONCRY"):
                        self.update_state(ModeStarterStates.LOG_STARTER)
                        continue

                # Johto Starters
                case Regions.JOHTO_STARTERS, ModeStarterStates.PARTY_FULL:
                    console.print("[red]Your party is full, make some room before using the Johto starters mode!")
                    context.set_manual_mode()
                    return

                case Regions.JOHTO_STARTERS, ModeStarterStates.OVERWORLD:
                    if (
                        get_player_avatar().local_coordinates[0]
                        != ["Cyndaquil", "Totodile", "Chikorita"].index(context.selected_pokemon) + 8
                    ):
                        follow_path([(["Cyndaquil", "Totodile", "Chikorita"].index(context.selected_pokemon) + 8, 5)])
                    elif not get_player_avatar().facing_direction == "Up":
                        context.emulator.press_button("Up")
                    else:
                        self.start_party_length = len(get_party())
                        if task_is_active("Task_DrawFieldMessage"):
                            context.emulator.press_button("A")
                        else:
                            context.message = "Waiting for a unique frame before continuing..."
                            self.update_state(ModeStarterStates.RNG)
                            continue

                case Regions.JOHTO_STARTERS, ModeStarterStates.CONFIRM_STARTER:
                    if len(get_party()) == self.start_party_length:
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeStarterStates.EXIT_MENUS)
                        continue

                case Regions.JOHTO_STARTERS, ModeStarterStates.EXIT_MENUS:
                    if context.config.cheats.fast_check_starters:
                        self.update_state(ModeStarterStates.LOG_STARTER)
                        continue
                    else:
                        if task_is_active("ScriptMovement_MoveObjects"):
                            context.emulator.press_button("B")
                        else:
                            self.update_state(ModeStarterStates.OPEN_START_MENU_POKEMON)
                            continue

                case Regions.JOHTO_STARTERS, ModeStarterStates.LOG_STARTER:
                    party = get_party()
                    encounter_pokemon(party[len(party) - 1])
                    opponent_changed()  # Prevent opponent from being logged if starter is shiny
                    return

                case Regions.JOHTO_STARTERS, ModeStarterStates.OPEN_POKEMON_SUMMARY_MENU:
                    if self.navigator is None:
                        self.navigator = PokemonPartyMenuNavigator(len(get_party()) - 1, "summary")
                    else:
                        yield from self.navigator.step()
                        match self.navigator.current_step:
                            case "exit":
                                self.navigator = None
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue
                    continue

                # Hoenn Starters
                case Regions.HOENN_STARTERS, ModeStarterStates.OVERWORLD:
                    if get_game_state() != GameState.CHOOSE_STARTER:
                        context.emulator.press_button("A")
                        yield
                    else:
                        self.update_state(ModeStarterStates.BAG_MENU)
                    continue

                case Regions.HOENN_STARTERS, ModeStarterStates.BAG_MENU:
                    cursor_task = get_task(self.task_bag_cursor)
                    if cursor_task:
                        cursor_pos = cursor_task.data[0]
                        if cursor_pos > self.bag_position:
                            context.emulator.press_button("Left")
                        elif cursor_pos < self.bag_position:
                            context.emulator.press_button("Right")
                        elif cursor_pos == self.bag_position:
                            self.update_state(ModeStarterStates.SELECT_STARTER)
                            continue

                case Regions.HOENN_STARTERS, ModeStarterStates.SELECT_STARTER:
                    if not task_is_active(self.task_confirm):
                        context.emulator.press_button("A")
                    else:
                        context.message = "Waiting for a unique frame before continuing..."
                        self.update_state(ModeStarterStates.RNG)
                        continue

                case Regions.HOENN_STARTERS, ModeStarterStates.CONFIRM_STARTER:
                    if context.config.cheats.fast_check_starters:
                        if len(get_party()) > 0:
                            self.update_state(ModeStarterStates.LOG_STARTER)
                        context.emulator.press_button("A")
                    else:
                        if task_is_active(self.task_confirm) and get_game_state() != GameState.BATTLE:
                            context.emulator.press_button("A")
                        else:
                            self.update_state(ModeStarterStates.THROW_BALL)
                            continue

                # Check for ball being thrown
                case Regions.HOENN_STARTERS, ModeStarterStates.THROW_BALL:
                    if not task_is_active(self.task_ball_throw):
                        context.emulator.press_button("B")
                    else:
                        self.update_state(ModeStarterStates.STARTER_CRY_START)
                        continue

                case Regions.HOENN_STARTERS, ModeStarterStates.STARTER_CRY_START:
                    if task_is_active("Task_DuckBGMForPokemonCry"):
                        self.update_state(ModeStarterStates.STARTER_CRY_END)
                        continue

                case Regions.HOENN_STARTERS, ModeStarterStates.STARTER_CRY_END:  # Ensures starter sprite is visible before resetting
                    if not task_is_active("Task_DuckBGMForPokemonCry"):
                        self.update_state(ModeStarterStates.LOG_STARTER)
                        continue

            yield


def generate_guaranteed_shiny_rng_seed(trainer_id: int, secret_id: int) -> bytes:
    while True:
        seed = random.randint(0, 0xFFFF_FFFF)

        rng_value = seed
        rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
        rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
        personality_value_upper = rng_value >> 16
        rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
        personality_value_lower = rng_value >> 16

        if trainer_id ^ secret_id ^ personality_value_upper ^ personality_value_lower < 8:
            return pack_uint32(seed)
