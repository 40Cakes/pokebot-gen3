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
from modules.menuing import StartMenuNavigator, PokemonPartyMenuNavigator
from modules.menu_parsers import parse_party_menu
from modules.pokemon import get_party
from modules.battle import get_battle_state


class ModeSweetScentStates(Enum):
    RESET = auto()
    TITLE = auto()
    SELECT_SCENT = auto()
    WAIT_FRAMES = auto()
    OVERWORLD = auto()
    INJECT_RNG = auto()
    RNG_CHECK = auto()
    BATTLE = auto()
    OPPONENT_CRY_START = auto()
    OPPONENT_CRY_END = auto()
    LOG_OPPONENT = auto()
    USE_SCENT = auto()


class ModeSweetScent:
    def __init__(self) -> None:
        if not context.config.cheats.random_soft_reset_rng:
            self.rng_history: list = get_rng_state_history()

        self.frame_count = None
        self.navigator = None
        self.state: ModeSweetScentStates = ModeSweetScentStates.RESET

    def update_state(self, state: ModeSweetScentStates) -> None:
        self.state: ModeSweetScentStates = state

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
                case ModeSweetScentStates.RESET:
                    match context.rom.game_title:
                        case "POKEMON FIRE" | "POKEMON LEAF":
                            context.emulator.reset()
                            self.update_state(ModeSweetScentStates.TITLE)
                            continue
                        case "POKEMON RUBY" | "POKEMON SAPP" | "POKEMON EMER":
                            if task_is_active("Task_HandleChooseMonInput"):
                                self.update_state(ModeSweetScentStates.SELECT_SCENT)
                            elif not task_is_active("Task_RunPerStepCallback") or task_is_active("Task_ShowStartMenu"):
                                context.emulator.press_button("B")
                                yield
                            else:
                                self.update_state(ModeSweetScentStates.OVERWORLD)
                    continue
                
                case ModeSweetScentStates.TITLE:
                    match get_game_state(), read_symbol("gQuestLogState"):
                        case GameState.TITLE_SCREEN, _:
                            context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))
                        case GameState.MAIN_MENU, _:
                            context.emulator.press_button("A")
                        case GameState.OVERWORLD, bytearray(b"\x00"):
                            self.update_state(ModeSweetScentStates.OVERWORLD)
                        case GameState.OVERWORLD, _:
                            context.emulator.press_button("B")
                    yield

                case ModeSweetScentStates.OVERWORLD:
                    if self.navigator is None:
                        self.navigator = StartMenuNavigator("POKEMON")
                    else:
                        yield from self.navigator.step()
                        match self.navigator.current_step:
                            case "exit":
                                self.navigator = None
                                self.update_state(ModeSweetScentStates.SELECT_SCENT)
                                continue
                    continue
                
                case ModeSweetScentStates.SELECT_SCENT:
                    scent_poke = None
                    for num, poke in enumerate(get_party()):
                        if "Sweet Scent" in str(poke.moves):
                            scent_poke = num
                            break
                    
                    if scent_poke is None:
                        raise Exception("No Pokemon with Sweet Scent in party")
                        context.set_manual_mode()
                        break
                    else:
                        if self.navigator is None:
                            self.navigator = PokemonPartyMenuNavigator(scent_poke, "hover_scent")
                        else:
                            yield from self.navigator.step()
                            match self.navigator.current_step:
                                case "exit":
                                    self.navigator = None
                                    self.update_state(ModeSweetScentStates.RNG_CHECK)
                                    continue
                                    # context.set_manual_mode()
                                    # break
                        continue
                
                case ModeSweetScentStates.RNG_CHECK:
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
                        self.update_state(ModeSweetScentStates.USE_SCENT)
                        continue

                
                case ModeSweetScentStates.USE_SCENT:
                    if not opponent_changed():
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeSweetScentStates.BATTLE)
                        continue

                case ModeSweetScentStates.BATTLE:
                    if get_game_state() != GameState.BATTLE:
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeSweetScentStates.OPPONENT_CRY_START)
                        continue

                case ModeSweetScentStates.OPPONENT_CRY_START:
                    if not task_is_active("Task_DuckBGMForPokemonCry"):
                        context.emulator.press_button("B")
                    else:
                        self.update_state(ModeSweetScentStates.OPPONENT_CRY_END)
                        continue

                # Ensure opponent sprite is fully visible before resetting
                case ModeSweetScentStates.OPPONENT_CRY_END:
                    if task_is_active("Task_DuckBGMForPokemonCry"):
                        pass
                    else:
                        self.update_state(ModeSweetScentStates.LOG_OPPONENT)
                        continue

                case ModeSweetScentStates.LOG_OPPONENT:
                    encounter_pokemon(get_opponent())
                    return

            yield
