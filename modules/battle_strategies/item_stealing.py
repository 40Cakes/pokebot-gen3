from typing import Optional

from modules.battle_state import BattleState, BattlePokemon, TemporaryStatus
from modules.battle_strategies import DefaultBattleStrategy, BattleStrategyUtil
from modules.battle_strategies import TurnAction
from modules.pokemon import Pokemon, get_type_by_name
from modules.pokemon_party import get_party


class ItemStealingBattleStrategy(DefaultBattleStrategy):
    def __init__(self):
        super().__init__()
        self._victims = set()

    def party_can_battle(self) -> bool:
        return any([self._can_steal_item(pokemon, None) for pokemon in get_party().non_eggs])

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", Optional[any]]:
        battler = battle_state.own_side.active_battler
        opponent = battle_state.opponent.active_battler

        if len(opponent.species.held_items) and (
            opponent.personality_value not in self._victims or opponent.held_item is not None
        ):
            if self._can_steal_item(battler, opponent):
                for index, learned_move in enumerate(battler.moves):
                    if learned_move.move.name in ("Covet", "Thief"):
                        self._victims.add(opponent.personality_value)
                        return TurnAction.use_move(index)
            else:
                best_thief_index = self._get_strongest_thief_index()
                if best_thief_index is not None and best_thief_index != battler.party_index:
                    return TurnAction.rotate_lead(best_thief_index)
        elif not battle_state.is_trainer_battle and (
            escape_method := BattleStrategyUtil(battle_state).get_best_escape_method()
        ):
            return escape_method

        return super().decide_turn(battle_state)

    def choose_new_lead_after_battle(self) -> int | None:
        best_thief_index = self._get_strongest_thief_index()
        return best_thief_index if best_thief_index is not None and best_thief_index > 0 else None

    def choose_new_lead_after_faint(self, battle_state: BattleState) -> int:
        best_thief_index = self._get_strongest_thief_index()
        return best_thief_index if best_thief_index is not None else super().choose_new_lead_after_faint(battle_state)

    def _can_steal_item(self, pokemon: BattlePokemon | Pokemon, opponent: BattlePokemon | None) -> bool:
        possible_moves = ("Thief", "Covet")
        if opponent is not None:
            if opponent.ability.name == "Sticky Hold":
                return False

            if TemporaryStatus.Substitute in opponent.status_temporary:
                return False

            if get_type_by_name("Ghost") in opponent.types:
                possible_moves = ("Thief",)

        if pokemon.current_hp == 0:
            return False

        for learned_move in pokemon.moves:
            if learned_move is not None and learned_move.move.name in possible_moves and learned_move.pp > 0:
                if isinstance(pokemon, BattlePokemon) and pokemon.disabled_move is learned_move.move:
                    continue
                else:
                    return True

        return False

    def _get_strongest_thief_index(self) -> int | None:
        strongest_thief = None
        strongest_thief_level = 0
        for index, pokemon in enumerate(get_party()):
            if not pokemon.is_egg and self._can_steal_item(pokemon, None) and pokemon.level > strongest_thief_level:
                strongest_thief = index
                strongest_thief_level = pokemon.level

        return strongest_thief
