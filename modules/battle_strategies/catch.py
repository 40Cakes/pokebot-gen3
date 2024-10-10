from modules.battle_state import BattleState
from modules.battle_strategies import SafariTurnAction, DefaultBattleStrategy
from modules.battle_strategies import TurnAction
from modules.context import context
from modules.items import Item, get_item_bag, get_item_by_name
from modules.map import get_map_data_for_current_position
from modules.pokedex import get_pokedex
from modules.pokemon import (
    Pokemon,
    get_type_by_name,
    StatusCondition,
    get_party,
    get_party_alive,
    get_not_eggs_in_party,
)


class CatchStrategy(DefaultBattleStrategy):
    def __init__(self):
        super().__init__()
        self._first_pokemon_sent_index = self.get_first_valid_pokemon_index()
        self._revive_mode = context.config.battle.catch_revive_mode
        self._revive_item = context.config.battle.revive_item

    def pokemon_can_battle(self, pokemon: Pokemon) -> bool:
        return not pokemon.is_egg and pokemon.current_hp > 0

    def should_flee_after_faint(self, battle_state: BattleState) -> bool:
        return False

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        """Determines the next action depending on the mode and current battle state."""
        party = get_party()
        lead_pokemon_index = self._first_pokemon_sent_index
        lead_pokemon = party[lead_pokemon_index]

        # If only one pokemon in party, we don't switch to manual
        # Switching only if several available Pokemons but only one left alive
        if get_party_alive() == 1 and get_not_eggs_in_party() > 1:
            context.message = "Last pokemon alive, switching to manual mode."
            return TurnAction.switch_to_manual()

        if lead_pokemon.current_hp == 0:
            match self._revive_mode:
                case "always_revive_lead":
                    return self.revive_fainted_lead(lead_pokemon_index)

                case "no_revive":
                    self.handle_catch_logic(battle_state)

                case _:
                    # Unrecognized revive mode. Switching to manual mode.
                    return TurnAction.switch_to_manual()
        return self.handle_catch_logic(battle_state)

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

    def choose_new_lead_after_faint(self, battle_state: BattleState) -> int:
        """Selects the first non egg Pokemon to become the new lead."""
        party = get_party()

        for index, pokemon in enumerate(party):
            if not pokemon.is_egg and pokemon.current_hp > 0:  # Ignore eggs and fainted Pokémon
                return index

    def get_first_valid_pokemon_index(self) -> int | None:
        """Returns the index of the first valid Pokémon that is not an egg."""
        party = get_party()
        for index, pokemon in enumerate(party):
            if not pokemon.is_egg and not pokemon.current_hp == 0:
                return index
        return None

    def get_first_valid_pokemon(self, party: list) -> Pokemon | None:
        """Returns the first valid Pokémon that is not an egg."""
        for pokemon in party:
            if not pokemon.is_egg:
                return pokemon

    def revive_fainted_lead(self, fainted_lead):
        """
        Revives the fainted lead Pokémon using Max Revive or Revive, based on the setting.

        `revive_item` can be one of the following:
        - "revive": Use Revive if available, otherwise do nothing.
        - "max_revive": Use Max Revive if available, otherwise do nothing.
        - "both": Prefer Max Revive if available, otherwise use Revive.

        :param fainted_lead: The Pokémon to revive.
        """

        revive_preference = self._revive_item

        max_revive_count = get_item_bag().quantity_of(get_item_by_name("Max Revive"))
        revive_count = get_item_bag().quantity_of(get_item_by_name("Revive"))

        match revive_preference:
            case "max_revive":
                if max_revive_count > 0:
                    return TurnAction.use_item_on(get_item_by_name("Max Revive"), fainted_lead)

            case "revive":
                if revive_count > 0:
                    return TurnAction.use_item_on(get_item_by_name("Revive"), fainted_lead)

            case "both":
                if max_revive_count > 0:
                    return TurnAction.use_item_on(get_item_by_name("Max Revive"), fainted_lead)
                elif revive_count > 0:
                    return TurnAction.use_item_on(get_item_by_name("Revive"), fainted_lead)

        context.message = "Player doesn't have any revive items left."
        return TurnAction.switch_to_manual()

    def handle_catch_logic(self, battle_state: BattleState):
        """Handles the default catch logic such as using a Poké Ball or status move."""
        ball_to_throw = self._get_best_poke_ball(battle_state)
        if ball_to_throw is None:
            context.message = "Player does not have any Poké Balls, cannot catch."
            return TurnAction.switch_to_manual()

        # If the opponent is healthy, attempt to apply a status move first
        if battle_state.opponent.active_battler.status_permanent == StatusCondition.Healthy:
            status_move = self._get_best_status_changing_move(battle_state)
            if status_move is not None:
                return TurnAction.use_move(status_move)

        # Otherwise, throw the best available Poké Ball
        return TurnAction.use_item(ball_to_throw)
