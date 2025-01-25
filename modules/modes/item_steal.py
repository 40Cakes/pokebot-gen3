from typing import Generator

from modules.battle_state import BattleOutcome
from modules.battle_strategies import BattleStrategy
from modules.battle_strategies.item_stealing import ItemStealingBattleStrategy
from modules.encounter import EncounterInfo
from modules.map import get_map_data_for_current_position
from modules.modes import BotMode, BattleAction, BotModeError
from modules.modes.util import map_has_pokemon_center_nearby
from modules.modes.util.pokecenter_loop import PokecenterLoopController
from modules.pokemon_party import get_party


class ItemStealMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Item Steal"

    @staticmethod
    def is_selectable() -> bool:
        current_location = get_map_data_for_current_position()
        if current_location is None:
            return False

        party = get_party()
        if not party.has_pokemon_with_move("Thief") and not party.has_pokemon_with_move("Covet"):
            return False

        return current_location.has_encounters and map_has_pokemon_center_nearby(current_location.map_group_and_number)

    def __init__(self):
        super().__init__()
        self._controller = PokecenterLoopController()
        self._controller.battle_strategy = ItemStealingBattleStrategy

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        return self._controller.on_battle_started(encounter)

    def on_battle_ended(self, outcome: BattleOutcome) -> None:
        self._controller.on_battle_ended()

    def on_whiteout(self) -> bool:
        return self._controller.on_whiteout()

    def run(self) -> Generator:
        party = get_party()
        if not party.has_pokemon_with_move("Thief") and not party.has_pokemon_with_move("Covet"):
            raise BotModeError(
                "You do not have a Pokémon that knows either Thief or Covet. One of these is needed to steal items."
            )

        self._controller.verify_on_start()
        yield from self._controller.run()
