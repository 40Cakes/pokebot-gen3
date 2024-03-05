from modules.battle_state import BattleState
from modules.battle_strategies import BattleStrategy, TurnAction, SafariTurnAction
from modules.pokemon import Pokemon, Move


class RunAwayStrategy(BattleStrategy):
    def party_can_battle(self) -> bool:
        return False

    def pokemon_can_battle(self, pokemon: Pokemon) -> bool:
        return False

    def which_move_should_be_replaced(self, pokemon: Pokemon, new_move: Move) -> int:
        return 4

    def should_allow_evolution(self, pokemon: Pokemon, party_index: int) -> bool:
        return False

    def should_flee_after_faint(self, battle_state: BattleState) -> bool:
        return True

    def choose_new_lead_after_battle(self) -> int | None:
        return False

    def choose_new_lead_after_faint(self, battle_state: BattleState) -> int:
        return 0

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        return TurnAction.run_away()

    def decide_turn_in_double_battle(self, battle_state: BattleState, battler_index: int) -> tuple["TurnAction", any]:
        return TurnAction.run_away()

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        return SafariTurnAction.run_away()
