import random
from enum import Enum, auto

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.files import get_rng_state_history, save_rng_state_history
from modules.memory import (
    read_symbol,
    get_game_state,
    GameState,
    write_symbol,
    unpack_uint32,
    pack_uint32,
    get_event_flag,
)
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.pokemon import get_party
from modules.player import get_player_avatar
from modules.tasks import task_is_active


class ModeStaticGiftResetsStates(Enum):
    RESET = auto()
    TITLE = auto()
    WAIT_FRAMES = auto()
    OVERWORLD = auto()
    INJECT_RNG = auto()
    RNG_CHECK = auto()
    LOG_ENCOUNTER = auto()
    CHECK_ENCOUNTER = auto()
    CLEAR_MESSAGES = auto()
    CHECK_PARTY = auto()


class ModeStaticGiftResets:
    def __init__(self) -> None:
        if not context.config.cheats.random_soft_reset_rng:
            self.rng_history: list = get_rng_state_history()

        self.frame_count = None
        self.navigator = None
        self.map = get_player_avatar().map_location.map_name
        self.state: ModeStaticGiftResetsStates = ModeStaticGiftResetsStates.RESET

    def update_state(self, state: ModeStaticGiftResetsStates) -> None:
        self.state: ModeStaticGiftResetsStates = state

    def wait_frames(self, frames: int) -> bool:
        if not self.frame_count:
            self.frame_count = context.emulator.get_frame_count()
        elif context.emulator.get_frame_count() < self.frame_count + frames:
            return False
        else:
            self.frame_count = 0
            return True

    def step(self):
        while True:
            match self.state:
                case ModeStaticGiftResetsStates.RESET:
                    context.emulator.reset()
                    self.update_state(ModeStaticGiftResetsStates.TITLE)

                case ModeStaticGiftResetsStates.TITLE:
                    match context.rom.game_title, get_game_state():
                        case "POKEMON RUBY" | "POKEMON SAPP" | "POKEMON EMER", GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                            context.emulator.press_button("A")

                        case "POKEMON RUBY" | "POKEMON SAPP" | "POKEMON EMER", GameState.OVERWORLD:
                            context.message = (
                                "Waiting for a unique frame before continuing..."
                            )
                            self.update_state(ModeStaticGiftResetsStates.RNG_CHECK)
                            continue

                        case "POKEMON FIRE" | "POKEMON LEAF", GameState.TITLE_SCREEN:
                            context.emulator.press_button(
                                random.choice(["A", "Start", "Left", "Right", "Up"])
                            )

                        case "POKEMON FIRE" | "POKEMON LEAF", GameState.MAIN_MENU:
                            if task_is_active("Task_HandleMenuInput"):
                                context.message = (
                                    "Waiting for a unique frame before continuing..."
                                )
                                self.update_state(ModeStaticGiftResetsStates.RNG_CHECK)
                                continue

                case ModeStaticGiftResetsStates.RNG_CHECK:
                    self.start_party_size = len(get_party())
                    if context.config.cheats.random_soft_reset_rng:
                        self.update_state(ModeStaticGiftResetsStates.WAIT_FRAMES)
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
                            self.update_state(ModeStaticGiftResetsStates.WAIT_FRAMES)
                            continue

                case ModeStaticGiftResetsStates.WAIT_FRAMES:
                    if self.wait_frames(5):
                        self.update_state(ModeStaticGiftResetsStates.INJECT_RNG)
                    else:
                        pass

                case ModeStaticGiftResetsStates.INJECT_RNG:
                    if context.config.cheats.random_soft_reset_rng:
                        write_symbol(
                            "gRngValue", pack_uint32(random.randint(0, 2**32 - 1))
                        )
                    self.update_state(ModeStaticGiftResetsStates.OVERWORLD)

                case ModeStaticGiftResetsStates.OVERWORLD:
                    if self.start_party_size == len(get_party()):
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeStaticGiftResetsStates.CHECK_ENCOUNTER)

                case ModeStaticGiftResetsStates.CHECK_ENCOUNTER:
                    if context.config.cheats.random_soft_reset_rng:
                        self.update_state(ModeStaticGiftResetsStates.LOG_ENCOUNTER)
                        continue
                    else:
                        self.update_state(ModeStaticGiftResetsStates.CLEAR_MESSAGES)

                case ModeStaticGiftResetsStates.CLEAR_MESSAGES:
                    context.message = self.map
                    if task_is_active("Task_DrawFieldMessageBox"):
                        context.emulator.press_button("B")
                    elif task_is_active("Task_YesNoMenu_HandleInput"):
                        context.emulator.press_button("B")
                    elif task_is_active("Task_HandleYesNoInput"):
                        context.emulator.press_button("B")
                    elif (
                        self.map == "SILPH CO."
                        and get_event_flag("FLAG_GOT_LAPRAS_FROM_SILPH") == False
                    ):
                        context.emulator.press_button("B")
                    elif (
                        self.map == "ROUTE 119"
                        and get_event_flag("FLAG_RECEIVED_CASTFORM") == False
                    ):
                        context.emulator.press_button("B")
                    elif self.navigator is None:
                        self.navigator = StartMenuNavigator("POKEMON")
                    else:
                        yield from self.navigator.step()
                        match self.navigator.current_step:
                            case "exit":
                                self.navigator = None
                                self.update_state(
                                    ModeStaticGiftResetsStates.CHECK_PARTY
                                )
                                continue

                case ModeStaticGiftResetsStates.CHECK_PARTY:
                    if self.navigator is None:
                        self.navigator = PokemonPartyMenuNavigator(
                            len(get_party()) - 1, "summary"
                        )
                    else:
                        yield from self.navigator.step()
                        match self.navigator.current_step:
                            case "exit":
                                self.navigator = None
                                self.update_state(
                                    ModeStaticGiftResetsStates.LOG_ENCOUNTER
                                )
                                continue
                    continue
                case ModeStaticGiftResetsStates.LOG_ENCOUNTER:
                    encounter_pokemon(get_party()[self.start_party_size])
                    self.update_state(ModeStaticGiftResetsStates.INJECT_RNG)
                    return

            yield
