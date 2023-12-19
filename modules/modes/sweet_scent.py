from enum import Enum, auto
from modules.context import context
from modules.encounter import encounter_pokemon
from modules.memory import (
    get_game_state,
    GameState
)
from modules.pokemon import get_opponent
from modules.tasks import task_is_active
from modules.menuing import StartMenuNavigator, PokemonPartyMenuNavigator
from modules.pokemon import get_party


class ModeSweetScentStates(Enum):
    RESET = auto()
    SELECT_SCENT = auto()
    OVERWORLD = auto()
    BATTLE = auto()
    OPPONENT_CRY_START = auto()
    OPPONENT_CRY_END = auto()
    LOG_OPPONENT = auto()


class ModeSweetScent:
    def __init__(self) -> None:
        self.navigator = None
        self.state: ModeSweetScentStates = ModeSweetScentStates.RESET

    def update_state(self, state: ModeSweetScentStates) -> None:
        self.state: ModeSweetScentStates = state

    def step(self):
        while True:
            match self.state:
                case ModeSweetScentStates.RESET:
                    if task_is_active("Task_HandleChooseMonInput"):
                        self.update_state(ModeSweetScentStates.SELECT_SCENT)
                    elif not task_is_active("Task_RunPerStepCallback") or task_is_active("Task_ShowStartMenu"):
                        context.emulator.press_button("B")
                        yield
                    else:
                        self.update_state(ModeSweetScentStates.OVERWORLD)
                    continue 

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
                    if self.navigator is None:
                        scent_poke = None
                        for num, poke in enumerate(get_party()):
                            if "SWEET SCENT" in str(poke.moves).upper():
                                scent_poke = num
                                break
                        if scent_poke is None:
                            raise Exception("No Pokemon with Sweet Scent in party")
                            context.set_manual_mode()
                            break
                        self.navigator = PokemonPartyMenuNavigator(scent_poke, "sweet_scent")
                    else:
                        yield from self.navigator.step()
                        match self.navigator.current_step:
                            case "exit":
                                self.navigator = None
                                self.update_state(ModeSweetScentStates.BATTLE)
                                continue
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
