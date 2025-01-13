from typing import Optional

from modules.battle_state import BattleState, BattlePokemon, get_battle_state
from modules.context import context
from modules.modes._interface import BotModeError
from modules.pokemon import Pokemon, Move, LearnedMove
from modules.pokemon_party import get_party
from ._interface import BattleStrategy, TurnAction, SafariTurnAction
from ._util import BattleStrategyUtil


class DefaultBattleStrategy(BattleStrategy):
    def __init__(self):
        self._first_non_fainted_party_index_before_battle = get_party().first_non_fainted.index

    def party_can_battle(self) -> bool:
        return any(self.pokemon_can_battle(pokemon) for pokemon in get_party())

    def pokemon_can_battle(self, pokemon: Pokemon) -> bool:
        if pokemon.is_egg or not self._pokemon_has_enough_hp(pokemon):
            return False

        return any(self._move_is_usable(move) for move in pokemon.moves)

    def which_move_should_be_replaced(self, pokemon: Pokemon, new_move: Move) -> int:
        if context.config.battle.new_move == "stop":
            context.message = f"{pokemon.name} is attempting to learn {new_move.name}. Switching to manual mode."
            context.set_manual_mode()
            return 4

        if context.config.battle.new_move == "cancel":
            return 4

        # Do not learn move if new move is banned.
        if new_move.name in context.config.battle.banned_moves:
            context.message = f"{new_move.name} is on the block list, so {pokemon.name} will skip learning it."
            return 4

        move_choices = [*[move.move for move in pokemon.moves], new_move]

        # Get the effective power of each move
        move_powers = []
        for move in move_choices:
            if move.name in context.config.battle.banned_moves:
                move_powers.append(0)
                continue

            # Never attempt to replace HMs because that won't work.
            if move.tm_hm is not None and move.tm_hm.name.startswith("HM"):
                move_powers.append(9999)
                continue

            match move.type.kind:
                case "Physical":
                    stat_multiplier = pokemon.stats.attack
                case "Special":
                    stat_multiplier = pokemon.stats.special_attack
                case _:
                    stat_multiplier = 1

            same_type_attack_bonus = 1
            if move.type in pokemon.species.types:
                same_type_attack_bonus = 1.5

            move_powers.append(move.base_power * stat_multiplier * same_type_attack_bonus)

        # Find the weakest move of the bunch
        weakest_move = move_powers.index(min(move_powers))

        # Try and aim for good coverage: It's generally better to have a wide array of move types
        # than 4 moves of the same type.
        redundant_type_moves = []
        existing_move_types = {}
        for move_index in range(len(move_choices)):
            move = move_choices[move_index]
            if move.base_power == 0:
                continue
            if move.type not in existing_move_types:
                existing_move_types[move.type] = move_index
            else:
                if not redundant_type_moves:
                    redundant_type_moves.append(existing_move_types[move.type])
                redundant_type_moves.append(move_index)

        if move_powers[weakest_move] > 0 and redundant_type_moves:
            redundant_move_powers = [move_powers[move_index] for move_index in redundant_type_moves]
            redundant_move = redundant_type_moves[redundant_move_powers.index(min(redundant_move_powers))]
            context.message = f"Replacing move {move_choices[redundant_move].name} because a stronger move of that type is already known, in order to maximise coverage."
            return redundant_move

        context.message = f"Replacing move {move_choices[weakest_move].name} because it is the weakest one (calculated power: {move_powers[weakest_move]})"

        return weakest_move

    def should_allow_evolution(self, pokemon: Pokemon, party_index: int) -> bool:
        if context.bot_mode_instance is None:
            return True
        else:
            return (
                context.bot_mode_instance.on_pokemon_evolving_after_battle(pokemon, party_index)
                and not context.config.battle.stop_evolution
            )

    def should_flee_after_faint(self, battle_state: BattleState) -> bool:
        if context.config.battle.faint_action == "stop":
            context.message = "Active Pokémon fainted. Switching to manual mode."
            context.set_manual_mode()
        elif context.config.battle.faint_action == "flee":
            if battle_state.is_trainer_battle:
                context.message = "Active Pokémon fainted. `faint_action` is set to `flee`, but this is a trainer battle. Switching to manual mode."
                context.set_manual_mode()
            return True
        elif not self.party_can_battle():
            return True
        else:
            return False

    def choose_new_lead_after_faint(self, battle_state: BattleState) -> int:
        new_lead: int | None = None
        new_lead_current_hp: int = 0
        party = get_party()
        for index in range(len(party)):
            pokemon = party[index]
            if battle_state.is_double_battle and (
                (
                    battle_state.own_side.left_battler is not None
                    and battle_state.own_side.left_battler.party_index == index
                )
                or (
                    battle_state.own_side.right_battler is not None
                    and battle_state.own_side.right_battler.party_index == index
                )
            ):
                continue
            if not pokemon.is_egg and pokemon.current_hp > 0 and pokemon.current_hp > new_lead_current_hp:
                new_lead = index
                new_lead_current_hp = pokemon.current_hp
        return new_lead

    def choose_new_lead_after_battle(self) -> int | None:
        party = get_party()
        if not self.pokemon_can_battle(party[self._first_non_fainted_party_index_before_battle]):
            util = BattleStrategyUtil(get_battle_state())
            return util.select_rotation_target()

        return None

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", Optional[any]]:
        """
        Decides the action to take for the current turn based on the battle state.
        """
        util = BattleStrategyUtil(battle_state)

        if not util.pokemon_has_enough_hp(battle_state.own_side.active_battler):
            return self._handle_lead_cannot_battle(battle_state, util, reason="HP below threshold")

        strongest_move = util.get_strongest_move_against(
            battle_state.own_side.active_battler, battle_state.opponent.active_battler
        )
        if strongest_move is not None:
            return TurnAction.use_move(strongest_move)

        return self._handle_lead_cannot_battle(battle_state, util, reason="No damaging moves available")

    def decide_turn_in_double_battle(self, battle_state: BattleState, battler_index: int) -> tuple["TurnAction", any]:
        util = BattleStrategyUtil(battle_state)
        battler = battle_state.own_side.left_battler if battler_index == 0 else battle_state.own_side.right_battler
        partner = battle_state.own_side.right_battler if battler_index == 0 else battle_state.own_side.left_battler
        pokemon = get_party()[battler.party_index]
        partner_pokemon = get_party()[partner.party_index] if partner is not None else None

        if not util.pokemon_has_enough_hp(pokemon):
            if partner_pokemon is None or not util.pokemon_has_enough_hp(partner_pokemon):
                return self._handle_lead_cannot_battle(battle_state, util)

        left_opponent = battle_state.opponent.left_battler
        right_opponent = battle_state.opponent.right_battler

        def first_available_move():
            for index, learned_move in enumerate(battler.moves):
                if (
                    learned_move is not None
                    and learned_move.pp > 0
                    and battler.disabled_move is None
                    or battler.disabled_move is not learned_move.move
                ):
                    return index
            return 0

        if left_opponent is not None:
            strongest_move = util.get_strongest_move_against(battler, left_opponent)
            if strongest_move is not None:
                return TurnAction.use_move_against_left_side_opponent(strongest_move)
            else:
                return TurnAction.use_move_against_left_side_opponent(first_available_move())

        if right_opponent is not None:
            strongest_move = util.get_strongest_move_against(battler, right_opponent)
            if strongest_move is not None:
                return TurnAction.use_move_against_right_side_opponent(strongest_move)
            else:
                return TurnAction.use_move_against_right_side_opponent(first_available_move())

        return self._handle_lead_cannot_battle(battle_state, util, reason="No damaging moves available")

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        return SafariTurnAction.switch_to_manual()

    def _move_is_usable(self, move: LearnedMove):
        return (
            move is not None
            and move.move.base_power > 0
            and move.pp > 0
            and move.move.name not in context.config.battle.banned_moves
        )

    def _pokemon_has_enough_hp(self, pokemon: Pokemon | BattlePokemon):
        return pokemon.current_hp_percentage > context.config.battle.hp_threshold

    def _handle_lead_cannot_battle(
        self, battle_state: BattleState, util: BattleStrategyUtil, reason: str
    ) -> tuple["TurnAction", Optional[any]]:
        """
        Handles situations where the lead Pokémon cannot battle due to low HP or lack of damaging moves.
        """
        lead_action = context.config.battle.lead_cannot_battle_action

        if lead_action == "flee":
            return self._handle_flee(battle_state, util, reason)

        if lead_action == "rotate":
            return self._handle_rotate(battle_state, util)

        raise BotModeError(f"Your Pokémon cannot battle due to {reason}, switching to manual mode...")

    def _handle_flee(
        self, battle_state: BattleState, util: BattleStrategyUtil, reason: str
    ) -> tuple["TurnAction", Optional[any]]:
        """
        Handles the flee action when the lead Pokémon cannot battle.
        """
        if battle_state.is_trainer_battle:
            raise BotModeError(
                f"Your Pokémon cannot battle due to {reason}, and 'flee' is not allowed in a trainer battle."
            )

        best_escape_method = util.get_best_escape_method()
        if best_escape_method is not None:
            return best_escape_method

        raise BotModeError(f"Your Pokémon cannot battle due to {reason}, and escape is not possible.")

    def _handle_rotate(self, battle_state: BattleState, util: BattleStrategyUtil) -> tuple["TurnAction", Optional[any]]:
        """
        Handles the rotate action when the lead Pokémon cannot battle.
        """
        if len(util.get_potential_rotation_targets(battle_state)) > 0 and util.can_switch():
            return TurnAction.rotate_lead(util.select_rotation_target(battle_state))

        raise BotModeError(
            "Your Pokémon cannot battle, 'lead_cannot_battle_action' is set to 'rotate', but no eligible Pokémon are available for switching."
        )
