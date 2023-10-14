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


class StarterStates(Enum):
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
        self.state: StarterStates = StarterStates.RESET
        self.kanto_starters: list = ["bulbasaur", "charmander", "squirtle"]
        self.johto_starters: list = ["chikorita", "totodile", "cyndaquil"]
        self.hoenn_starters: list = ["treecko", "torchic", "mudkip"]

        if config["general"]["starter"] in self.kanto_starters and GetROM().game_title in [
            "POKEMON LEAF",
            "POKEMON FIRE",
        ]:
            self.region: Regions = Regions.KANTO_STARTERS

        elif config["general"]["starter"] in self.johto_starters and GetROM().game_title == "POKEMON EMER":
            self.region: Regions = Regions.JOHTO_STARTERS
            self.start_party_length: int = 0
            config["cheats"]["starters"] = True  # TODO temporary until menu navigation is ready
            console.print(
                "[red]Notice: Johto starters enables the fast `starters` check option in `config/cheats.yml` by "
                "default, the shininess of the starter is checked via memhacks while start menu navigation is WIP (in "
                "future, shininess will be checked via the party summary menu)."
            )
            if len(GetParty()) == 6:
                self.update_state(StarterStates.PARTY_FULL)

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
                self.state = StarterStates.INCOMPATIBLE
        else:
            self.state = StarterStates.INCOMPATIBLE

        if not config["cheats"]["starters_rng"]:
            self.rng_history: list = GetRNGStateHistory(config["general"]["starter"])

    def update_state(self, state: StarterStates):
        self.state = state

    def step(self):
        if self.state == StarterStates.INCOMPATIBLE:
            console.print(
                f"[red bold]Starter `{config['general']['starter']}` is incompatible with {GetROM().game_name}!"
            )
            ForceManualMode()
            return

        match self.region:
            case Regions.KANTO_STARTERS:
                match self.state:
                    case StarterStates.RESET:
                        GetEmulator().Reset()
                        self.update_state(StarterStates.TITLE)

                    case StarterStates.TITLE:
                        while True:
                            match GetGameState():
                                case GameState.TITLE_SCREEN:
                                    GetEmulator().PressButton("A")
                                case GameState.MAIN_MENU:  # TODO assumes trainer is in Oak's lab, facing a ball
                                    if GetTask("TASK_HANDLEMENUINPUT").get("isActive", False):
                                        self.update_state(StarterStates.RNG_CHECK)
                                        break
                            yield

                    case StarterStates.RNG_CHECK:
                        if config["cheats"]["starters_rng"]:
                            self.update_state(StarterStates.OVERWORLD)
                        else:
                            while True:
                                rng = int(struct.unpack("<I", ReadSymbol("gRngValue", size=4))[0])
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    SaveRNGStateHistory(config["general"]["starter"], self.rng_history)
                                    self.update_state(StarterStates.OVERWORLD)
                                    break
                                yield

                    case StarterStates.OVERWORLD:
                        self.start_party_length = len(GetParty())
                        while True:
                            if not GetTask("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.INJECT_RNG)
                                break
                            yield

                    case StarterStates.INJECT_RNG:
                        if config["cheats"]["starters_rng"]:
                            WriteSymbol("gRngValue", struct.pack("<I", random.randint(0, 2**32 - 1)))
                        self.update_state(StarterStates.SELECT_STARTER)

                    case StarterStates.SELECT_STARTER:  # TODO can be made slightly faster by holding B through chat
                        while True:
                            if GetTask("TASK_DRAWFIELDMESSAGEBOX").get("isActive", False):
                                GetEmulator().PressButton("A")
                            elif not GetTask("TASK_SCRIPTSHOWMONPIC").get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(StarterStates.CONFIRM_STARTER)
                                break
                            yield

                    case StarterStates.CONFIRM_STARTER:
                        while True:
                            if len(GetParty()) == 0:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.EXIT_MENUS)
                                break
                            yield

                    case StarterStates.EXIT_MENUS:
                        if not config["cheats"]["starters"]:
                            while True:
                                if trainer.GetFacingDirection() != "Down":
                                    GetEmulator().PressButton("B")
                                    GetEmulator().HoldButton("Down")
                                else:
                                    GetEmulator().ReleaseButton("Down")
                                    self.update_state(StarterStates.FOLLOW_PATH)
                                    break
                                yield
                        else:
                            self.update_state(StarterStates.LOG_STARTER)
                            yield

                    case StarterStates.FOLLOW_PATH:
                        FollowPath([(trainer.GetCoords()[0], 7), (7, 7), (7, 8)])  # TODO Revisit FollowPath rework
                        self.update_state(StarterStates.CHECK_STARTER)

                    case StarterStates.CHECK_STARTER:
                        while True:
                            if GetTask("TASK_PLAYERCONTROLLER_RESTOREBGMAFTERCRY").get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(StarterStates.LOG_STARTER)
                                break
                            yield

                    case StarterStates.LOG_STARTER:
                        EncounterPokemon(GetParty()[0])
                        return

            case Regions.JOHTO_STARTERS:
                match self.state:
                    case StarterStates.PARTY_FULL:
                        console.print("[red]Your party is full, make some room before using the Johto starters mode!")
                        ForceManualMode()
                        return

                    case StarterStates.RESET:
                        GetEmulator().Reset()
                        self.update_state(StarterStates.TITLE)

                    case StarterStates.TITLE:
                        while True:
                            match GetGameState():
                                case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                                    GetEmulator().PressButton("A")
                                case GameState.OVERWORLD:
                                    self.update_state(StarterStates.OVERWORLD)
                                    break
                            yield

                    case StarterStates.OVERWORLD:
                        self.start_party_length = len(GetParty())
                        while True:
                            if GetTask("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.INJECT_RNG)
                                break
                            yield

                    case StarterStates.INJECT_RNG:
                        if config["cheats"]["starters_rng"]:
                            WriteSymbol("gRngValue", struct.pack("<I", random.randint(0, 2**32 - 1)))
                        self.update_state(StarterStates.YES_NO)

                    case StarterStates.YES_NO:
                        while True:
                            if GetTask("TASK_HANDLEYESNOINPUT").get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(StarterStates.RNG_CHECK)
                                break
                            yield

                    case StarterStates.RNG_CHECK:
                        if config["cheats"]["starters_rng"]:
                            self.update_state(StarterStates.CONFIRM_STARTER)
                        else:
                            while True:
                                rng = int(struct.unpack("<I", ReadSymbol("gRngValue", size=4))[0])
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    SaveRNGStateHistory(config["general"]["starter"], self.rng_history)
                                    self.update_state(StarterStates.CONFIRM_STARTER)
                                    break
                                yield

                    case StarterStates.CONFIRM_STARTER:
                        while True:
                            if len(GetParty()) == self.start_party_length:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.EXIT_MENUS)
                                break
                            yield

                    case StarterStates.EXIT_MENUS:
                        if not config["cheats"]["starters"]:
                            while True:
                                if GetTask("TASK_POKEMONPICWINDOW").get("isActive", False):
                                    GetEmulator().PressButton("B")
                                elif GetTask("TASK_DRAWFIELDMESSAGE").get("isActive", False):
                                    GetEmulator().PressButton("B")
                                else:
                                    break
                                yield
                        else:
                            self.update_state(StarterStates.CHECK_STARTER)
                            yield

                    case StarterStates.CHECK_STARTER:
                        while True:
                            if config["cheats"]["starters"]:
                                self.update_state(StarterStates.LOG_STARTER)
                                break
                            else:
                                break  # TODO check Pokémon summary screen once menu navigation merged
                            yield

                    case StarterStates.LOG_STARTER:
                        party = GetParty()
                        EncounterPokemon(party[len(party) - 1])
                        return

            case Regions.HOENN_STARTERS:
                match self.state:
                    case StarterStates.RESET:
                        GetEmulator().Reset()
                        self.update_state(StarterStates.TITLE)

                    case StarterStates.TITLE:
                        while True:
                            game_state = GetGameState()
                            match game_state:
                                case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                                    GetEmulator().PressButton("A")
                                case GameState.OVERWORLD:  # TODO assumes trainer is on Route 101, facing bag
                                    if GetTask(self.task_map_popup):
                                        self.update_state(StarterStates.OVERWORLD)
                                        break
                            yield

                    case StarterStates.OVERWORLD:
                        while True:
                            if GetGameState() != GameState.CHOOSE_STARTER:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.INJECT_RNG)
                                break
                            yield

                    case StarterStates.INJECT_RNG:
                        if config["cheats"]["starters_rng"]:
                            WriteSymbol("gRngValue", struct.pack("<I", random.randint(0, 2**32 - 1)))
                        self.update_state(StarterStates.BAG_MENU)

                    case StarterStates.BAG_MENU:
                        while True:
                            cursor_task = GetTask(self.task_bag_cursor).get("data", False)
                            if cursor_task:
                                cursor_pos = cursor_task[0]
                                if cursor_pos > self.bag_position:
                                    GetEmulator().PressButton("Left")
                                elif cursor_pos < self.bag_position:
                                    GetEmulator().PressButton("Right")
                                elif cursor_pos == self.bag_position:
                                    self.update_state(StarterStates.SELECT_STARTER)
                                    break
                            yield

                    case StarterStates.SELECT_STARTER:
                        while True:
                            confirm = GetTask(self.task_confirm).get("isActive", False)
                            if not confirm:
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.RNG_CHECK)
                                break
                            yield

                    case StarterStates.RNG_CHECK:
                        while True:
                            if config["cheats"]["starters_rng"]:
                                self.update_state(StarterStates.CONFIRM_STARTER)
                            else:
                                rng = int(struct.unpack("<I", ReadSymbol("gRngValue", size=4))[0])
                                if rng in self.rng_history:
                                    pass
                                else:
                                    self.rng_history.append(rng)
                                    SaveRNGStateHistory(config["general"]["starter"], self.rng_history)
                                    self.update_state(StarterStates.CONFIRM_STARTER)
                                    break
                            yield

                    case StarterStates.CONFIRM_STARTER:
                        while True:
                            if config["cheats"]["starters"]:
                                if len(GetParty()) > 0:
                                    self.update_state(StarterStates.LOG_STARTER)
                                GetEmulator().PressButton("A")
                            else:
                                confirm = GetTask(self.task_confirm).get("isActive", False)
                                if not confirm and GetGameState() == GameState.BATTLE:
                                    self.update_state(StarterStates.THROW_BALL)
                                    break
                                else:
                                    GetEmulator().PressButton("A")
                            yield

                    # Check for ball being thrown
                    case StarterStates.THROW_BALL:
                        while True:
                            if not GetTask(self.task_ball_throw).get("isActive", False):
                                GetEmulator().PressButton("B")
                            else:
                                self.update_state(StarterStates.STARTER_CRY)
                                break
                            yield

                    case StarterStates.STARTER_CRY:
                        while True:
                            if GetTask("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", False):
                                GetEmulator().PressButton("A")
                            else:
                                self.update_state(StarterStates.STARTER_CRY_END)
                                break
                            yield

                    case StarterStates.STARTER_CRY_END:  # Ensures starter sprite is fully visible before resetting
                        while True:
                            if not GetTask("TASK_DUCKBGMFORPOKEMONCRY").get("isActive", True):
                                self.update_state(StarterStates.LOG_STARTER)
                                break
                            yield

                    case StarterStates.LOG_STARTER:
                        EncounterPokemon(GetParty()[0])
                        return
        yield
