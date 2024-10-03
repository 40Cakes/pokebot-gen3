from operator import truediv
from typing import TYPE_CHECKING

from modules.battle_state import Weather, TemporaryStatus, BattleType
from modules.battle_strategies import TurnAction
from modules.context import context
from modules.items import ItemHoldEffect, get_item_bag, get_item_by_name
from modules.memory import get_event_flag, read_symbol
from modules.pokemon import StatusCondition, get_type_by_name, get_ability_by_name

if TYPE_CHECKING:
    from modules.battle_state import BattlePokemon, BattleState
    from modules.pokemon import Move, Type


class DamageRange:
    min: int
    max: int

    def __init__(self, min_damage: int, max_damage: int | None = None):
        self.min = min_damage
        self.max = max_damage if max_damage is not None else min_damage


def _get_move_type_and_power(move: "Move", pokemon: "BattlePokemon") -> tuple["Type", int]:
    if move.effect == "HIDDEN_POWER":
        return pokemon.hidden_power_type, pokemon.hidden_power_damage
    else:
        return move.type, move.base_power


def _calculate_modified_stat(original_stat: int, modifier_level: int) -> int:
    return original_stat * (10 + max(0, modifier_level) * 5) // (10 + abs(min(0, modifier_level)) * 5)


def _percentage(value: int, percent: int) -> int:
    return (percent * value) // 100


