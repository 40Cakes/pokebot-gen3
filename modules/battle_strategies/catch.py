from modules.battle_state import BattleState, BattlePokemon
from modules.battle_strategies import BattleStrategy, SafariTurnAction
from modules.battle_strategies import TurnAction
from modules.context import context
from modules.items import Item, get_item_bag
from modules.map import get_map_data_for_current_position
from modules.pokedex import get_pokedex
from modules.pokemon import Pokemon, Move, get_type_by_name, StatusCondition


class CatchStrategy(BattleStrategy):
    def party_can_battle(self) -> bool:
        return True

    def pokemon_can_battle(self, pokemon: Pokemon) -> bool:
        return True

    def should_flee_after_faint(self, battle_state: BattleState) -> bool:
        return False

    def choose_new_lead_after_battle(self) -> int | None:
        return None

    def choose_new_lead_after_faint(self, battle_state: BattleState) -> int:
        context.set_manual_mode()
        return 0

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        ball_to_throw = self._get_best_poke_ball(battle_state)
        if ball_to_throw is None:
            context.message = "Player does not have any Poké Balls, cannot catch."
            return TurnAction.switch_to_manual()

        if battle_state.opponent.active_battler.status_permanent == StatusCondition.Healthy:
            status_move = self._get_best_status_changing_move(battle_state)
            if status_move is not None:
                return TurnAction.use_move(status_move)

        return TurnAction.use_item(ball_to_throw)

    def decide_turn_in_double_battle(self, battle_state: BattleState, battler_index: int) -> tuple["TurnAction", any]:
        return self.decide_turn(battle_state)

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        return SafariTurnAction.switch_to_manual()

    def _get_best_status_changing_move(self, battle_state: BattleState) -> int | None:
        status_move_index: int | None = None
        status_move_value: float = 0

        for index in range(len(battle_state.own_side.active_battler.moves)):
            learned_move = battle_state.own_side.active_battler.moves[index]
            if learned_move is None or learned_move.pp == 0:
                continue

            opponent_ability = battle_state.opponent.active_battler.ability.name

            value = 0
            if learned_move.move.effect == "SLEEP" and opponent_ability not in ("Insomnia", "Vital Spirit"):
                value = 2 * learned_move.move.accuracy
            if learned_move.move.effect == "PARALYZE" and opponent_ability != "Limber":
                value = 1.5 * learned_move.move.accuracy
            if status_move_value < value:
                status_move_index = index
                status_move_value = value

        return status_move_index

    def _get_best_poke_ball(self, battle_state: BattleState) -> Item | None:
        best_poke_ball: Item | None = None
        best_catch_rate_multiplier: float = 0
        for ball in get_item_bag().poke_balls:
            catch_rate_multiplier = self._get_poke_ball_catch_rate_multiplier(battle_state, ball.item)

            if best_catch_rate_multiplier < catch_rate_multiplier:
                best_poke_ball = ball.item
                best_catch_rate_multiplier = catch_rate_multiplier

        return best_poke_ball

    def _get_poke_ball_catch_rate_multiplier(self, battle_state: BattleState, ball: Item) -> float:
        opponent = battle_state.opponent.active_battler
        catch_rate_multiplier = 1
        match ball.index:
            # Master Ball -- we never choose to throw this one, should be the player's choice
            case 1:
                catch_rate_multiplier = -1

            # Ultra Ball
            case 2:
                catch_rate_multiplier = 2

            # Great Ball, Safari Ball:
            case 3 | 5:
                catch_rate_multiplier = 1.5

            # Net Ball
            case 6:
                water = get_type_by_name("Water")
                bug = get_type_by_name("Bug")
                if opponent.species.has_type(water) or opponent.species.has_type(bug):
                    catch_rate_multiplier = 3

            # Dive Ball
            case 7:
                if get_map_data_for_current_position().map_type == "Underwater":
                    catch_rate_multiplier = 3.5

            # Nest Ball
            case 8:
                if opponent.level < 40:
                    catch_rate_multiplier = max(1.0, (40 - opponent.level) / 10)

            # Repeat Ball
            case 9:
                if opponent.species in get_pokedex().owned_species:
                    catch_rate_multiplier = 3

            # Timer Ball
            case 10:
                catch_rate_multiplier = min(4.0, (10 + battle_state.current_turn) / 10)

        return catch_rate_multiplier
