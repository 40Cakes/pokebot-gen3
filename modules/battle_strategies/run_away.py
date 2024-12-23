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
            strongest_move = util.get_strongest_move_against(
                battle_state.own_side.active_battler, battle_state.opponent.active_battler
            )

            if strongest_move is not None:
                return TurnAction.use_move(
                    util.get_strongest_move_against(
                        battle_state.own_side.active_battler, battle_state.opponent.active_battler
                    )
                )
            else:
                # Even if escape chance is 0, maybe we can escape next turn
                return TurnAction.run_away()

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        return SafariTurnAction.run_away()
