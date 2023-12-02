from enum import Enum, auto

from modules.context import context
from modules.memory import get_task, get_game_state, GameState
from modules.trainer import trainer, RunningStates, TileTransitionStates, AcroBikeStates


class TaskFishing(Enum):
    INIT = auto()
    GET_ROD_OUT = auto()
    WAIT_BEFORE_DOTS = auto()
    INIT_DOTS = auto()
    SHOW_DOTS = auto()
    CHECK_FOR_BITE = auto()
    GOT_BITE = auto()
    WAIT_FOR_A = auto()
    CHECK_MORE_DOTS = auto()
    MON_ON_HOOK = auto()
    START_ENCOUNTER = auto()
    NOT_EVEN_NIBBLE = auto()
    GOT_AWAY = auto()
    NO_MON = auto()
    PUT_ROD_AWAY = auto()
    END_NO_MON = auto()


class ModeSpin:
    def __init__(self):
        self.clockwise = ["Up", "Right", "Down", "Left"]

    def get_next_direction(self, current_direction):
        current_index = self.clockwise.index(current_direction)
        next_index = (current_index + 1) % 4
        return self.clockwise[next_index]

    def step(self):
        while True:
            match (trainer.get_running_state(), trainer.get_tile_transition_state()):
                case (RunningStates.NOT_MOVING, TileTransitionStates.NOT_MOVING):
                    context.emulator.press_button(self.get_next_direction(trainer.get_facing_direction()))
                case (RunningStates.TURN_DIRECTION, TileTransitionStates.CENTERING):
                    if get_game_state() == GameState.BATTLE:
                        return
            yield


class ModeFishing:
    def step(self):
        while True:
            task_fishing = get_task("TASK_FISHING")
            if task_fishing.get("isActive", False):
                match task_fishing["data"][0]:
                    case TaskFishing.WAIT_FOR_A.value | TaskFishing.END_NO_MON.value:
                        context.emulator.press_button("A")
                    case TaskFishing.NOT_EVEN_NIBBLE.value:
                        context.emulator.press_button("B")
                    case TaskFishing.START_ENCOUNTER.value:
                        context.emulator.press_button("A")
            elif get_game_state() == GameState.BATTLE:
                return
            else:
                context.emulator.press_button("Select")  # TODO assumes player has a rod registered
            yield


class ModeBunnyHop:
    def step(self):
        while True:
            match (trainer.get_acro_bike_state(), trainer.get_tile_transition_state(), trainer.get_on_bike()):
                case (AcroBikeStates.NORMAL, TileTransitionStates.NOT_MOVING, False):
                    context.emulator.press_button("Select")  # TODO assumes player has the Acro Bike registered
                case (AcroBikeStates.HOPPING_WHEELIE, TileTransitionStates.CENTERING, True):
                    if get_game_state() == GameState.BATTLE:
                        context.emulator.release_button("B")
                        return
                case (AcroBikeStates.STANDING_WHEELIE, TileTransitionStates.NOT_MOVING, True):
                    context.emulator.hold_button("B")
                case _:
                    context.emulator.press_button("B")
            yield
