from modules.battle_state import BattleState
from modules.battle_strategies import (
    TurnAction,
    SafariTurnAction,
    BattleStrategyUtil,
    DefaultBattleStrategy,
)


class RunAwayStrategy(DefaultBattleStrategy):
    def should_flee_after_faint(self, battle_state: BattleState) -> bool:
        return True

    def choose_new_lead_after_battle(self) -> int | None:
        return False

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        util = BattleStrategyUtil(battle_state)
        best_escape_method = util.get_best_escape_method()
        if best_escape_method is not None:
            return best_escape_method
        else:
            return TurnAction.use_move(
                util.get_strongest_move_against(
                    battle_state.own_side.active_battler, battle_state.opponent.active_battler
                )
            )

    def decide_turn_in_double_battle(self, battle_state: BattleState, battler_index: int) -> tuple["TurnAction", any]:
        util = BattleStrategyUtil(battle_state)
        battler = battle_state.own_side.left_battler if battler_index == 0 else battle_state.own_side.right_battler
        best_escape_method = util.get_best_escape_method()
        if best_escape_method is not None:
            return best_escape_method
        elif battle_state.opponent.left_battler is not None:
            opponent = battle_state.opponent.left_battler
            return TurnAction.use_move_against_left_side_opponent(util.get_strongest_move_against(battler, opponent))
        else:
            opponent = battle_state.opponent.right_battler
            return TurnAction.use_move_against_right_side_opponent(util.get_strongest_move_against(battler, opponent))

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        return SafariTurnAction.run_away()
