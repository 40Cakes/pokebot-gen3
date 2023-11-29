import random
from enum import Enum

from modules.console import console
from modules.context import context
from modules.encounter import encounter_pokemon
from modules.files import get_rng_state_history, save_rng_state_history
from modules.memory import read_symbol, get_game_state, GameState, get_task, write_symbol, unpack_uint32, pack_uint32, get_event_flag
from modules.navigation import follow_path
from modules.pokemon import get_party, opponent_changed
from modules.trainer import trainer
from modules.game import decode_string
from modules.map import get_map_objects

config = context.config


class Regions(Enum):
    KANTO_STARTERS = 0
    JOHTO_STARTERS = 1
    HOENN_STARTERS = 2


class BagPositions(Enum):
    TREECKO = 0
    TORCHIC = 1
    MUDKIP = 2


class ModeStarterStates(Enum):
    RESET = 0
    TITLE = 1
    OVERWORLD = 2
    BAG_MENU = 3
    INJECT_RNG = 4
    SELECT_STARTER = 5
    CONFIRM_STARTER = 6
    RNG_CHECK = 7
    STARTER_BATTLE = 8
    THROW_BALL = 9
    STARTER_CRY = 10
    STARTER_CRY_END = 11
    YES_NO = 12
    EXIT_MENUS = 13
    FOLLOW_PATH = 14
    CHECK_STARTER = 15
    PARTY_FULL = 16
    LOG_STARTER = 17
    INCOMPATIBLE = 18


