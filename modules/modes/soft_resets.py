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
)
from modules.pokemon import get_opponent, opponent_changed
from modules.tasks import task_is_active


class ModeStaticSoftResetsStates(Enum):
    RESET = auto()
    TITLE = auto()
    WAIT_FRAMES = auto()
    OVERWORLD = auto()
    INJECT_RNG = auto()
    RNG_CHECK = auto()
    BATTLE = auto()
    OPPONENT_CRY_START = auto()
    OPPONENT_CRY_END = auto()
    LOG_OPPONENT = auto()


class ModeStaticSoftResets:
    def __init__(self) -> None:
        if not context.config.cheats.random_soft_reset_rng:
            self.rng_history: list = get_rng_state_history()

        self.frame_count = None
        self.state: ModeStaticSoftResetsStates = ModeStaticSoftResetsStates.RESET

    def update_state(self, state: ModeStaticSoftResetsStates) -> None:
        self.state: ModeStaticSoftResetsStates = state

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
                case ModeStaticSoftResetsStates.RESET:
                    context.emulator.reset()
                    self.update_state(ModeStaticSoftResetsStates.TITLE)

                case ModeStaticSoftResetsStates.TITLE:
                    match context.rom.game_title, get_game_state():
                        case "POKEMON RUBY" | "POKEMON SAPP" | "POKEMON EMER", GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                            context.emulator.press_button("A")

                        case "POKEMON RUBY" | "POKEMON SAPP" | "POKEMON EMER", GameState.OVERWORLD:
                            context.message = "Waiting for a unique frame before continuing..."
                            self.update_state(ModeStaticSoftResetsStates.RNG_CHECK)
                            continue

                        case "POKEMON FIRE" | "POKEMON LEAF", GameState.TITLE_SCREEN:
                            context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))

                        case "POKEMON FIRE" | "POKEMON LEAF", GameState.MAIN_MENU:
                            if task_is_active("Task_HandleMenuInput"):
                                context.message = "Waiting for a unique frame before continuing..."
                                self.update_state(ModeStaticSoftResetsStates.RNG_CHECK)
                                continue

                case ModeStaticSoftResetsStates.RNG_CHECK:
                    if context.config.cheats.random_soft_reset_rng:
                        self.update_state(ModeStaticSoftResetsStates.WAIT_FRAMES)
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
                            self.update_state(ModeStaticSoftResetsStates.WAIT_FRAMES)
                            continue

                case ModeStaticSoftResetsStates.WAIT_FRAMES:
                    if self.wait_frames(5):
                        self.update_state(ModeStaticSoftResetsStates.INJECT_RNG)
                    else:
                        pass

                case ModeStaticSoftResetsStates.INJECT_RNG:
                    if context.config.cheats.random_soft_reset_rng:
                        write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                    self.update_state(ModeStaticSoftResetsStates.OVERWORLD)

                case ModeStaticSoftResetsStates.OVERWORLD:
                    if not opponent_changed():
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeStaticSoftResetsStates.BATTLE)
                        continue

                case ModeStaticSoftResetsStates.BATTLE:
                    if get_game_state() != GameState.BATTLE:
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeStaticSoftResetsStates.OPPONENT_CRY_START)
                        continue

                case ModeStaticSoftResetsStates.OPPONENT_CRY_START:
                    if not task_is_active("Task_DuckBGMForPokemonCry"):
                        context.emulator.press_button("B")
                    else:
                        self.update_state(ModeStaticSoftResetsStates.OPPONENT_CRY_END)
                        continue

                # Ensure opponent sprite is fully visible before resetting
                case ModeStaticSoftResetsStates.OPPONENT_CRY_END:
                    if task_is_active("Task_DuckBGMForPokemonCry"):
                        pass
                    else:
                        self.update_state(ModeStaticSoftResetsStates.LOG_OPPONENT)
                        continue

                case ModeStaticSoftResetsStates.LOG_OPPONENT:
                    encounter_pokemon(get_opponent())
                    return

            yield
