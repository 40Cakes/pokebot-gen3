from typing import Generator

from modules.context import context
from modules.map_data import MapFRLG, MapRSE
from modules.modes import get_bot_mode_by_name
from modules.player import get_player_avatar
from modules.tasks import get_global_script_context
from ._asserts import assert_auto_battle
from ._interface import BotMode, BotModeError
from ._util import (
    deprecated_navigate_to_on_current_map,
    wait_for_task_to_start_and_finish,
    walk_one_tile,
)
from ..battle import BattleOutcome


class PokecenterLoopMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Pokecenter Loop"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_frlg:
            allowed_maps = [MapFRLG.ROUTE2]
        elif context.rom.is_emerald:
            allowed_maps = [MapRSE.ROUTE102]
        else:
            allowed_maps = []
        return get_player_avatar().map_group_and_number in allowed_maps

    def __init__(self):
        super().__init__()
        assert_auto_battle("AutoBattle needs to be enabled for this mode to work")
        self._use_bike = False
        self._go_healing = False
        self._controller = get_bot_mode_by_name("Spin")().run()

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if outcome == BattleOutcome.RanAway:
            self._go_healing = True
        else:
            self._go_healing = False

    def run(self) -> Generator:
        if context.rom.is_frlg:
            match get_player_avatar().map_group_and_number:
                case MapFRLG.ROUTE2:

                    def path():
                        # navigate to Pokecenter
                        yield from deprecated_navigate_to_on_current_map(8, 0)
                        yield from walk_one_tile("Up")
                        yield from deprecated_navigate_to_on_current_map(17, 26)
                        yield from walk_one_tile("Up")
                        yield from deprecated_navigate_to_on_current_map(7, 4)
                        # Healing
                        yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "A")
                        yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "A")
                        while get_global_script_context().is_active:
                            context.emulator.press_button("B")
                            yield
                        yield
                        # navigate back to route
                        yield from deprecated_navigate_to_on_current_map(7, 8)
                        yield from walk_one_tile("Down")
                        yield from deprecated_navigate_to_on_current_map(20, 39)
                        yield from walk_one_tile("Down")
                        yield from deprecated_navigate_to_on_current_map(8, 2)

                case _:
                    raise BotModeError("You are not on the right map.")
        elif context.rom.is_emerald:
            match get_player_avatar().map_group_and_number:
                case MapRSE.ROUTE102:

                    def path():
                        # navigate to Pokecenter
                        yield from deprecated_navigate_to_on_current_map(0, 7)
                        yield from walk_one_tile("Left")
                        yield from deprecated_navigate_to_on_current_map(20, 17)
                        yield from walk_one_tile("Up")
                        yield from deprecated_navigate_to_on_current_map(7, 4)
                        # healing
                        yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
                        yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
                        while get_global_script_context().is_active:
                            context.emulator.press_button("B")
                            yield
                        yield
                        # navigate back to route
                        yield from deprecated_navigate_to_on_current_map(7, 8)
                        yield from walk_one_tile("Down")
                        yield from deprecated_navigate_to_on_current_map(29, 17)
                        yield from walk_one_tile("Right")
                        yield from deprecated_navigate_to_on_current_map(4, 7)

                case _:
                    raise BotModeError("You are not on the right map.")

        while True:
            # path to pokecenter, heal and back
            yield from path()
            self._go_healing = False
            # spin untill RanAway from battle
            while not self._go_healing:
                next(self._controller)
                yield
