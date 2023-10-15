from enum import Enum

from modules.Gui import GetEmulator
from modules.Memory import GetTask, GetGameState, GameState
from modules.Trainer import trainer, RunningStates


class SpinStates(Enum):
    IDLE = 0
    CHANGING_DIRECTION = 1


class FishingStates(Enum):
    IDLE = 0
    FISHING = 1
    BATTLE_INIT = 2


class ModeSpin:
    def __init__(self):
        self.state: SpinStates = SpinStates.IDLE
        self.clockwise = ["Up", "Right", "Down", "Left"]

    def get_next_direction(self, current_direction):
        current_index = self.clockwise.index(current_direction)
        next_index = (current_index + 1) % 4
        return self.clockwise[next_index]

    def update_state(self, state: SpinStates):
        self.state = state

    def step(self):
        match self.state:
            case SpinStates.IDLE:
                if trainer.GetRunningState() == RunningStates.NOT_MOVING:
                    GetEmulator().PressButton(self.get_next_direction(trainer.GetFacingDirection()))
                else:
                    self.update_state(SpinStates.CHANGING_DIRECTION)

            case SpinStates.CHANGING_DIRECTION:
                while trainer.GetRunningState() == RunningStates.TURN_DIRECTION and GetGameState() != GameState.BATTLE:
                    yield
                else:
                    return
        yield


class ModeFishing:
    def __init__(self):
        self.state: FishingStates = FishingStates.IDLE

    def update_state(self, state: FishingStates):
        self.state = state

    def step(self):
        match self.state:
            case FishingStates.IDLE:
                while True:
                    task = GetTask("TASK_FISHING")
                    if task == {} or not task["isActive"]:
                        GetEmulator().PressButton("Select")  # TODO assumes the player has a rod registered
                    else:
                        self.update_state(FishingStates.FISHING)
                        break
                    yield

            case FishingStates.FISHING:
                while True:
                    task = GetTask("TASK_FISHING")
                    if task["data"][0] == 7:  # `Fishing_WaitForA`
                        GetEmulator().PressButton("A")
                    elif task["data"][0] == 10:  # `Fishing_StartEncounter`
                        self.update_state(FishingStates.BATTLE_INIT)
                        break
                    elif task["data"][0] == 15:  # `Fishing_EndNoMon`
                        GetEmulator().PressButton("B")
                        self.update_state(FishingStates.IDLE)
                        break
                    elif task == {} or not task["isActive"]:
                        self.update_state(FishingStates.IDLE)
                        break
                    yield

            case FishingStates.BATTLE_INIT:
                while True:
                    if GetGameState() == GameState.BATTLE:
                        return
                    else:
                        GetEmulator().PressButton("A")
                    yield
        yield