class ModeStarters:
    def __init__(self) -> None:
        self.state: ModeStarterStates = ModeStarterStates.RESET
        self.kanto_starters: list = ["Bulbasaur",  "Squirtle", "Charmander"]
        self.johto_starters: list = ["Cyndaquil", "Totodile", "Chikorita"]
        self.hoenn_starters: list = ["Treecko", "Torchic", "Mudkip"]
        
        johto_objects = 0
        for item in get_map_objects():
            if str(item) in ["Entity at (8, 4)","Entity at (9, 4)","Entity at (10, 4)"]:
                johto_objects += 1
        
        if (config.general.starter.value in self.kanto_starters or config.general.random) and context.rom.game_title in [
            "POKEMON LEAF",
            "POKEMON FIRE",
        ]:
            self.region: Regions = Regions.KANTO_STARTERS
            if config.general.random:
                config.general.set_mon(random.choice(self.kanto_starters))
        
        elif (config.general.starter.value in self.johto_starters or config.general.random) and context.rom.game_title == "POKEMON EMER" and johto_objects >= 2: 
            self.region: Regions = Regions.JOHTO_STARTERS
            self.start_party_length: int = 0
            if config.general.random:
                config.general.set_mon(random.choice(self.johto_starters))
            if len(get_party()) == 6:
                self.update_state(ModeStarterStates.PARTY_FULL)

        elif config.general.starter.value in self.hoenn_starters or config.general.random:
            if config.general.random:
                config.general.set_mon(random.choice(self.hoenn_starters))
            self.bag_position: int = BagPositions[config.general.starter.value.upper()].value
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
            else:
                self.state = ModeStarterStates.INCOMPATIBLE
        else:
            self.state = ModeStarterStates.INCOMPATIBLE

        if not config.cheats.starters_rng:
            self.rng_history: list = get_rng_state_history(config.general.starter.value)

    def update_state(self, state: ModeStarterStates):
        self.state: ModeStarterStates = state

    def step(self):
        if self.state == ModeStarterStates.INCOMPATIBLE:
            message = (
                f"Starter `{config.general.starter.value}` is incompatible, update `starter` in config "
                f"file `general.yml` to a valid starter for {context.rom.game_name} and restart the bot!"
            )
            console.print(f"[red bold]{message}")
            context.message = message
            context.bot_mode = "Manual"
            return

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
                                    context.emulator.press_button("A")
                                case GameState.MAIN_MENU:  # TODO assumes trainer is in Oak's lab, facing a ball
                                    if get_task("TASK_HANDLEMENUINPUT").get("isActive", False):
                                        context.message = "Waiting for a unique frame before continuing..."
                                        self.update_state(ModeStarterStates.RNG_CHECK)
                                        continue

                        case ModeStarterStates.RNG_CHECK:
                            if config.cheats.starters_rng:
                                self.update_state(ModeStarterStates.OVERWORLD)
                            else:
                                rng = unpack_uint32(read_symbol("gRngValue"))
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    save_rng_state_history(config.general.starter.value, self.rng_history)
                                    self.update_state(ModeStarterStates.OVERWORLD)
                                    continue

                        case ModeStarterStates.OVERWORLD:
                            context.message = "Pathing to starter..."
                            starter = config.general.starter.value
                            if get_task("TASK_HANDLEMENUINPUT").get("isActive", False):
                                context.emulator.press_button("A")
                            elif get_task("TASK_RUNTIMEBASEDEVENTS").get("data", False) != bytearray(b'\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'):
                                context.emulator.press_button("B")
                            elif trainer.get_coords()[0] != self.kanto_starters.index(starter)+8:
                                follow_path(
                                    [(self.kanto_starters.index(starter)+8 , 5)]
                                )
                            elif not trainer.get_facing_direction() == "Up":
                                context.emulator.press_button("Up")
                            else:
                                self.start_party_length = len(get_party())
                                if not get_task("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                    context.emulator.press_button("A")
                                else:
                                    self.update_state(ModeStarterStates.INJECT_RNG)
                                    continue

                        case ModeStarterStates.INJECT_RNG:
                            if config.cheats.starters_rng:
                                write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                            self.update_state(ModeStarterStates.SELECT_STARTER)

                        case ModeStarterStates.SELECT_STARTER:  # TODO can be made slightly faster by holding B through chat
                            if get_task("TASK_DRAWFIELDMESSAGEBOX").get("isActive", False):
                                context.emulator.press_button("A")
                            elif not get_task("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                context.emulator.press_button("B")
                            else:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if len(get_party()) == 0:
                                context.emulator.press_button("A")
                            else:
                                self.update_state(ModeStarterStates.EXIT_MENUS)
                                continue

                        case ModeStarterStates.EXIT_MENUS:
                            if not config.cheats.starters:
                                if trainer.get_facing_direction() != "Down":
                                    context.emulator.press_button("B")
                                    context.emulator.hold_button("Down")
                                else:
                                    context.emulator.release_button("Down")
                                    self.update_state(ModeStarterStates.FOLLOW_PATH)
                                    continue
                            else:
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.FOLLOW_PATH:
                            follow_path(
                                [(trainer.get_coords()[0], 7), (7, 7), (7, 8)]
                            )  # TODO Revisit FollowPath rework
                            self.update_state(ModeStarterStates.CHECK_STARTER)

                        case ModeStarterStates.CHECK_STARTER:
                            if not get_task("TASK_PLAYERCONTROLLER_RESTOREBGMAFTERCRY").get("isActive", False):
                                context.emulator.press_button("B")
                            else:
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
                            starter = config.general.starter.value
                            # if get_task("TASK_HANDLEMENUINPUT").get("isActive", False):
                            #     context.emulator.press_button("A")
                            # elif get_task("TASK_RUNTIMEBASEDEVENTS").get("data", False) != bytearray(b'\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'):
                            #     context.emulator.press_button("B")
                            
                            if trainer.get_coords()[0] != self.johto_starters.index(starter)+8:
                                follow_path(
                                    [(self.johto_starters.index(starter)+8 , 5)]
                                )
                            elif not trainer.get_facing_direction() == "Up":
                                context.emulator.press_button("Up")
                            else:
                                self.start_party_length = len(get_party())
                                if get_task("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                    context.emulator.press_button("A")
                                else:
                                    self.update_state(ModeStarterStates.INJECT_RNG)
                                    continue

                        case ModeStarterStates.INJECT_RNG:
                            if config.cheats.starters_rng:
                                write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                            self.update_state(ModeStarterStates.YES_NO)

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
                                    save_rng_state_history(config.general.starter.value, self.rng_history)
                                    self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                    continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if len(get_party()) == self.start_party_length:
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
                            # config.cheats.starters = True  # TODO temporary until menu navigation is ready
                            if config.cheats.starters:  # TODO check Pokémon summary screen once menu navigation merged
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
                                self.update_state(ModeStarterStates.INJECT_RNG)
                                continue

                        case ModeStarterStates.INJECT_RNG:
                            if config.cheats.starters_rng:
                                write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                            self.update_state(ModeStarterStates.BAG_MENU)

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
                                    save_rng_state_history(config.general.starter.value, self.rng_history)
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
