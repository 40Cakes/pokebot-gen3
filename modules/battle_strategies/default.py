from modules.battle_state import BattleState, BattlePokemon
from modules.context import context
from modules.pokemon import get_party, Pokemon, Move, LearnedMove, StatusCondition
from ._interface import BattleStrategy, TurnAction, SafariTurnAction


class DefaultBattleStrategy(BattleStrategy):
    def battle_can_happen(self, check_lead_only: bool = False) -> bool:
        party = [get_party()[0]] if check_lead_only else get_party()
        return any(self.pokemon_can_battle(mon) for mon in party)

    def pokemon_can_battle(self, pokemon: Pokemon):
        if pokemon.is_egg or not self._pokemon_has_enough_hp(pokemon):
            return False

        return any(self._move_is_usable(move) for move in pokemon.moves)

    def which_move_should_be_replaced(self, pokemon: Pokemon, new_move: Move) -> int:
        if context.config.battle.new_move == "stop":
            context.message = f"{pokemon.name} is attempting to learn {new_move.name}."
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
        return battle_state.is_trainer_battle and context.config.battle.faint_action == "flee"

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

        if context.config.battle.lead_mon_balance_levels:
            rotation_candidates = self._get_usable_party_indices()
            weakest_party_index = 0
            for index in rotation_candidates:
                if party[index].level < party[weakest_party_index].level:
                    weakest_party_index = index

            if weakest_party_index != 0:
                return weakest_party_index
            else:
                return None

        if not self.pokemon_can_battle(party[0]):
            return self._select_rotation_target()

        return None

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        if not self._pokemon_has_enough_hp(get_party()[battle_state.own_side.active_battler.party_index]):
            if context.config.battle.lead_cannot_battle_action == "flee" and not battle_state.is_trainer_battle:
                return TurnAction.run_away()
            elif (
                context.config.battle.lead_cannot_battle_action == "rotate"
                and len(self._get_usable_party_indices(battle_state)) > 0
            ):
                return TurnAction.rotate_lead(self._select_rotation_target(battle_state))
            else:
                context.message = "Leading Pokémon's HP fell below the minimum threshold."
                return TurnAction.switch_to_manual()

        return TurnAction.use_move(
            self._get_strongest_move_against(battle_state.own_side.active_battler, battle_state.opponent.active_battler)
        )

    def decide_turn_in_double_battle(self, battle_state: BattleState, battler_index: int) -> tuple["TurnAction", any]:
        battler = battle_state.own_side.left_battler if battler_index == 0 else battle_state.own_side.right_battler
        partner = battle_state.own_side.right_battler if battler_index == 0 else battle_state.own_side.left_battler
        pokemon = get_party()[battler.party_index]
        partner_pokemon = get_party()[partner.party_index] if partner is not None else None

        if not self._pokemon_has_enough_hp(pokemon):
            if partner_pokemon is None or not self._pokemon_has_enough_hp(partner_pokemon):
                if context.config.battle.lead_cannot_battle_action == "flee" and not battle_state.is_trainer_battle:
                    return TurnAction.run_away()
                elif (
                    context.config.battle.lead_cannot_battle_action == "rotate"
                    and len(self._get_usable_party_indices(battle_state)) > 0
                ):
                    return TurnAction.rotate_lead(self._select_rotation_target(battle_state))
                else:
                    context.message = "Both battling Pokémon's HP fell below the minimum threshold."
                    return TurnAction.switch_to_manual()

        if battle_state.opponent.left_battler is not None:
            opponent = battle_state.opponent.left_battler
            return TurnAction.use_move_against_left_side_opponent(self._get_strongest_move_against(battler, opponent))
        else:
            opponent = battle_state.opponent.right_battler
            return TurnAction.use_move_against_right_side_opponent(self._get_strongest_move_against(battler, opponent))

    def decide_turn_in_safari_zone(self, battle_state: BattleState) -> tuple["SafariTurnAction", any]:
        return SafariTurnAction.switch_to_manual()

    def _pokemon_has_enough_hp(self, pokemon: Pokemon):
        return pokemon.current_hp / pokemon.stats.hp > context.config.battle.hp_threshold / 100

    def _get_usable_party_indices(self, battle_state: BattleState | None = None) -> list[int]:
        active_party_indices = []
        if battle_state is not None:
            if battle_state.own_side.left_battler is not None:
                active_party_indices.append(battle_state.own_side.left_battler.party_index)
            if battle_state.own_side.right_battler is not None:
                active_party_indices.append(battle_state.own_side.right_battler.party_index)

        party = get_party()
        usable_pokemon = []
        for index in range(len(party)):
            pokemon = party[index]
            if self.pokemon_can_battle(pokemon) and index not in active_party_indices:
                usable_pokemon.append(index)

        return usable_pokemon

    def _select_rotation_target(self, battle_state: BattleState | None = None) -> int | None:
        indices = self._get_usable_party_indices(battle_state)
        if len(indices) == 0:
            return None

        party = get_party()
        values = []
        for index in indices:
            pokemon = party[index]
            if context.config.battle.switch_strategy == "lowest_level":
                value = 100 - pokemon.level
            else:
                value = pokemon.current_hp
                if pokemon.status_condition in (StatusCondition.Sleep, StatusCondition.Freeze):
                    value *= 0.25
                elif pokemon.status_condition == StatusCondition.BadPoison:
                    value *= 0.5
                elif pokemon.status_condition in (
                    StatusCondition.BadPoison,
                    StatusCondition.Poison,
                    StatusCondition.Burn,
                ):
                    value *= 0.65
                elif pokemon.status_condition == StatusCondition.Paralysis:
                    value *= 0.8

            values.append(value)

        best_value = max(values)
        index = indices[values.index(best_value)]

        return index

    def _move_is_usable(self, move: LearnedMove):
        return (
            move is not None
            and move.move.base_power > 0
            and move.pp > 0
            and move.move.name not in context.config.battle.banned_moves
        )

    def _get_strongest_move_against(self, pokemon: BattlePokemon, opponent: BattlePokemon):
        move_strengths = []
        for learned_move in pokemon.moves:
            move = learned_move.move
            if move.base_power == 0:
                move_strengths.append(0)
                continue
            elif learned_move.pp == 0:
                move_strengths.append(-1)
                continue

            stat_modifier = pokemon.stats.attack if move.type == "Physical" else pokemon.stats.special_attack
            same_type_bonus = 1.5 if move.type in pokemon.types else 1
            type_modifier = 1
            for type in opponent.types:
                type_modifier *= move.type.get_effectiveness_against(type)

            move_strengths.append(move.base_power * stat_modifier * same_type_bonus * type_modifier)

        strongest_move = move_strengths.index(max(move_strengths))
        return strongest_move