from enum import Enum

from modules.Gui import GetEmulator
from modules.Memory import GetTask, GetGameState, GameState
from modules.Trainer import trainer, RunningStates


class ModeSpinStates(Enum):
    IDLE = 0
    CHANGING_DIRECTION = 1


class ModeFishingStates(Enum):
    FISHING = 0
    BATTLE_INIT = 1


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
        self.state: ModeSpinStates = ModeSpinStates.IDLE
        self.clockwise = ["Up", "Right", "Down", "Left"]

    def get_next_direction(self, current_direction):
        current_index = self.clockwise.index(current_direction)
        next_index = (current_index + 1) % 4
        return self.clockwise[next_index]

    def update_state(self, state: ModeSpinStates):
        self.state: ModeSpinStates = state

    def step(self):
        while True:
            match self.state:
                case ModeSpinStates.IDLE:
                    if trainer.GetRunningState() == RunningStates.NOT_MOVING:
                        GetEmulator().PressButton(self.get_next_direction(trainer.GetFacingDirection()))
                    else:
                        self.update_state(ModeSpinStates.CHANGING_DIRECTION)
                        continue

                case ModeSpinStates.CHANGING_DIRECTION:
                    if trainer.GetRunningState() != RunningStates.TURN_DIRECTION or GetGameState() == GameState.BATTLE:
                        return
            yield


class ModeFishing:
    def __init__(self):
        self.state: ModeFishingStates = ModeFishingStates.FISHING

    def update_state(self, state: ModeFishingStates):
        self.state: ModeFishingStates = state

    def step(self):
        while True:
            match self.state:
                case ModeFishingStates.FISHING:
                    task = GetTask("TASK_FISHING")
                    if task.get("isActive", False):
                        match task["data"][0]:
                            case TaskFishing.WAIT_FOR_A.value | TaskFishing.END_NO_MON.value:
                                GetEmulator().PressButton("A")
                            case TaskFishing.NOT_EVEN_NIBBLE.value:
                                GetEmulator().PressButton("B")
                            case TaskFishing.START_ENCOUNTER.value:
                                self.update_state(ModeFishingStates.BATTLE_INIT)
                                continue
                    else:
                        GetEmulator().PressButton("Select")

                case ModeFishingStates.BATTLE_INIT:
                    if GetGameState() == GameState.BATTLE:
                        return
                    else:
                        GetEmulator().PressButton("A")
            yield
