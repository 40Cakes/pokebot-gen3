from typing import Generator

from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.map_data import MapFRLG
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon_party import get_party, get_party_size
from . import BattleAction
from ._interface import BotMode, BotModeError
from .util import navigate_to, wait_for_player_avatar_to_be_standing_still
from ..battle_strategies import BattleStrategy
from ..battle_strategies.lose_on_purpose import LoseOnPurposeBattleStrategy
from ..encounter import EncounterInfo


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

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        return LoseOnPurposeBattleStrategy()

    def on_whiteout(self) -> bool:
        self._has_whited_out = True
        return True

    def run(self) -> Generator:
        if get_event_flag("HIDE_NUGGET_BRIDGE_ROCKET"):
            raise BotModeError("Unfortunately, you've already received the nugget. You cannot use this mode.")
        if get_party_size() > 1:
            raise BotModeError("Deposit all but one Pokémon to use this mode.")
        if get_party()[0].level > 6 and get_party()[0].species.name != "Magikarp":
            raise BotModeError(
                "Please use a Pokémon that is level 6 or lower.\n"
                "This means you will lose to the rocket instead of defeating him.\n"
                "You can find level 6 Pokémon on Route 4."
            )

        while True:
            if get_player_avatar().map_group_and_number == MapFRLG.CERULEAN_CITY_POKEMON_CENTER_1F:
                nugget_count = get_item_bag().quantity_of(get_item_by_name("Nugget"))
                context.message = f"Bag contains {str(nugget_count)} nuggets.\nTotal value: ₽{nugget_count * 5000:,}"
                yield from wait_for_player_avatar_to_be_standing_still()
                yield from navigate_to(MapFRLG.CERULEAN_CITY_POKEMON_CENTER_1F, (7, 8))
            elif get_player_avatar().map_group_and_number in (MapFRLG.CERULEAN_CITY, MapFRLG.ROUTE24):
                self._has_whited_out = False
                yield from navigate_to(MapFRLG.ROUTE24, (11, 15))
                while not self._has_whited_out:
                    context.emulator.press_button("B")
                    yield
            else:
                raise BotModeError("Player is on an unexpected map. Please go to Cerulean City or Route 24.")
