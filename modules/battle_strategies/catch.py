from modules.battle_state import BattleState, TemporaryStatus
from modules.battle_strategies import SafariTurnAction, DefaultBattleStrategy, BattleStrategyUtil
from modules.battle_strategies import TurnAction
from modules.context import context
from modules.items import Item, get_item_bag, PokeblockType
from modules.map import get_map_data_for_current_position
from modules.pokedex import get_pokedex
from modules.pokemon import Pokemon, get_type_by_name, StatusCondition, get_opponent
from modules.pokeblock_feeder import get_active_pokeblock_feeder_for_location
from modules.safari_strategy import (
    get_safari_strategy_action,
    is_watching_carefully,
    get_safari_balls_left,
    get_lowest_feel_any_pokeblock,
    get_lowest_feel_excluding_type,
    get_lowest_feel_pokeblock_by_type,
    get_baiting_state,
    PokeblockState,
    RSESafariStrategy,
)


class CatchStrategy(DefaultBattleStrategy):

    def __init__(self):
        super().__init__()
        self._current_catching_strategy_index = 0
        self._is_current_catching_strategy_baited = False
        self._number_of_balls_strategy = 0
        self._has_been_baited = False
        self._has_been_rocked = False
        self._pokeblock_state = None
        self._given_pokeblock = None

    def pokemon_can_battle(self, pokemon: Pokemon) -> bool:
        return not pokemon.is_egg and pokemon.current_hp > 0

    def should_flee_after_faint(self, battle_state: BattleState) -> bool:
        return False

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        ball_to_throw = self._get_best_poke_ball(battle_state)
        if ball_to_throw is None:
            context.message = "Player does not have any Poké Balls, cannot catch."
            return TurnAction.switch_to_manual()

        # The chance of a Pokémon being caught increases if it has a status condition (sleeping,
        # paralysed, poisoned, burned, frozen.) If possible, we will try to inflict a status
        # condition to increase catch odds.
        if battle_state.opponent.active_battler.status_permanent == StatusCondition.Healthy:
            catch_success_chance = BattleStrategyUtil(battle_state).calculate_catch_success_chance(
                battle_state, self._get_poke_ball_catch_rate_multiplier(battle_state, ball_to_throw)
            )

            # Only bother inflicting a status condition if the chance of the opponent being caught
            # in one turn is less than 50%, otherwise just throw balls and hope for the best.
            if catch_success_chance < 0.5:
                status_move = self._get_best_status_changing_move(battle_state)
                if status_move is not None:
                    return TurnAction.use_move(status_move)

        return TurnAction.use_item(ball_to_throw)

    def decide_turn_in_double_battle(self, battle_state: BattleState, battler_index: int) -> tuple["TurnAction", any]:
        return self.decide_turn(battle_state)

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        """
        Determines the next action in the Safari Zone based on the game.

        Parameters:
            battle_state (BattleState): The current battle state in Safari Zone.

        Returns:
            tuple[SafariTurnAction, any]: The next Safari action to perform and any additional context.
        """
        if context.rom.is_rse:
            return self._decide_turn_safari_rse(battle_state)
        elif context.rom.is_frlg:
            return self._decide_turn_safari_frlg(battle_state)
        return SafariTurnAction.switch_to_manual()

    def _decide_turn_safari_rse(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        """
        Handles the turn decision for RSE games.
        """
        if RSESafariStrategy.should_start_pokeblock_strategy(get_opponent()):
            if battle_state.current_turn == 0:
                feeder = get_active_pokeblock_feeder_for_location()
                if feeder:
                    flavor_str = feeder.pokeblock.type.value
                    pokeblock_index, pokeblock = get_lowest_feel_pokeblock_by_type(flavor_str)
                else:
                    pokeblock_index, pokeblock = get_lowest_feel_any_pokeblock()
                if pokeblock_index is None:
                    return SafariTurnAction.ThrowBall, None

                self._pokeblock_state = get_baiting_state(pokeblock)
                self._given_pokeblock = pokeblock.type.value

                return SafariTurnAction.Pokeblock, pokeblock_index

            if battle_state.current_turn == 1:
                if self._pokeblock_state == PokeblockState.IGNORED:
                    excluded_type = PokeblockType(self._given_pokeblock)
                    pokeblock_index, pokeblock = get_lowest_feel_excluding_type(excluded_type)
                    if pokeblock_index is None:
                        return SafariTurnAction.ThrowBall, None
                    return SafariTurnAction.Pokeblock, pokeblock_index

        return SafariTurnAction.ThrowBall, None

    def _decide_turn_safari_frlg(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        """
        Handles the turn decision for FRLG games based on the watching/rocked/baited status.
        """
        if self._is_new_strategy_required():
            if not self._has_been_baited:
                return self._start_new_baited_strategy()
            else:
                return self._start_new_continuing_baited_strategy()
        return self._continue_current_strategy()

    def _is_new_strategy_required(self) -> bool:
        """
        Checks if a new catching strategy should be initiated.
        """
        return is_watching_carefully() and not self._has_been_rocked

    def _start_new_baited_strategy(self) -> tuple["SafariTurnAction", any]:
        """
        Initiates a new baited catch strategy and returns the next action.
        """
        self._number_of_balls_strategy = get_safari_balls_left()
        self._has_been_baited = True

        action, rocked = self._execute_strategy_action()

        if rocked:
            self._has_been_rocked = rocked

        self._current_catching_strategy_index += 1

        return action, None

    def _start_new_continuing_baited_strategy(self) -> tuple["SafariTurnAction", any]:
        """
        Initiates a new baited catch strategy after first baited one and returns the next action.
        """
        self._current_catching_strategy_index = 0
        self._number_of_balls_strategy = get_safari_balls_left()
        self._is_current_catching_strategy_baited == True

        action, rocked = self._execute_strategy_action()

        if rocked:
            self._has_been_rocked = rocked
        self._current_catching_strategy_index += 1

        return action, None

    def _continue_current_strategy(self) -> tuple["SafariTurnAction", any]:
        """
        Continues the current catching strategy and returns the next action.
        """
        action, rocked = self._execute_strategy_action()

        if rocked:
            self._has_been_rocked = rocked
        self._current_catching_strategy_index += 1

        return action, None

    def _execute_strategy_action(self) -> tuple["SafariTurnAction", bool]:
        """
        Executes the catch strategy action based on the current strategy index, baited state, and remaining balls.
        """
        action, rocked = get_safari_strategy_action(
            get_opponent(),
            self._number_of_balls_strategy,
            self._current_catching_strategy_index,
            self._is_current_catching_strategy_baited,
        )
        return action, rocked

    def _get_best_status_changing_move(self, battle_state: BattleState) -> int | None:
        # A Pokémon under the influence of Taunt can only use damaging moves.
        if battle_state.own_side.active_battler.taunt_turns_remaining > 0:
            return None

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
