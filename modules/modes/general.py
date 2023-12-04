from enum import Enum

from modules.context import context
from modules.memory import get_game_state, GameState
from modules.tasks import get_task
from modules.player import get_player_avatar, RunningState, TileTransitionState, AcroBikeState


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
            player = get_player_avatar()
            match (player.running_state, player.tile_transition_state):
                case (RunningState.NOT_MOVING, TileTransitionState.NOT_MOVING):
                    context.emulator.press_button(self.get_next_direction(player.facing_direction))
                case (RunningState.TURN_DIRECTION, TileTransitionState.CENTERING):
                    if get_game_state() == GameState.BATTLE:
                        return
            yield


class ModeFishing:
    def step(self):
        while True:
            task_fishing = get_task("Task_Fishing")
            if task_fishing is not None:
                match task_fishing.data[0]:
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
            player = get_player_avatar()
            match (player.acro_bike_state, player.tile_transition_state, player.is_on_bike):
                case (AcroBikeState.NORMAL, TileTransitionState.NOT_MOVING, False):
                    context.emulator.press_button("Select")  # TODO assumes player has the Acro Bike registered
                case (AcroBikeState.HOPPING_WHEELIE, TileTransitionState.CENTERING, True):
                    if get_game_state() == GameState.BATTLE:
                        context.emulator.release_button("B")
                        return
                case (AcroBikeState.STANDING_WHEELIE, TileTransitionState.NOT_MOVING, True):
                    context.emulator.hold_button("B")
                case _:
                    context.emulator.press_button("B")
            yield
