from typing import Generator

from modules.context import context
from modules.map import get_map_data_for_current_position
from modules.modes import BattleAction
from modules.pokemon_party import get_party
from ._asserts import assert_party_has_damaging_move
from ._interface import BotMode, BotModeError
from .util import change_lead_party_pokemon
from .util.map import map_has_pokemon_center_nearby
from .util.pokecenter_loop import PokecenterLoopController
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy
from ..battle_strategies.level_balancing import LevelBalancingBattleStrategy
from ..battle_strategies.level_up import LevelUpLeadBattleStrategy
from ..encounter import EncounterInfo
from ..gui.multi_select_window import ask_for_choice, Selection, ask_for_confirmation
from ..runtime import get_sprites_path
from ..sprites import get_sprite


class LevelGrindMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Level Grind"

    @staticmethod
    def is_selectable() -> bool:
        current_location = get_map_data_for_current_position()
        if current_location is None:
            return False

        return current_location.has_encounters and map_has_pokemon_center_nearby(current_location.map_group_and_number)

    def __init__(self):
        super().__init__()
        self._controller = PokecenterLoopController()

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        return self._controller.on_battle_started(encounter)

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        return self._controller.on_battle_ended()

    def on_whiteout(self) -> bool:
        return self._controller.on_whiteout()

    def run(self) -> Generator:
        # Check training spot first to see if it has encounters to not print multi choices windows for nothing
        self._controller.verify_on_start()

        party_lead_pokemon = get_party().non_eggs[0]
        level_mode_choice = self._ask_for_leveling_mode(party_lead_pokemon)

        if level_mode_choice is None:
            context.set_manual_mode()
            yield
            return

        if level_mode_choice.startswith("Level-balance"):
            self._controller.battle_strategy = LevelBalancingBattleStrategy
            party_lead_index = LevelBalancingBattleStrategy().choose_new_lead_after_battle()
            if party_lead_index != None:
                yield from change_lead_party_pokemon(party_lead_index)
        else:
            self._controller.battle_strategy = LevelUpLeadBattleStrategy
            self._controller._focus_on_lead_pokemon = True
            assert_party_has_damaging_move("No Pokémon in the party has a usable attacking move!")

            if not LevelUpLeadBattleStrategy().pokemon_can_battle(party_lead_pokemon):
                user_confirmed = ask_for_confirmation(
                    "Your party leader has no battle moves. The bot will maybe swap with other Pokémon depending on your bot configuration, causing them to gain XP. Are you sure you want to proceed with this strategy?"
                )

                if not user_confirmed:
                    context.set_manual_mode()
                    yield
                    return

                if context.config.battle.lead_cannot_battle_action == "flee":
                    raise BotModeError(
                        "Cannot level grind because your leader has no battle moves and lead_cannot_battle_action is set to flee!"
                    )

                if not user_confirmed:
                    context.set_manual_mode()

        yield from self._controller.run()

    def _get_training_spot(self):
        training_spot = get_map_data_for_current_position()
        if not training_spot.has_encounters:
            raise BotModeError("There are no encounters on this tile.")
        return training_spot

    def _get_party_lead(self):
        for index, pokemon in enumerate(get_party()):
            if not pokemon.is_egg:
                return pokemon, index
        raise BotModeError("No valid Pokémon found in the party.")

    def _ask_for_leveling_mode(self, party_lead_pokemon):
        return ask_for_choice(
            [
                Selection(
                    f"Level only first one\nin party ({party_lead_pokemon.species_name_for_stats})",
                    get_sprite(party_lead_pokemon),
                ),
                Selection("Level-balance all\nparty Pokémon", get_sprites_path() / "items" / "Rare Candy.png"),
            ],
            "What to level?",
        )
