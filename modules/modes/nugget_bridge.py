from typing import Generator

from modules.data.map import MapFRLG

from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from ._interface import BotMode, BotModeError
from ._util import navigate_to, walk_one_tile, follow_path, wait_for_task_to_start_and_finish, wait_for_n_frames


class NuggetBridgeMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Nugget Bridge"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_frlg:
            allowed_maps = [
                MapFRLG.ROUTE_24.value,
                MapFRLG.CERULEAN_CITY.value,
                MapFRLG.CERULEAN_CITY_D.value,
            ]
        return get_player_avatar().map_group_and_number in allowed_maps

    def run(self) -> Generator:
        if get_event_flag("HIDE_NUGGET_BRIDGE_ROCKET"):
            raise BotModeError(f"Unfortunately, you've already received the nugget. You cannot use this mode.")
        if not context.config.battle.battle:
            raise BotModeError(f"Please set \"battle: true\" in battle.yml to use this mode.")

        while True:
            if get_player_avatar().map_group_and_number == MapFRLG.CERULEAN_CITY_D.value:
                nugget_count = get_item_bag().quantity_of(get_item_by_name("Nugget"))
                context.message = (
                    "Bag contains " + str(nugget_count) + " nuggets.\nTotal value: ₽" + f"{nugget_count * 5000:,}"
                )
                yield from wait_for_n_frames(30)
                context.emulator.press_button("B")
                yield from navigate_to(7, 8)
                yield from walk_one_tile("Down")
            if get_player_avatar().map_group_and_number == MapFRLG.CERULEAN_CITY.value:
                yield from follow_path([(10, 20), (10, 12), (23, 12), (23, 0)])
                yield from walk_one_tile("Up")
            if get_player_avatar().map_group_and_number == MapFRLG.ROUTE_24.value:
                yield from navigate_to(11, 16)
                context.emulator.press_button("Up")
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "B")
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "B")
