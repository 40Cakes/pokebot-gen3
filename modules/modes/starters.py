import random
from enum import Enum, auto
from pathlib import Path

from modules.console import console
from modules.context import context
from modules.data.map import MapRSE, MapFRLG
from modules.encounter import encounter_pokemon
from modules.files import get_rng_state_history, save_rng_state_history
from modules.gui.multi_select_window import Selection, MultiSelector, MultiSelectWindow
from modules.memory import read_symbol, get_game_state, GameState, get_task, write_symbol, unpack_uint32, pack_uint32
from modules.navigation import follow_path
from modules.pokemon import get_party, opponent_changed
from modules.trainer import trainer
from modules.game import decode_string
from modules.map import get_map_objects

config = context.config


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
    RNG_CHECK = auto()
    STARTER_BATTLE = auto()
    THROW_BALL = auto()
    OPPONENT_CRY_START = auto()
    OPPONENT_CRY_END = auto()
    STARTER_CRY = auto()
    STARTER_CRY_END = auto()
    YES_NO = auto()
    EXIT_MENUS = auto()
    FOLLOW_PATH = auto()
    CHECK_STARTER = auto()
    PARTY_FULL = auto()
    LOG_STARTER = auto()

class ModeStarters:
    def __init__(self) -> None:
        if not context.selected_pokemon:
            sprites = Path(__file__).parent.parent.parent / "sprites" / "pokemon" / "normal"

            conditions = {
                "Bulbasaur": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and trainer.get_map() == MapFRLG.PALLET_TOWN_D.value
                        and trainer.get_coords() == (8, 5)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
                "Charmander": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and trainer.get_map() == MapFRLG.PALLET_TOWN_D.value
                        and trainer.get_coords() == (10, 5)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
                "Squirtle": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and trainer.get_map() == MapFRLG.PALLET_TOWN_D.value
                        and trainer.get_coords() == (9, 5)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
                "Random_Kanto": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and trainer.get_map() == MapFRLG.PALLET_TOWN_D.value
                        and (trainer.get_coords()[0] in [8, 9, 10] and trainer.get_coords()[1] == 5)
                    )
                ),
                "Chikorita": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and trainer.get_map() == MapRSE.LITTLEROOT_TOWN_E.value
                        and trainer.get_coords() == (10, 5)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
                "Cyndaquil": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and trainer.get_map() == MapRSE.LITTLEROOT_TOWN_E.value
                        and trainer.get_coords() == (8, 5)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
                "Totodile": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and trainer.get_map() == MapRSE.LITTLEROOT_TOWN_E.value
                        and trainer.get_coords() == (9, 5)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
                "Random_Johto": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and trainer.get_map() == MapRSE.LITTLEROOT_TOWN_E.value
                        and (trainer.get_coords()[0] in [8, 9, 10] and trainer.get_coords()[1] == 5)
                    )
                ),
                "Treecko": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and trainer.get_map() == MapRSE.ROUTE_101.value
                        and (
                            (trainer.get_coords() == (7, 15) and trainer.get_facing_direction() == "Up")
                            or (trainer.get_coords() == (8, 14) and trainer.get_facing_direction() == "Left")
                        )
                    )
                ),
                "Torchic": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and trainer.get_map() == MapRSE.ROUTE_101.value
                        and (
                            (trainer.get_coords() == (7, 15) and trainer.get_facing_direction() == "Up")
                            or (trainer.get_coords() == (8, 14) and trainer.get_facing_direction() == "Left")
                        )
                    )
                ),
                "Mudkip": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and trainer.get_map() == MapRSE.ROUTE_101.value
                        and (
                            (trainer.get_coords() == (7, 15) and trainer.get_facing_direction() == "Up")
                            or (trainer.get_coords() == (8, 14) and trainer.get_facing_direction() == "Left")
                        )
                    )
                ),
                "Random_Hoenn": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and trainer.get_map() == MapRSE.ROUTE_101.value
                        and (
                            (trainer.get_coords() == (7, 15) and trainer.get_facing_direction() == "Up")
                            or (trainer.get_coords() == (8, 14) and trainer.get_facing_direction() == "Left")
                        )
                    )
                )
            }

            if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
                selections = [
                    Selection(
                        button_label="Bulbasaur",
                        button_enable=conditions["Bulbasaur"],
                        button_tooltip="Select Bulbasaur"
                        if conditions["Bulbasaur"]
                        else "Invalid location:\nPlace the trainer facing Bulbasaur's PokéBall in Oak's lab",
                        sprite=sprites / "Bulbasaur.png",
                    ),
                    Selection(
                        button_label="Squirtle",
                        button_enable=conditions["Squirtle"],
                        button_tooltip="Select Squirtle"
                        if conditions["Squirtle"]
                        else "Invalid location:\nPlace the trainer facing Squirtle's PokéBall in Oak's lab",
                        sprite=sprites / "Squirtle.png",
                    ),
                    Selection(
                        button_label="Charmander",
                        button_enable=conditions["Charmander"],
                        button_tooltip="Select Charmander"
                        if conditions["Charmander"]
                        else "Invalid location:\nPlace the trainer facing Charmander's PokéBall in Oak's lab",
                        sprite=sprites / "Charmander.png",
                    ),
                    Selection(
                        button_label="Random_Kanto",
                        button_enable=conditions["Random_Kanto"],
                        button_tooltip="Select Random"
                        if conditions["Random_Kanto"]
                        else "Invalid location:\nPlace the trainer facing any PokéBall in Oak's lab",
                        sprite=sprites / "Unown.png",
                    )
                ]
            elif context.rom.game_title == "POKEMON EMER" and trainer.get_map() == MapRSE.LITTLEROOT_TOWN_E.value:
                selections = [
                    Selection(
                        button_label="Cyndaquil",
                        button_enable=conditions["Cyndaquil"],
                        button_tooltip="Select Cyndaquil"
                        if conditions["Cyndaquil"]
                        else "Invalid location:\nPlace the trainer facing Cyndaquil's PokéBall in Birch's lab",
                        sprite=sprites / "Cyndaquil.png",
                    ),
                    Selection(
                        button_label="Totodile",
                        button_enable=conditions["Totodile"],
                        button_tooltip="Select Totodile"
                        if conditions["Totodile"]
                        else "Invalid location:\nPlace the trainer facing Totodile's PokéBall in Birch's lab",
                        sprite=sprites / "Totodile.png",
                    ),
                    Selection(
                        button_label="Chikorita",
                        button_enable=conditions["Chikorita"],
                        button_tooltip="Select Chikorita"
                        if conditions["Chikorita"]
                        else "Invalid location:\nPlace the trainer facing Chikorita's PokéBall in Birch's lab",
                        sprite=sprites / "Chikorita.png",
                    ),
                    Selection(
                        button_label="Random_Johto",
                        button_enable=conditions["Random_Johto"],
                        button_tooltip="Select Random"
                        if conditions["Random_Johto"]
                        else "Invalid location:\nPlace the trainer facing any PokéBall in Birch's lab",
                        sprite=sprites / "Unown.png",
                    )
                ]
            else:
                selections = [
                    Selection(
                        button_label="Treecko",
                        button_enable=conditions["Treecko"],
                        button_tooltip="Select Treecko"
                        if conditions["Treecko"]
                        else "Invalid location:\nPlace the trainer facing Birch's bag on Route 101",
                        sprite=sprites / "Treecko.png",
                    ),
                    Selection(
                        button_label="Torchic",
                        button_enable=conditions["Torchic"],
                        button_tooltip="Select Torchic"
                        if conditions["Torchic"]
                        else "Invalid location:\nPlace the trainer facing Birch's bag on Route 101",
                        sprite=sprites / "Torchic.png",
                    ),
                    Selection(
                        button_label="Mudkip",
                        button_enable=conditions["Mudkip"],
                        button_tooltip="Select Mudkip"
                        if conditions["Mudkip"]
                        else "Invalid location:\nPlace the trainer facing Birch's bag on Route 101",
                        sprite=sprites / "Mudkip.png",
                    ),
                    Selection(
                        button_label="Random_Hoenn",
                        button_enable=conditions["Random_Hoenn"],
                        button_tooltip="Select Random"
                        if conditions["Random_Hoenn"]
                        else "Invalid location:\nPlace the trainer facing Birch's bag on Route 101",
                        sprite=sprites / "Unown.png",
                    )
                ]

            options = MultiSelector("Select a starter...", selections)
            MultiSelectWindow(context.gui.window, options)
            if context.selected_pokemon in ["Random_Kanto","Random_Johto","Random_Hoenn"]:
                context.random_starter = True
            else:
                context.random_starter = False

        if context.selected_pokemon in ["Bulbasaur", "Charmander", "Squirtle", "Random_Kanto"]:
            if context.random_starter:
                context.selected_pokemon = random.choice(["Bulbasaur", "Charmander", "Squirtle"])
            self.region: Regions = Regions.KANTO_STARTERS

        elif context.selected_pokemon in ["Chikorita", "Cyndaquil", "Totodile", "Random_Johto"]:
            if context.random_starter:
                context.selected_pokemon = random.choice(["Chikorita", "Cyndaquil", "Totodile"])
            self.region: Regions = Regions.JOHTO_STARTERS
            self.start_party_length: int = 0
            if len(get_party()) == 6:
                self.update_state(ModeStarterStates.PARTY_FULL)

        elif context.selected_pokemon in ["Treecko", "Torchic", "Mudkip","Random_Hoenn"]:
            if context.random_starter:
                context.selected_pokemon = random.choice(["Treecko", "Torchic", "Mudkip"])
            self.bag_position: int = BagPositions[context.selected_pokemon.upper()].value
            if context.rom.game_title == "POKEMON EMER":
                self.region = Regions.HOENN_STARTERS
                self.task_bag_cursor: str = "TASK_HANDLESTARTERCHOOSEINPUT"
                self.task_confirm: str = "TASK_HANDLECONFIRMSTARTERINPUT"
                self.task_ball_throw: str = "TASK_PLAYCRYWHENRELEASEDFROMBALL"
                self.task_map_popup: str = "TASK_MAPNAMEPOPUPWINDOW"
            elif context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP"]:
                self.region = Regions.HOENN_STARTERS
                self.task_bag_cursor: str = "TASK_STARTERCHOOSE2"
                self.task_confirm: str = "TASK_STARTERCHOOSE5"
                self.task_ball_throw: str = "SUB_814146C"
                self.task_map_popup: str = "TASK_MAPNAMEPOPUP"

        if not config.cheats.starters_rng:
            self.rng_history: list = get_rng_state_history(context.selected_pokemon)

        self.state: ModeStarterStates = ModeStarterStates.RESET

    def update_state(self, state: ModeStarterStates):
        self.state: ModeStarterStates = state

    def step(self):
        while True:
            match self.region:
                case Regions.KANTO_STARTERS:
                    match self.state:
                        case ModeStarterStates.RESET:
                            context.emulator.reset()
                            self.update_state(ModeStarterStates.TITLE)

                        case ModeStarterStates.TITLE:
                            match get_game_state():
                                case GameState.TITLE_SCREEN:
                                    context.emulator.press_button(random.choice(["A","Start","Left","Right", "Up"]))
                                case GameState.MAIN_MENU:  # TODO assumes trainer is in Oak's lab, facing a ball
                                    if get_task("TASK_HANDLEMENUINPUT").get("isActive", False):
                                        self.update_state(ModeStarterStates.OVERWORLD)
                                        continue
                        
                        case ModeStarterStates.OVERWORLD:
                            context.message = "Pathing to starter..."
                            if get_task("TASK_HANDLEMENUINPUT").get("isActive", False):
                                context.emulator.press_button("A")
                            elif get_task("TASK_RUNTIMEBASEDEVENTS").get("data", False) != bytearray(b'\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'):
                                context.emulator.press_button("B")
                            elif trainer.get_coords()[0] != ["Bulbasaur", "Squirtle", "Charmander"].index(context.selected_pokemon)+8:
                                follow_path(
                                    [(["Bulbasaur", "Squirtle", "Charmander"].index(context.selected_pokemon)+8 , 5)]
                                )
                            elif not trainer.get_facing_direction() == "Up":
                                context.emulator.press_button("Up")
                            else:
                                context.message = "Waiting for a unique frame before continuing..."
                                self.update_state(ModeStarterStates.RNG_CHECK)
                                continue

                        case ModeStarterStates.RNG_CHECK:
                            if config.cheats.starters_rng:
                                self.update_state(ModeStarterStates.SELECT_STARTER)
                            else:
                                rng = unpack_uint32(read_symbol("gRngValue"))
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    if context.random_starter:
                                        save_rng_state_history("Random_Kanto", self.rng_history)
                                    else:
                                        save_rng_state_history(context.selected_pokemon, self.rng_history)
                                    self.update_state(ModeStarterStates.SELECT_STARTER)
                                    continue

                        case ModeStarterStates.SELECT_STARTER:  # TODO can be made slightly faster by holding B through chat
                            self.start_party_length = len(get_party())
                            if not get_task("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                context.emulator.press_button("A")
                            elif get_task("TASK_DRAWFIELDMESSAGEBOX").get("isActive", False):
                                context.emulator.press_button("A")
                            elif not get_task("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                context.emulator.press_button("B")
                            else:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if len(get_party()) == 0:
                                if config.cheats.starters_rng:
                                    write_symbol("gRngValue", generate_guaranteed_shiny_rng_seed(trainer.get_tid(), trainer.get_sid()))
                                context.emulator.press_button("A")
                            else:
                                self.update_state(ModeStarterStates.EXIT_MENUS)
                                context.message = "Checking if shiny..."
                                continue

                        case ModeStarterStates.EXIT_MENUS:
                            if get_task("SCRIPTMOVEMENT_MOVEOBJECTS").get("isActive", False):
                                context.emulator.press_button("B")
                            elif not read_symbol("sStartMenuWindowId") == bytearray(b'\x01'):
                                context.emulator.press_button("Start")
                            elif get_task("TASK_STARTMENUHANDLEINPUT").get("isActive", False) or get_task("TASK_HANDLECHOOSEMONINPUT").get("isActive", False) or get_task("TASK_HANDLESELECTIONMENUINPUT").get("isActive", False):
                                context.emulator.press_button("A")
                            elif get_task("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", False):
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.LOG_STARTER:
                            encounter_pokemon(get_party()[0])
                            opponent_changed()  # Prevent opponent from being logged if starter is shiny
                            return

                case Regions.JOHTO_STARTERS:
                    match self.state:
                        case ModeStarterStates.PARTY_FULL:
                            console.print(
                                "[red]Your party is full, make some room before using the Johto starters mode!"
                            )
                            context.bot_mode = "Manual"
                            return

                        case ModeStarterStates.RESET:
                            context.emulator.reset()
                            self.update_state(ModeStarterStates.TITLE)

                        case ModeStarterStates.TITLE:
                            match get_game_state():
                                case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                                    context.emulator.press_button("A")
                                case GameState.OVERWORLD:
                                    self.update_state(ModeStarterStates.OVERWORLD)
                                    continue
                    
                        
                        case ModeStarterStates.OVERWORLD:
                            context.message = "Pathing to starter..."
                            if trainer.get_coords()[0] != ["Cyndaquil", "Totodile", "Chikorita"].index(context.selected_pokemon)+8:
                                follow_path(
                                    [(["Cyndaquil", "Totodile", "Chikorita"].index(context.selected_pokemon)+8 , 5)]
                                )
                            elif not trainer.get_facing_direction() == "Up":
                                context.emulator.press_button("Up")
                            else:
                                self.start_party_length = len(get_party())
                                if get_task("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                    context.emulator.press_button("A")
                                else:
                                    self.update_state(ModeStarterStates.YES_NO)
                                    continue

                        case ModeStarterStates.YES_NO:
                            if get_task("TASK_HANDLEYESNOINPUT").get("isActive", False):
                                context.emulator.press_button("B")
                            else:
                                context.message = "Waiting for a unique frame before continuing..."
                                self.update_state(ModeStarterStates.RNG_CHECK)
                                continue

                        case ModeStarterStates.RNG_CHECK:
                            if config.cheats.starters_rng:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                            else:
                                rng = unpack_uint32(read_symbol("gRngValue"))
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    if context.random_starter:
                                        save_rng_state_history("Random_Johto", self.rng_history)
                                    else:
                                        save_rng_state_history(context.selected_pokemon, self.rng_history)
                                    self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                    continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if len(get_party()) == self.start_party_length:
                                if config.cheats.starters_rng:
                                    write_symbol("gRngValue", generate_guaranteed_shiny_rng_seed(trainer.get_tid(), trainer.get_sid()))
                                context.emulator.press_button("A")
                            else:
                                self.update_state(ModeStarterStates.EXIT_MENUS)
                                continue

                        case ModeStarterStates.EXIT_MENUS:
                            if config.cheats.starters:
                                self.update_state(ModeStarterStates.CHECK_STARTER)
                                continue
                            else:
                                if get_task("TASK_POKEMONPICWINDOW").get("isActive", False):
                                    context.emulator.press_button("B")
                                elif get_task("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                    context.emulator.press_button("B")
                                else:
                                    self.update_state(ModeStarterStates.CHECK_STARTER)
                                    continue

                        case ModeStarterStates.CHECK_STARTER:
                            if config.cheats.starters:
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue
                            elif get_task("SCRIPTMOVEMENT_MOVEOBJECTS").get("isActive", False):
                                context.emulator.press_button("B")
                            elif not read_symbol("sStartMenuWindowId") == bytearray(b'\x01'):
                                context.emulator.press_button("Start")
                            elif not read_symbol("sStartMenuCursorPos") == bytearray(b'\x01'):
                                context.emulator.press_button("Down")
                            elif (read_symbol("sStartMenuCursorPos") == bytearray(b'\x01') and get_task("TASK_SHOWSTARTMENU").get("isActive", False)) or get_task("TASK_HANDLECHOOSEMONINPUT").get("isActive", False):
                                context.emulator.press_button("A")
                            elif get_task("TASK_HANDLESLECTIONMENUINPUT").get("isActive", False):
                                context.emulator.press_button("A")
                            elif not get_task("TASK_HANDLEINPUT").get("isActive", False) and not get_task("TASK_CHANGESUMMARYMON").get("isActive", False):
                                context.emulator.press_button("A")
                            else:
                                if ", met at  È5, LITTLEROOT TOWN." in decode_string(read_symbol("gStringVar4")):
                                    print("auidjhw")
                                    self.update_state(ModeStarterStates.LOG_STARTER)
                                else:
                                    context.emulator.press_button("Down")

                        case ModeStarterStates.LOG_STARTER:
                            party = get_party()
                            encounter_pokemon(party[len(party) - 1])
                            opponent_changed()  # Prevent opponent from being logged if starter is shiny
                            return

                case Regions.HOENN_STARTERS:
                    match self.state:
                        case ModeStarterStates.RESET:
                            context.emulator.reset()
                            self.update_state(ModeStarterStates.TITLE)

                        case ModeStarterStates.TITLE:
                            game_state = get_game_state()
                            match game_state:
                                case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                                    context.emulator.press_button("A")
                                case GameState.OVERWORLD:  # TODO assumes trainer is on Route 101, facing bag
                                    if get_task(self.task_map_popup):
                                        self.update_state(ModeStarterStates.OVERWORLD)
                                        continue
                                    
                        case ModeStarterStates.OVERWORLD:
                            if get_game_state() != GameState.CHOOSE_STARTER:
                                context.emulator.press_button("A")
                            else:
                                self.update_state(ModeStarterStates.BAG_MENU)
                                continue

                        case ModeStarterStates.BAG_MENU:
                            cursor_task = get_task(self.task_bag_cursor).get("data", False)
                            if cursor_task:
                                cursor_pos = cursor_task[0]
                                if cursor_pos > self.bag_position:
                                    context.emulator.press_button("Left")
                                elif cursor_pos < self.bag_position:
                                    context.emulator.press_button("Right")
                                elif cursor_pos == self.bag_position:
                                    self.update_state(ModeStarterStates.SELECT_STARTER)
                                    continue

                        case ModeStarterStates.SELECT_STARTER:
                            confirm = get_task(self.task_confirm).get("isActive", False)
                            if not confirm:
                                context.emulator.press_button("A")
                            else:
                                context.message = "Waiting for a unique frame before continuing..."
                                self.update_state(ModeStarterStates.RNG_CHECK)
                                continue

                        case ModeStarterStates.RNG_CHECK:
                            if config.cheats.starters_rng:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                            else:
                                rng = unpack_uint32(read_symbol("gRngValue"))
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    if context.random_starter:
                                        save_rng_state_history("Random_Hoenn", self.rng_history)
                                    else:
                                        save_rng_state_history(context.selected_pokemon, self.rng_history)
                                    self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                    continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if config.cheats.starters:
                                if len(get_party()) > 0:
                                    self.update_state(ModeStarterStates.LOG_STARTER)
                                context.emulator.press_button("A")
                            else:
                                confirm = get_task(self.task_confirm).get("isActive", False)
                                if confirm and get_game_state() != GameState.BATTLE:
                                    if config.cheats.starters_rng:
                                        write_symbol("gRngValue", generate_guaranteed_shiny_rng_seed(trainer.get_tid(), trainer.get_sid()))
                                    context.emulator.press_button("A")
                                else:
                                    self.update_state(ModeStarterStates.THROW_BALL)
                                    continue

                        # Check for ball being thrown
                        case ModeStarterStates.THROW_BALL:
                            if not get_task(self.task_ball_throw).get("isActive", False):
                                context.emulator.press_button("B")
                            else:
                                self.update_state(ModeStarterStates.STARTER_CRY)
                                continue

                        case ModeStarterStates.STARTER_CRY:
                            if get_task("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", False):
                                context.emulator.press_button("A")
                            else:
                                self.update_state(ModeStarterStates.STARTER_CRY_END)
                                continue

                        case ModeStarterStates.STARTER_CRY_END:  # Ensures starter sprite is fully visible before resetting
                            if not get_task("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", True):
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.LOG_STARTER:
                            encounter_pokemon(get_party()[0])
                            opponent_changed()  # Prevent opponent from being logged if starter is shiny
                            return
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
