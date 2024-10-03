from typing import TYPE_CHECKING

from modules.battle_strategies import BattleStrategy, TurnAction, BattleStrategyUtil
from modules.pokemon import get_party, StatusCondition

if TYPE_CHECKING:
    from modules.battle_state import BattleState, BattlePokemon, BattleType
    from modules.pokemon import Pokemon, Move


def _get_weakest_move_against(battle_state: "BattleState", pokemon: "BattlePokemon", opponent: "BattlePokemon"):
    util = BattleStrategyUtil(battle_state)

    move_strengths = []
    for learned_move in pokemon.moves:
        move = learned_move.move

        # Never use moves that ran out of PP, unless _all_ moves are out of PPs in
        # which case we're using Struggle either way.
        if learned_move.pp == 0 or pokemon.disabled_move is move:
            move_strengths.append(99999)
            continue

        # Calculate effective power of the move.
        move_power = util.calculate_move_damage_range(move, pokemon, opponent).max

        # Doing nothing is always the best idea.
        if move.effect == "SPLASH":
            move_power = -1

        # Moves that might end the battle.
        if move.effect == "ROAR" and BattleType.Trainer not in battle_state.type:
            move_power = 99998

        # Moves that give an invulnerable turn (Fly, Dig, ...), as we WANT to be damaged.
        if move.effect == "SEMI_INVULNERABLE":
            move_power *= 2

        # Moves that hit multiple times
        if move.effect == "DOUBLE_HIT":
            move_power *= 2
        if move.effect == "MULTI_HIT":
            move_power *= 3
        if move.effect == "TRIPLE_KICK":
            move_power *= 5

        # Moves that would restore our HP.
        if move.effect == "ABSORB":
            move_power *= 1.5

        if move.effect in ("SOFTBOILED", "MOONLIGHT", "MORNING_SUN", "SYNTHESIS", "RECOVER"):
            move_power = 1500
        elif move.effect in "REST":
            # Rest is the preferable healing move because it at least puts us to sleep.
            move_power = 1490

        # Moves that would remove damaging status effects.
        if pokemon.status_permanent is not StatusCondition.Healthy and move.effect == "HEAL_BELL":
            move_power = 1470
        elif (
            pokemon.status_permanent
            in (StatusCondition.Poison, StatusCondition.BadPoison, StatusCondition.Burn, StatusCondition.Paralysis)
            and move.effect == "REFRESH"
        ):
            move_power = 1470

        # Moves that would decrease the opponent's accuracy or our own evasion.
        if move.effect in ("ACCURACY_DOWN", "ACCURACY_DOWN_HIT", "EVASION_UP"):
            move_power += 25

        # Moves that would increase our own Defence.
        if move.effect in ("DEFENSE_CURL", "DEFENSE_UP", "DEFENSE_UP_2", "DEFENSE_UP_HIT", "SPECIES_DEFENSE_UP_2"):
            move_power += 15

        # Moves that would decrease the opponent's attack power.
        if move.effect in ("ATTACK_DOWN", "ATTACK_DOWN_2", "ATTACK_DOWN_HIT", "SPECIAL_ATTACK_DOWN_HIT"):
            move_power += 15

        # Add bonus for moves that would make US faint
        if move.effect == "EXPLOSION":
            move_power *= 0.85

        # Add bonus for moves that inflict recoil damage
        if move.effect == "DOUBLE_EDGE":
            move_power *= 1 - 0.33
        if move.effect == "RECOIL":
            move_power *= 1 - 0.25

        # One-hit KO moves should not be risked, unless the opponent's level is higher than ours
        # (in which case OHKO moves always fail)
        if move.effect == "OHKO" and pokemon.level >= opponent.level:
            move_power = 99997

        # Moves might might inflict a status condition
        if opponent.status_permanent is StatusCondition.Healthy and move.effect in (
            "TRI_ATTACK",
            "SECRET_POWER",
        ):
            move_power += 50

        # Moves that might poison the target
        if opponent.status_permanent is StatusCondition.Healthy and move.effect in (
            "POISON",
            "POISON_FANG",
            "POISON_HIT",
            "POISON_TAIL",
            "TOXIC",
            "TWINEEDLE",
        ):
            move_power += 50

        # Moves that might burn the target
        if opponent.status_permanent is StatusCondition.Healthy and move.effect in (
            "BURN_HIT",
            "BLAZE_KICK",
            "THAW_HIT",
            "TRI_ATTACK",
            "WILL_O_WISP",
        ):
            move_power += 50

        # Moves that might inflict paralysis
        if opponent.status_permanent is StatusCondition.Healthy and move.effect in (
            "PARALYZE",
            "PARALYZE_HIT",
            "THUNDER",
        ):
            move_power += 20

        # Moves that might freeze the opponent
        if opponent.status_permanent is StatusCondition.Healthy and move.effect == "FREEZE_HIT":
            move_power += 45

        # Moves that might make the opponent flinch
        if move.effect in ("FLINCH_MINIMIZE_HIT", "FLINCH_HIT", "TWISTER"):
            move_power += 5

        # Bonus for moves that can only hit in certain conditions
        if move.effect == "SNORE" and pokemon.status_permanent is not StatusCondition.Sleep:
            move_power = 0

        if move.effect == "FAKE_OUT" and battle_state.current_turn > 1:
            move_power = 0

        move_strengths.append(move_power)

    weakest_move = move_strengths.index(min(move_strengths))
    return weakest_move


class LoseOnPurposeBattleStrategy(BattleStrategy):
    def party_can_battle(self) -> bool:
        return True

    def pokemon_can_battle(self, pokemon: "Pokemon") -> bool:
        return not pokemon.is_egg and pokemon.current_hp > 0

    def which_move_should_be_replaced(self, pokemon: "Pokemon", new_move: "Move") -> int:
        return 4

    def should_allow_evolution(self, pokemon: "Pokemon", party_index: int) -> bool:
        return False

    def should_flee_after_faint(self, battle_state: "BattleState") -> bool:
        return False

    def choose_new_lead_after_battle(self) -> int | None:
        return None

    def choose_new_lead_after_faint(self, battle_state: "BattleState") -> int:
        party = get_party()
        for index in range(len(party)):
            if self.pokemon_can_battle(party[index]):
                return index

    def decide_turn(self, battle_state: "BattleState") -> tuple["TurnAction", any]:
        return TurnAction.use_move(
            _get_weakest_move_against(
                battle_state, battle_state.own_side.active_battler, battle_state.opponent.active_battler
            )
        )

    def decide_turn_in_double_battle(self, battle_state: "BattleState", battler_index: int) -> tuple["TurnAction", any]:
        battler = battle_state.own_side.left_battler if battler_index == 0 else battle_state.own_side.right_battler

        if battle_state.opponent.left_battler is not None:
            opponent = battle_state.opponent.left_battler
            return TurnAction.use_move_against_left_side_opponent(
                _get_weakest_move_against(battle_state, battler, opponent)
            )
        else:
            opponent = battle_state.opponent.right_battler
            return TurnAction.use_move_against_right_side_opponent(
                _get_weakest_move_against(battle_state, battler, opponent)
            )