class BattleStrategyUtil:
    def __init__(self, battle_state: "BattleState"):
        self._battle_state = battle_state

    def get_escape_chance(self) -> float:
        """
        Calculates the likelihood of an attempt to flee the battle will succeed.

        This only counts for the 'Run Away' battle option, not for other ways of escaping
        (using a Poké Doll, using Teleport, ...)

        :return: A number between 0 and 1, with 0 meaning that escaping is impossible.
        """

        # Cannot run from trainer battles or R/S/E's first battle (Birch will complain)
        if BattleType.Trainer in self._battle_state.type or BattleType.FirstBattle in self._battle_state.type:
            return 0

        # Smoke Ball check
        battler = self._battle_state.own_side.active_battler
        if battler.held_item is not None and battler.held_item.hold_effect is ItemHoldEffect.CanAlwaysRunAway:
            return 1

        if battler.ability.name == "Run Away":
            return 1

        if (
            TemporaryStatus.Rooted in battler.status_temporary
            or TemporaryStatus.Wrapped in battler.status_temporary
            or TemporaryStatus.EscapePrevention in battler.status_temporary
        ):
            return 0

        opponent = self._battle_state.opponent.active_battler
        if self._battle_state.opponent.has_ability(get_ability_by_name("Shadow Tag")):
            return 0

        if (
            self._battle_state.opponent.has_ability(get_ability_by_name("Arena Trap"))
            and get_type_by_name("Flying") not in battler.types
            and battler.ability.name != "Levitate"
        ):
            return 0

        if opponent.ability.name == "Magnet Pull" and get_type_by_name("Steel") in battler.types:
            return 0

        if opponent.stats.speed < battler.stats.speed:
            return 1

        if context.rom.is_rs:
            escape_attempts = context.emulator.read_bytes(0x0201_6078, length=1)[0]
        else:
            escape_attempts = read_symbol("gBattleStruct", offset=0x4C, size=1)[0]
        escape_chance = ((battler.stats.speed * 128) // opponent.stats.speed + (escape_attempts * 30)) % 256
        return escape_chance / 255

    def get_best_escape_method(self) -> tuple[TurnAction, any] | None:
        """
        :return: A turn action for escaping, or None if escaping is impossible.
        """

        escape_chance = self.get_escape_chance()
        if escape_chance == 1:
            return TurnAction.run_away()

        # Use Poké Doll or Fluffy Tail if available
        if escape_chance < 0.9:
            item_bag = get_item_bag()
            if item_bag.quantity_of(get_item_by_name("Poké Doll")) > 0:
                return TurnAction.use_item(get_item_by_name("Poké Doll"))
            elif item_bag.quantity_of(get_item_by_name("Fluffy Tail")) > 0:
                return TurnAction.use_item(get_item_by_name("Fluffy Tail"))

        # If escape odds are low enough, try escaping using a move
        battler = self._battle_state.own_side.active_battler
        opponent = self._battle_state.opponent.active_battler
        if 0 < escape_chance < 0.5:
            # Prefer Teleport as that might be quicker
            for index in range(len(battler.moves)):
                if battler.moves[index].move.name == "Teleport":
                    return TurnAction.use_move(index)

            # Whirlwind and Roar
            if opponent.ability.name != "Suction Cups" and TemporaryStatus.Rooted not in opponent.status_temporary:
                for index in range(len(battler.moves)):
                    if battler.moves[index].move.effect == "ROAR":
                        return TurnAction.use_move(index)

        # Only try to escape if it's not impossible
        if escape_chance > 0:
            return TurnAction.run_away()

        return None

    def can_switch(self) -> bool:
        """
        :return: True if switching Pokémon is allowed at this point, False if it is impossible.
        """
        battler = self._battle_state.own_side.active_battler
        if (
            TemporaryStatus.Wrapped in battler.status_temporary
            or TemporaryStatus.EscapePrevention in battler.status_temporary
            or TemporaryStatus.Rooted in battler.status_temporary
        ):
            return False

        if self._battle_state.opponent.has_ability(get_ability_by_name("Shadow Tag")):
            return False

        if (
            self._battle_state.opponent.has_ability(get_ability_by_name("Arena Trap"))
            and get_type_by_name("Flying") not in battler.types
            and battler.ability.name != "Levitate"
        ):
            return False

        if (
            self._battle_state.opponent.has_ability(get_ability_by_name("Magnet Pull"))
            and get_type_by_name("Steel") in battler.types
        ):
            return False

        return True

    def calculate_move_damage_range(
        self, move: "Move", attacker: "BattlePokemon", defender: "BattlePokemon", is_critical_hit: bool = False
    ) -> DamageRange:
        # todo: Bide, Counter, Endeavor, Mirror Coat

        damage = self._calculate_base_move_damage(move, attacker, defender, is_critical_hit)

        move_type, move_power = _get_move_type_and_power(move, attacker)

        if defender.ability.name == "Levitate" and move_type.name == "Ground":
            damage = 0

        if defender.ability.name == "Wonder Guard":
            super_effective = False
            for defender_type in defender.types:
                if move_type.get_effectiveness_against(defender_type) > 1:
                    super_effective = True
                    break
            if not super_effective:
                damage = 0

        if defender.ability.name == "Soundproof" and move.is_sound_move:
            damage = 0

        if defender.ability.name == "Volt Absorb" and move_type.name == "Electric":
            damage = 0

        if defender.ability.name == "Water Absorb" and move_type.name == "Water":
            damage = 0

        if defender.ability.name == "Flash Fire" and move_type.name == "Fire":
            damage = 0

        if damage == 0:
            return DamageRange(0)

        # Same-type Attack Bonus
        if move_type in attacker.types:
            damage = _percentage(damage, 150)

        # Type effectiveness
        for defender_type in defender.types:
            damage = _percentage(damage, int(100 * move_type.get_effectiveness_against(defender_type)))

        if move.name == "Dragon Rage":
            return DamageRange(40)

        if move.name == "Sonic Boom":
            return DamageRange(20)

        if move.name == "Super Fang":
            return DamageRange(max(1, defender.current_hp // 2))

        if move.name in ("Night Shade", "Seismic Toss"):
            return DamageRange(attacker.level)

        if move.name == "Psy Wave":
            return DamageRange(attacker.level, _percentage(attacker.level, 150))

        if is_critical_hit:
            damage *= 2

        if TemporaryStatus.ChargedUp in attacker.status_temporary and move_type.name == "Electric":
            damage *= 2

        # todo: Helping Hand

        return DamageRange(max(1, _percentage(damage, 85)), damage)

    def get_strongest_move_against(self, pokemon: "BattlePokemon", opponent: "BattlePokemon"):
        move_strengths = []
        for learned_move in pokemon.moves:
            move = learned_move.move
            if learned_move.pp == 0 or pokemon.disabled_move is move:
                move_strengths.append(-1)
            else:
                move_strengths.append(self.calculate_move_damage_range(move, pokemon, opponent).max)

        strongest_move = move_strengths.index(max(move_strengths))

        return strongest_move

    def _calculate_base_move_damage(
        self, move: "Move", attacker: "BattlePokemon", defender: "BattlePokemon", is_critical_hit: bool = False
    ):
        # It is possible for the player to attack themselves (in double battles), so these
        # two things are not mutually exclusive and thus need to be checked separately.
        if attacker in self._battle_state.own_side:
            attacker_side = self._battle_state.own_side
            attacker_is_player = True
            attacker_partner = self._battle_state.own_side.partner_for(attacker)
        else:
            attacker_side = self._battle_state.opponent
            attacker_is_player = False
            attacker_partner = self._battle_state.opponent.partner_for(attacker)

        if defender in self._battle_state.own_side:
            defender_side = self._battle_state.own_side
            defender_is_player = True
            defender_partner = self._battle_state.own_side.partner_for(defender)
        else:
            defender_side = self._battle_state.opponent
            defender_is_player = False
            defender_partner = self._battle_state.opponent.partner_for(defender)

        move_type, move_power = _get_move_type_and_power(move, attacker)

        if move_power == 0:
            return 0

        attack = attacker.stats.attack
        defence = defender.stats.defence
        special_attack = attacker.stats.special_attack
        special_defence = defender.stats.special_defence

        # There's something going on with Enigma Berries in the game code which I can't
        # be bothered to figure out. Enigma Berries aren't supported.

        if attacker.ability.name in ("Pure Power", "Huge Power"):
            attack *= 2

        # Badge Boosts
        if get_event_flag("BADGE01_GET") and attacker_is_player:
            attack = _percentage(attack, 110)
        if get_event_flag("BADGE05_GET") and defender_is_player:
            defence = _percentage(defence, 110)
        if get_event_flag("BADGE07_GET") and attacker_is_player:
            special_attack = _percentage(special_attack, 110)
        if get_event_flag("BADGE08_GET") and defender_is_player:
            special_defence = _percentage(special_defence, 110)

        # Held Item effects
        if attacker.held_item is not None:
            item = attacker.held_item
            if (
                item.hold_effect.value.endswith("_power")
                and item.hold_effect.value[0:-6].lower() == move_type.name.lower()
            ):
                if move_type.is_physical:
                    attack = _percentage(attack, 100 + item.parameter)
                else:
                    special_attack = _percentage(special_attack, 100 + item.parameter)

            if item.hold_effect is ItemHoldEffect.ChoiceBand:
                attack = _percentage(attack, 150)
            if item.hold_effect is ItemHoldEffect.SoulDew and attacker.species.name in ("Latias", "Latios"):
                special_attack = _percentage(special_attack, 150)
            if item.hold_effect is ItemHoldEffect.DeepSeaTooth and attacker.species.name == "Clamperl":
                special_attack *= 2
            if item.hold_effect is ItemHoldEffect.LightBall and attacker.species.name == "Pikachu":
                special_attack *= 2
            if item.hold_effect is ItemHoldEffect.ThickClub and attacker.species.name in ("Cubone", "Marowak"):
                attack *= 2

        if defender.held_item is not None:
            item = defender.held_item
            if item.hold_effect is ItemHoldEffect.SoulDew and defender.species.name in ("Latias", "Latios"):
                special_defence = _percentage(special_defence, 150)
            if item.hold_effect is ItemHoldEffect.DeepSeaScale and defender.species.name == "Clamperl":
                special_defence *= 2
            if item.hold_effect is ItemHoldEffect.MetalPowder and defender.species.name == "Ditto":
                defence *= 2

        # Abilities
        if defender.ability.name == "Thick Fat" and move_type.name in ("Fire", "Ice"):
            special_attack //= 2
        if attacker.ability.name == "Hustle":
            attack = _percentage(attack, 150)
        if attacker_partner is not None:
            if attacker.ability.name == "Plus" and attacker_partner.ability.name == "Minus":
                special_attack = _percentage(special_attack, 150)
            if attacker.ability.name == "Minus" and attacker_partner.ability.name == "Plus":
                special_attack = _percentage(special_attack, 150)
        if attacker.ability.name == "Guts" and attacker.status_permanent is not StatusCondition.Healthy:
            attack = _percentage(attack, 150)
        if defender.ability.name == "Marvel Scale" and attacker.status_permanent is not StatusCondition.Healthy:
            defence = _percentage(defence, 150)

        # todo:
        # if (type == TYPE_ELECTRIC && AbilityBattleEffects(ABILITYEFFECT_FIELD_SPORT, 0, 0, ABILITYEFFECT_MUD_SPORT, 0))
        #     gBattleMovePower /= 2;
        # if (type == TYPE_FIRE && AbilityBattleEffects(ABILITYEFFECT_FIELD_SPORT, 0, 0, ABILITYEFFECT_WATER_SPORT, 0))
        #     gBattleMovePower /= 2;

        if attacker.current_hp <= (attacker.total_hp // 3):
            if (
                (move_type.name == "Grass" and attacker.ability.name == "Overgrow")
                or (move_type.name == "Fire" and attacker.ability.name == "Blaze")
                or (move_type.name == "Water" and attacker.ability.name == "Torrent")
                or (move_type.name == "Bug" and attacker.ability.name == "Swarm")
            ):
                move_power = _percentage(move_power, 150)

        if move.effect == "EXPLOSION":
            defence //= 2

        damage = 0

        if move_type.is_physical:
            if is_critical_hit and attacker.stats_modifiers.attack <= 0:
                damage = attack
            else:
                damage = _calculate_modified_stat(attack, attacker.stats_modifiers.attack)

            damage *= move_power
            damage *= 2 * attacker.level // 5 + 2

            if is_critical_hit and defender.stats_modifiers.defence > 0:
                damage //= defence
            else:
                damage //= _calculate_modified_stat(defence, defender.stats_modifiers.defence)

            damage //= 50

            # Burn cuts attack in half
            if attacker.status_permanent is StatusCondition.Burn:
                damage //= 2

            # Reflect
            if defender_side.reflect_timer.turns_remaining > 0 and not is_critical_hit:
                if self._battle_state.is_double_battle and defender_partner is not None:
                    damage = 2 * (damage // 3)
                else:
                    damage //= 2

            # Moves hitting both targets do half damage in double battles
            if self._battle_state.is_double_battle and move.target == "BOTH" and defender_partner is not None:
                damage //= 2

            # Moves always do at least 1 damage.
            damage = max(1, damage)

        # '???'-type moves do no damage
        if move_type.name == "???":
            damage = 0

        if move_type.is_special:
            if is_critical_hit and attacker.stats_modifiers.special_attack <= 0:
                damage = special_attack
            else:
                damage = _calculate_modified_stat(special_attack, attacker.stats_modifiers.special_attack)

            damage *= move_power
            damage *= 2 * attacker.level // 5 + 2

            if is_critical_hit and defender.stats_modifiers.special_defence > 0:
                damage //= special_defence
            else:
                damage //= _calculate_modified_stat(special_defence, defender.stats_modifiers.special_defence)

            damage //= 50

            # Light Screen
            if defender_side.lightscreen_timer.turns_remaining > 0 and not is_critical_hit:
                if self._battle_state.is_double_battle and defender_partner is not None:
                    damage = 2 * (damage // 3)
                else:
                    damage //= 2

            # Moves hitting both targets do half damage in double battles
            if self._battle_state.is_double_battle and move.target == "BOTH" and defender_partner is not None:
                damage //= 2

            # todo: Check if Cloud Nine or Air Lock
            weather = self._battle_state.weather

            # Rain weakens Fire, boosts Water
            if Weather.Rain is weather:
                if move_type.name == "Fire":
                    damage //= 2
                if move_type.name == "Water":
                    damage = (15 * damage) // 10

            # Any weather except sun weakens solar beam
            if weather in (Weather.Rain, Weather.Sandstorm, Weather.Hail) and move.name == "Solar Beam":
                damage //= 2

            # Sun boosts Fire, weakens Water
            if Weather.Sunny is weather:
                if move_type.name == "Fire":
                    damage = (15 * damage) // 10
                if move_type.name == "Water":
                    damage //= 2

            # todo: Flash Fire

        return damage + 2
