from enum import Enum
from typing import Generator

from modules.context import context
from modules.memory import get_game_state, GameState
from modules.player import get_player_avatar
from modules.tasks import get_task
from ._asserts import assert_registered_item
from ._interface import BotMode


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


class FishingMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Fishing"

    @staticmethod
    def is_selectable() -> bool:
        player = get_player_avatar()
        targeted_tile = player.map_location_in_front
        if targeted_tile is None:
            return False
        return targeted_tile.is_surfable

    def run(self) -> Generator:
        assert_registered_item(
            expected_items=["Old Rod", "Good Rod", "Super Rod"],
            error_message="You need to register a fishing rod for the Select button.",
        )

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
                context.emulator.press_button("Select")
            yield
