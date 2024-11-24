from modules.battle_state import BattleState
from modules.battle_strategies import DefaultBattleStrategy, TurnAction, BattleStrategyUtil
from modules.context import context
from modules.pokemon import Pokemon, get_party, StatusCondition
from modules.modes import BotModeError


class NoRotateLeadDefaultBattleStrategy(DefaultBattleStrategy):

    def choose_new_lead_after_battle(self) -> int | None:
        return None

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        """
        Decides the turn's action based on the current battle state.
        """
        util = BattleStrategyUtil(battle_state)
        current_battler = get_party()[battle_state.own_side.active_battler.party_index]

        def handle_lead_cannot_battle() -> tuple["TurnAction", any]:
            action = context.config.battle.lead_cannot_battle_action
            if action == "flee":
                return self._escape(battle_state)
            elif action == "rotate" and util.can_switch():
                if len(util.get_usable_party_indices(battle_state)) > 0:
                    return TurnAction.rotate_lead(util.select_rotation_target(battle_state))
            return self._escape(battle_state)

        if not any(util.move_is_usable(move) for move in current_battler.moves) or not super()._pokemon_has_enough_hp(
            current_battler
        ):
            return handle_lead_cannot_battle()

        try:
            strongest_move = util.get_strongest_move_against(
                battle_state.own_side.active_battler, battle_state.opponent.active_battler
            )
        except BotModeError:
            return handle_lead_cannot_battle()
        return TurnAction.use_move(strongest_move)

    def party_can_battle(self) -> bool:
        party = get_party()

        for pokemon in party:
            if pokemon.is_egg or pokemon.is_empty:
                continue

            if super()._pokemon_has_enough_hp(pokemon) and pokemon.status_condition is StatusCondition.Healthy:
                for move in pokemon.moves:
                    if (
                        move is not None
                        and move.move.base_power > 0
                        and move.pp > 0
                        and move.move.name not in context.config.battle.banned_moves
                    ):
                        return True
        return False

    def pokemon_can_battle(self, pokemon: Pokemon) -> bool:
        return any(
            move is not None and move.move.base_power > 0 and move.move.name not in context.config.battle.banned_moves
            for move in pokemon.moves
        )

    def _escape(self, battle_state: BattleState):
        util = BattleStrategyUtil(battle_state)
        best_escape_method = util.get_best_escape_method()

        if best_escape_method is not None:
            return best_escape_method

        raise BotModeError(
            "Unable to escape: 'lead_cannot_battle_action' is set to 'flee', but the flee chance is 0%. "
            "Switching to manual mode."
        )
