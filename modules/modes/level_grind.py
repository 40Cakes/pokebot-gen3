from typing import Generator

from modules.context import context
from modules.map import get_map_data_for_current_position
from modules.map_data import get_map_enum
from modules.modes import BattleAction
from modules.player import get_player_avatar
from modules.pokemon import StatusCondition
from modules.pokemon_party import get_party
from ._asserts import assert_party_has_damaging_move
from ._interface import BotMode, BotModeError
from .util import navigate_to, heal_in_pokemon_center, change_lead_party_pokemon, spin
from .util.map import map_has_pokemon_center_nearby, find_closest_pokemon_center
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy, DefaultBattleStrategy
from ..battle_strategies.level_balancing import LevelBalancingBattleStrategy
from ..battle_strategies.level_up import LevelUpLeadBattleStrategy
from ..encounter import handle_encounter, EncounterInfo
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
        self._leave_pokemon_center = False
        self._go_healing = True
        self._level_balance = False

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        action = handle_encounter(encounter, enable_auto_battle=True)
        if action is BattleAction.Fight:
            if self._level_balance:
                return LevelBalancingBattleStrategy()
            else:
                return LevelUpLeadBattleStrategy()
        else:
            return action

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        lead_pokemon = get_party()[0]

        if self._level_balance:
            if (
                not DefaultBattleStrategy().pokemon_can_battle(lead_pokemon)
                or lead_pokemon.status_condition is not StatusCondition.Healthy
            ):
                self._go_healing = True
        else:
            if lead_pokemon.current_hp_percentage < context.config.battle.hp_threshold:
                self._go_healing = True

            lead_pokemon_has_damaging_moves = False
            lead_pokemon_has_damaging_move_with_pp = False
            for learned_move in lead_pokemon.moves:
                if (
                    learned_move is not None
                    and learned_move.move.base_power > 1
                    and learned_move.move.name not in context.config.battle.banned_moves
                ):
                    lead_pokemon_has_damaging_moves = True
                    if learned_move.pp > 0:
                        lead_pokemon_has_damaging_move_with_pp = True
            if lead_pokemon_has_damaging_moves and not lead_pokemon_has_damaging_move_with_pp:
                self._go_healing = True

            if not LevelUpLeadBattleStrategy().party_can_battle():
                self._go_healing = True

    def on_whiteout(self) -> bool:
        self._leave_pokemon_center = True
        return True

    def run(self) -> Generator:
        # Check training spot first to see if it has encounters to not print multi choices windows for nothing
        training_spot = self._get_training_spot()

        party_lead_pokemon, party_lead_index = self._get_party_lead()
        level_mode_choice = self._ask_for_leveling_mode(party_lead_pokemon)

        if level_mode_choice is None:
            context.set_manual_mode()
            yield
            return

        if level_mode_choice.startswith("Level-balance"):
            self._level_balance = True
        else:
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

                if user_confirmed:
                    self._level_balance = False
                else:
                    context.set_manual_mode()

        if self._level_balance:
            party_lead_index = LevelBalancingBattleStrategy().choose_new_lead_after_battle()

        if party_lead_index:
            yield from change_lead_party_pokemon(party_lead_index)

        pokemon_center = find_closest_pokemon_center(training_spot)

        yield from self._leveling_loop(training_spot, pokemon_center)

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

    def _leveling_loop(self, training_spot, pokemon_center):
        training_spot_map = get_map_enum(training_spot)
        training_spot_coordinates = training_spot.local_position

        while True:
            if self._leave_pokemon_center:
                yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
            elif self._go_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._go_healing = False

            yield from navigate_to(training_spot_map, training_spot_coordinates)
            yield from spin(stop_condition=lambda: self._go_healing or self._leave_pokemon_center)
