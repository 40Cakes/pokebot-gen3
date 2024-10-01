from modules.battle_state import BattleState
from modules.battle_strategies import DefaultBattleStrategy, TurnAction
from modules.context import context
from modules.pokemon import get_party


def _get_lowest_level_party_member_index(only_non_fainted: bool = False) -> int:
    lowest_level: tuple[int, int] | None = None
    party = get_party()
    for index in range(len(party)):
        pokemon = party[index]
        if not pokemon.is_egg and (only_non_fainted is False or pokemon.current_hp > 0):
            if lowest_level is None or pokemon.level < lowest_level[1]:
                lowest_level = (index, pokemon.level)
    return lowest_level[0]


class LevelBalancingBattleStrategy(DefaultBattleStrategy):
    def choose_new_lead_after_faint(self, battle_state: BattleState) -> int:
        return _get_lowest_level_party_member_index(only_non_fainted=True)

    def choose_new_lead_after_battle(self) -> int | None:
        lowest_level_index = _get_lowest_level_party_member_index()
        return lowest_level_index if lowest_level_index > 0 else None

    def decide_turn(self, battle_state: BattleState) -> tuple["TurnAction", any]:
        battler = battle_state.own_side.active_battler

        # If the lead Pokémon (the one with the lowest level) is on low HP, try switching
        # in the most powerful Pokémon in the party to defeat the opponent, so that the
        # lead Pokémon at least gets partial XP.
        # This helps if the lead has a much lower level than the encounters.
        if battler.party_index == 0 and battler.current_hp_percentage < context.config.battle.hp_threshold:
            strongest_pokemon: tuple[int, int] = (0, 0)
            party = get_party()
            for index in range(len(party)):
                if self.pokemon_can_battle(party[index]) and party[index].level > strongest_pokemon[1]:
                    strongest_pokemon = (index, party[index].level)
            if strongest_pokemon[0] > 0:
                return TurnAction.rotate_lead(strongest_pokemon[0])

        return super().decide_turn(battle_state)
