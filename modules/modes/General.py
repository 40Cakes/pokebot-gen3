from enum import Enum

from modules.Gui import GetEmulator
from modules.Memory import GetTask, GetGameState, GameState
from modules.Pokemon import OpponentChanged, GetOpponent
from modules.Stats import LogEncounter
from modules.Trainer import trainer, RunningStates, TileTransitionStates
from modules.modes.Battle import encounter_pokemon


class TaskFishing(Enum):
    INIT = 0
    GET_ROD_OUT = 1
    WAIT_BEFORE_DOTS = 2
    INIT_DOTS = 3
    SHOW_DOTS = 4
    CHECK_FOR_BITE = 5
    GOT_BITE = 6
    WAIT_FOR_A = 7
    CHECK_MORE_DOTS = 8
    MON_ON_HOOK = 9
    START_ENCOUNTER = 10
    NOT_EVEN_NIBBLE = 11
    GOT_AWAY = 12
    NO_MON = 13
    PUT_ROD_AWAY = 14
    END_NO_MON = 15


class ModeSpin:
    def __init__(self):
        self.clockwise = ["Up", "Right", "Down", "Left"]

    def get_next_direction(self, current_direction):
        current_index = self.clockwise.index(current_direction)
        next_index = (current_index + 1) % 4
        return self.clockwise[next_index]

    def step(self):
        while True:
            if trainer.GetRunningState() == RunningStates.NOT_MOVING:
                GetEmulator().PressButton(self.get_next_direction(trainer.GetFacingDirection()))
            elif trainer.GetTileTransitionState() == TileTransitionStates.CENTERING:
                if GetGameState() in [GameState.BATTLE, GameState.PARTY_MENU]:
                    if OpponentChanged():
                        LogEncounter(GetOpponent())
                        continue
                    else:
                        while True:
                            yield from encounter_pokemon()
            yield


class ModeFishing:
    def step(self):
        while True:
            task = GetTask("TASK_FISHING")
            if task.get("isActive", False):
                match task["data"][0]:
                    case TaskFishing.WAIT_FOR_A.value | TaskFishing.END_NO_MON.value:
                        GetEmulator().PressButton("A")
                    case TaskFishing.NOT_EVEN_NIBBLE.value:
                        GetEmulator().PressButton("B")
                    case TaskFishing.START_ENCOUNTER.value:
                        GetEmulator().PressButton("A")
            else:
                if GetGameState() in [GameState.BATTLE, GameState.PARTY_MENU]:
                    if OpponentChanged():
                        LogEncounter(GetOpponent())
                        continue
                    else:
                        while True:
                            yield from encounter_pokemon()
                GetEmulator().PressButton("Select")
            yield
