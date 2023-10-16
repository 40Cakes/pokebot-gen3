import random
import struct
from enum import Enum

from modules.Config import config, ForceManualMode
from modules.Console import console
from modules.Gui import GetROM, GetEmulator
from modules.Memory import ReadSymbol, GetGameState, GameState, GetTask, WriteSymbol
from modules.Navigation import FollowPath
from modules.Pokemon import GetParty
from modules.Stats import GetRNGStateHistory, SaveRNGStateHistory, EncounterPokemon
from modules.Trainer import trainer


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
        self.kanto_starters: list = ["Bulbasaur", "Charmander", "Squirtle"]
        self.johto_starters: list = ["Chikorita", "Totodile", "Cyndaquil"]
        self.hoenn_starters: list = ["Treecko", "Torchic", "Mudkip"]

        if config["general"]["starter"] in self.kanto_starters and GetROM().game_title in [
            "POKEMON LEAF",
            "POKEMON FIRE",
        ]:
            self.region: Regions = Regions.KANTO_STARTERS

        elif config["general"]["starter"] in self.johto_starters and GetROM().game_title == "POKEMON EMER":
            self.region: Regions = Regions.JOHTO_STARTERS
            self.start_party_length: int = 0
            console.print(
                "[red]Notice: Johto starters enables the fast `starters` check option in `config/cheats.yml` by "
                "default, the shininess of the starter is checked via memhacks while start menu navigation is WIP (in "
                "future, shininess will be checked via the party summary menu)."
            )
            if len(GetParty()) == 6:
                self.update_state(ModeStarterStates.PARTY_FULL)

        elif config["general"]["starter"] in self.hoenn_starters:
            self.bag_position: int = BagPositions[config["general"]["starter"].upper()].value
            if GetROM().game_title == "POKEMON EMER":
                self.region = Regions.HOENN_STARTERS
                self.task_bag_cursor: str = "TASK_HANDLESTARTERCHOOSEINPUT"
                self.task_confirm: str = "TASK_HANDLECONFIRMSTARTERINPUT"
                self.task_ball_throw: str = "TASK_PLAYCRYWHENRELEASEDFROMBALL"
                self.task_map_popup: str = "TASK_MAPNAMEPOPUPWINDOW"
            elif GetROM().game_title in ["POKEMON RUBY", "POKEMON SAPP"]:
                self.region = Regions.HOENN_STARTERS
                self.task_bag_cursor: str = "TASK_STARTERCHOOSE2"
                self.task_confirm: str = "TASK_STARTERCHOOSE5"
                self.task_ball_throw: str = "SUB_814146C"
                self.task_map_popup: str = "TASK_MAPNAMEPOPUP"
            else:
                self.state = ModeStarterStates.INCOMPATIBLE
        else:
            self.state = ModeStarterStates.INCOMPATIBLE

        if not config["cheats"]["starters_rng"]:
            self.rng_history: list = GetRNGStateHistory(config["general"]["starter"])

    def update_state(self, state: ModeStarterStates):
        self.state: ModeStarterStates = state

    def step(self):
        if self.state == ModeStarterStates.INCOMPATIBLE:
            console.print(
                f"[red bold]Starter `{config['general']['starter']}` is incompatible, update `starter` in config "
                f"file `general.yml` to a valid starter for {GetROM().game_name} and restart the bot!"
            )
            ForceManualMode()
            return

        while True:
            match self.region:
                case Regions.KANTO_STARTERS:
                    match self.state:
                        case ModeStarterStates.RESET:
                            GetEmulator().Reset()
                            self.update_state(ModeStarterStates.TITLE)

                        case ModeStarterStates.TITLE:
                            match GetGameState():
                                case GameState.TITLE_SCREEN:
                                    GetEmulator().PressButton("A")
                                case GameState.MAIN_MENU:  # TODO assumes trainer is in Oak's lab, facing a ball
                                    if GetTask("TASK_HANDLEMENUINPUT").get("isActive", False):
                                        self.update_state(ModeStarterStates.RNG_CHECK)
                                        continue

                        case ModeStarterStates.RNG_CHECK:
                            if config["cheats"]["starters_rng"]:
                                self.update_state(ModeStarterStates.OVERWORLD)
                            else:
                                rng = int(struct.unpack("<I", ReadSymbol("gRngValue", size=4))[0])
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    SaveRNGStateHistory(config["general"]["starter"], self.rng_history)
                                    self.update_state(ModeStarterStates.OVERWORLD)
                                    continue

                        case ModeStarterStates.OVERWORLD:
                            self.start_party_length = len(GetParty())
                            if not GetTask("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.INJECT_RNG)
                                continue

                        case ModeStarterStates.INJECT_RNG:
                            if config["cheats"]["starters_rng"]:
                                WriteSymbol("gRngValue", struct.pack("<I", random.randint(0, 2**32 - 1)))
                            self.update_state(ModeStarterStates.SELECT_STARTER)

                        case ModeStarterStates.SELECT_STARTER:  # TODO can be made slightly faster by holding B through chat
                            if GetTask("TASK_DRAWFIELDMESSAGEBOX").get("isActive", False):
                                GetEmulator().PressButton("A")
                            elif not GetTask("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if len(GetParty()) == 0:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.EXIT_MENUS)
                                continue

                        case ModeStarterStates.EXIT_MENUS:
                            if not config["cheats"]["starters"]:
                                if trainer.GetFacingDirection() != "Down":
                                    GetEmulator().PressButton("B")
                                    GetEmulator().HoldButton("Down")
                                else:
                                    GetEmulator().ReleaseButton("Down")
                                    self.update_state(ModeStarterStates.FOLLOW_PATH)
                                    continue
                            else:
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.FOLLOW_PATH:
                            FollowPath([(trainer.GetCoords()[0], 7), (7, 7), (7, 8)])  # TODO Revisit FollowPath rework
                            self.update_state(ModeStarterStates.CHECK_STARTER)

                        case ModeStarterStates.CHECK_STARTER:
                            if not GetTask("TASK_PLAYERCONTROLLER_RESTOREBGMAFTERCRY").get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.LOG_STARTER:
                            EncounterPokemon(GetParty()[0])
                            return

                case Regions.JOHTO_STARTERS:
                    match self.state:
                        case ModeStarterStates.PARTY_FULL:
                            console.print(
                                "[red]Your party is full, make some room before using the Johto starters mode!"
                            )
                            ForceManualMode()
                            return

                        case ModeStarterStates.RESET:
                            GetEmulator().Reset()
                            self.update_state(ModeStarterStates.TITLE)

                        case ModeStarterStates.TITLE:
                            match GetGameState():
                                case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                                    GetEmulator().PressButton("A")
                                case GameState.OVERWORLD:
                                    self.update_state(ModeStarterStates.OVERWORLD)
                                    continue

                        case ModeStarterStates.OVERWORLD:
                            self.start_party_length = len(GetParty())
                            if GetTask("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.INJECT_RNG)
                                continue

                        case ModeStarterStates.INJECT_RNG:
                            if config["cheats"]["starters_rng"]:
                                WriteSymbol("gRngValue", struct.pack("<I", random.randint(0, 2**32 - 1)))
                            self.update_state(ModeStarterStates.YES_NO)

                        case ModeStarterStates.YES_NO:
                            if GetTask("TASK_HANDLEYESNOINPUT").get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(ModeStarterStates.RNG_CHECK)
                                continue

                        case ModeStarterStates.RNG_CHECK:
                            if config["cheats"]["starters_rng"]:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                            else:
                                rng = int(struct.unpack("<I", ReadSymbol("gRngValue", size=4))[0])
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    SaveRNGStateHistory(config["general"]["starter"], self.rng_history)
                                    self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                    continue

                        case ModeStarterStates.CONFIRM_STARTER:
                            if len(GetParty()) == self.start_party_length:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.EXIT_MENUS)
                                continue

                        case ModeStarterStates.EXIT_MENUS:
                            if config["cheats"]["starters"]:
                                self.update_state(ModeStarterStates.CHECK_STARTER)
                                continue
                            else:
                                if GetTask("TASK_POKEMONPICWINDOW").get("isActive", False):
                                    GetEmulator().PressButton("B")
                                elif GetTask("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                    GetEmulator().PressButton("B")
                                else:
                                    self.update_state(ModeStarterStates.CHECK_STARTER)
                                    continue

                        case ModeStarterStates.CHECK_STARTER:
                            config["cheats"]["starters"] = True  # TODO temporary until menu navigation is ready
                            if config["cheats"]["starters"]:     # TODO check Pokémon summary screen once menu navigation merged
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.LOG_STARTER:
                            party = GetParty()
                            EncounterPokemon(party[len(party) - 1])
                            return

                case Regions.HOENN_STARTERS:
                    match self.state:
                        case ModeStarterStates.RESET:
                            GetEmulator().Reset()
                            self.update_state(ModeStarterStates.TITLE)

                        case ModeStarterStates.TITLE:
                            game_state = GetGameState()
                            match game_state:
                                case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                                    GetEmulator().PressButton("A")
                                case GameState.OVERWORLD:  # TODO assumes trainer is on Route 101, facing bag
                                    if GetTask(self.task_map_popup):
                                        self.update_state(ModeStarterStates.OVERWORLD)
                                        continue

                        case ModeStarterStates.OVERWORLD:
                            if GetGameState() != GameState.CHOOSE_STARTER:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.INJECT_RNG)
                                continue

                        case ModeStarterStates.INJECT_RNG:
                            if config["cheats"]["starters_rng"]:
                                WriteSymbol("gRngValue", struct.pack("<I", random.randint(0, 2**32 - 1)))
                            self.update_state(ModeStarterStates.BAG_MENU)

                        case ModeStarterStates.BAG_MENU:
                            cursor_task = GetTask(self.task_bag_cursor).get("data", False)
                            if cursor_task:
                                cursor_pos = cursor_task[0]
                                if cursor_pos > self.bag_position:
                                    GetEmulator().PressButton("Left")
                                elif cursor_pos < self.bag_position:
                                    GetEmulator().PressButton("Right")
                                elif cursor_pos == self.bag_position:
                                    self.update_state(ModeStarterStates.SELECT_STARTER)
                                    continue

                        case ModeStarterStates.SELECT_STARTER:
                            confirm = GetTask(self.task_confirm).get("isActive", False)
                            if not confirm:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.RNG_CHECK)
                                continue

                        case ModeStarterStates.RNG_CHECK:
                            if config["cheats"]["starters_rng"]:
                                self.update_state(ModeStarterStates.CONFIRM_STARTER)
                            else:
                                rng = int(struct.unpack("<I", ReadSymbol("gRngValue", size=4))[0])
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    SaveRNGStateHistory(config["general"]["starter"], self.rng_history)
                                    self.update_state(ModeStarterStates.CONFIRM_STARTER)
                                    continue

                        case ModeStarterStates.CONFIRM_STARTER:
                                if config["cheats"]["starters"]:
                                    if len(GetParty()) > 0:
                                        self.update_state(ModeStarterStates.LOG_STARTER)
                                    GetEmulator().PressButton("A")
                                else:
                                    confirm = GetTask(self.task_confirm).get("isActive", False)
                                    if confirm and GetGameState() != GameState.BATTLE:
                                        GetEmulator().PressButton("A")
                                    else:
                                        self.update_state(ModeStarterStates.THROW_BALL)
                                        continue

                        # Check for ball being thrown
                        case ModeStarterStates.THROW_BALL:
                            if not GetTask(self.task_ball_throw).get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(ModeStarterStates.STARTER_CRY)
                                continue

                        case ModeStarterStates.STARTER_CRY:
                            if GetTask("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", False):
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(ModeStarterStates.STARTER_CRY_END)
                                continue

                        case ModeStarterStates.STARTER_CRY_END:  # Ensures starter sprite is fully visible before resetting
                            if not GetTask("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", True):
                                self.update_state(ModeStarterStates.LOG_STARTER)
                                continue

                        case ModeStarterStates.LOG_STARTER:
                            EncounterPokemon(GetParty()[0])
                            return
            yield
