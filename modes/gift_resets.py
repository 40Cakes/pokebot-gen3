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
from modules.pokemon import get_opponent, get_party, opponent_changed
from modules.tasks import task_is_active


class ModeStaticGiftResetsStates(Enum):
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
    CHECK_PARTY = auto()

class ModeStaticGiftResets:
    def __init__(self) -> None:
        if not context.config.cheats.random_soft_reset_rng:
            self.rng_history: list = get_rng_state_history()

        self.frame_count = None
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
                            context.message = "Waiting for a unique frame before continuing..."
                            self.update_state(ModeStaticGiftResetsStates.RNG_CHECK)
                            continue

                        case "POKEMON FIRE" | "POKEMON LEAF", GameState.TITLE_SCREEN:
                            context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))

                        case "POKEMON FIRE" | "POKEMON LEAF", GameState.MAIN_MENU:
                            if task_is_active("Task_HandleMenuInput"):
                                context.message = "Waiting for a unique frame before continuing..."
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
                        write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                    self.update_state(ModeStaticGiftResetsStates.OVERWORLD)

                case ModeStaticGiftResetsStates.OVERWORLD:
                    if self.start_party_size == len(get_party()):
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeStaticGiftResetsStates.LOG_OPPONENT)


                case ModeStaticGiftResetsStates.LOG_OPPONENT:
                    if context.config.cheats.random_soft_reset_rng:
                        encounter_pokemon(get_party()[self.start_party_size])
                        self.update_state(ModeStaticGiftResetsStates.INJECT_RNG)
                        return
                    else: 
                        self.update_state(ModeStaticGiftResetsStates.CHECK_PARTY)

                case ModeStaticGiftResetsStates.CHECK_PARTY:
                    #complete messages
                    if self.start_party_size == len(get_party()+1):
                        context.emulator.press_button("B")
                        #if Task_DrawFieldMessage isnt active
                        # press start
                        context.emulator.press_button("Start")
                        
                        
                            
                    #dont nickname
                    #open start menu
                    #open pokemon menu
                    #navigate to get_party()[start_party_size]
                    #open summary
                    #log_encounter get_party()[start_party_size]
                    return

            yield
