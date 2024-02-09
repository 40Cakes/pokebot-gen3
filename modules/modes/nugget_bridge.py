from typing import Generator

from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.map_data import MapFRLG
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon import get_party
from ._interface import BotMode, BotModeError
from ._util import navigate_to, walk_one_tile, follow_path, wait_for_n_frames


class NuggetBridgeMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Nugget Bridge"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_frlg:
            return get_player_avatar().map_group_and_number in [
                MapFRLG.ROUTE24,
                MapFRLG.CERULEAN_CITY,
                MapFRLG.CERULEAN_CITY_POKEMON_CENTER_1F,
            ]
        else:
            return False

    def __init__(self):
        super().__init__()
        self._has_whited_out = False

    def on_whiteout(self) -> bool:
        self._has_whited_out = True
        return True

    def run(self) -> Generator:
        if get_event_flag("HIDE_NUGGET_BRIDGE_ROCKET"):
            raise BotModeError(f"Unfortunately, you've already received the nugget. You cannot use this mode.")
        if not context.config.battle.battle:
            raise BotModeError(f'Please set "battle: true" in battle.yml to use this mode.')
        if len(get_party()) > 1:
            raise BotModeError(f"Deposit all but one Pokémon to use this mode.")
        if get_party()[0].level > 6:
            raise BotModeError(
                f"Please use a Pokémon that is level 6 or lower.\nThis means you will lose to the rocket instead of defeating him.\nYou can find level 6 Pokémon on Route 4."
            )

        while True:
            if get_player_avatar().map_group_and_number == MapFRLG.CERULEAN_CITY_POKEMON_CENTER_1F:
                nugget_count = get_item_bag().quantity_of(get_item_by_name("Nugget"))
                context.message = (
                    "Bag contains " + str(nugget_count) + " nuggets.\nTotal value: ₽" + f"{nugget_count * 5000:,}"
                )
                yield from wait_for_n_frames(30)
                context.emulator.press_button("B")
                yield from navigate_to(7, 8)
                yield from walk_one_tile("Down")
            if get_player_avatar().map_group_and_number == MapFRLG.CERULEAN_CITY:
                yield from follow_path([(10, 20), (10, 12), (23, 12), (23, 0)])
                yield from walk_one_tile("Up")
            if get_player_avatar().map_group_and_number == MapFRLG.ROUTE24:
                yield from navigate_to(11, 16)
                self._has_whited_out = False
                context.emulator.press_button("Up")
                while not self._has_whited_out:
                    context.emulator.press_button("B")
                    yield
