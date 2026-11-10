from typing import TYPE_CHECKING

from tests.utility import BotTestCase, use_unique_rng_values, with_frame_timeout, with_master_test_states

if TYPE_CHECKING:
    from modules.items import Item

# `struct BattlePokemon` in `gBattleMons`, the opponent is the second one
BATTLE_POKEMON_SIZE = 0x58
HELD_ITEM_OFFSET = 0x2E
PERSONALITY_OFFSET = 0x48


def give_thief_to_lead() -> None:
    """Teaches Thief to the lead in its first move slot, and takes its held item so that it can steal one."""
    from modules.context import context
    from modules.debug_utilities import debug_create_pokemon, debug_write_party
    from modules.pokemon import LearnedMove, get_move_by_name
    from modules.pokemon_party import get_party

    party = list(get_party())
    lead = party[0]
    moves = [LearnedMove.create(get_move_by_name("Thief"))] + [move for move in lead.moves[1:] if move is not None]
    party[0] = debug_create_pokemon(lead.species, lead.level, original_pokemon=lead, moves=moves, held_item=None)
    debug_write_party(party)
    # The party is cached for the current frame
    context.state_cache.reset()


def give_item_to_opponent() -> "Item | None":
    """
    Wild Pokémon rarely hold an item, so the opponent gets the first item its species can hold. Returns that
    item, or None if its species can't hold one. Called when the battle starts: the item is written both in
    the enemy party and in the battle data, whichever the game has already copied.
    """
    from modules.debug_utilities import debug_create_pokemon
    from modules.items import get_item_by_name
    from modules.memory import pack_uint16, read_symbol, unpack_uint32, write_symbol
    from modules.pokemon import get_opponent

    opponent = get_opponent()
    if opponent is None or len(opponent.species.held_items) == 0:
        return None
    # Species data holds the item's name
    item = get_item_by_name(opponent.species.held_items[0].item)
    with_item = debug_create_pokemon(opponent.species, opponent.level, original_pokemon=opponent, held_item=item)
    write_symbol("gEnemyParty", with_item.data)
    battle_data = read_symbol("gBattleMons", offset=BATTLE_POKEMON_SIZE, size=BATTLE_POKEMON_SIZE)
    if unpack_uint32(battle_data[PERSONALITY_OFFSET : PERSONALITY_OFFSET + 4]) == opponent.personality_value:
        write_symbol("gBattleMons", pack_uint16(item.index), offset=BATTLE_POKEMON_SIZE + HELD_ITEM_OFFSET)
    return item


class TestItemSteal(BotTestCase):
    # Item Steal works on the same maps as Level Grind. In FR/LG, no Pokémon of the Level Grind maps can
    # hold an item: the 'Item Steal' states are in Route 7, where Meowth can.
    @with_master_test_states("Level Grind*.ss1", "Item Steal*.ss1")
    @with_frame_timeout(60000)
    def test_it_steals_the_opponents_item_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.items import get_item_bag
        from modules.map import get_wild_encounters_for_map
        from modules.memory import GameState, get_game_state
        from modules.modes.item_steal import ItemStealMode
        from modules.player import get_player_avatar
        from modules.pokemon_party import get_party

        give_thief_to_lead()
        if not ItemStealMode.is_selectable():
            self.skipTest("The mode is not selectable in this state.")
        encounters = get_wild_encounters_for_map(*get_player_avatar().map_group_and_number)
        if not any(len(encounter.species.held_items) > 0 for encounter in encounters.land_encounters):
            self.skipTest("No Pokémon of this map can hold an item, so the mode only runs away.")
        use_unique_rng_values()

        mode = ItemStealMode()
        # The item given to each opponent, with how many of it the bag held then
        given_items = []
        # The test doesn't run during battles (the battle handler does), so this is done when one starts
        on_battle_started = mode.on_battle_started

        def give_item_and_start_battle(encounter):
            item = give_item_to_opponent()
            if item is not None:
                given_items.append((item, get_item_bag().quantity_of(item)))
            return on_battle_started(encounter)

        def stolen_item() -> "Item | None":
            for item, quantity_before in given_items:
                if get_item_bag().quantity_of(item) > quantity_before:
                    return item
            return None

        mode.on_battle_started = give_item_and_start_battle
        self.bot_mode.forward_hooks_to(mode)
        for _ in mode.run():
            # The bag can't be read while the game moves its save data, during map changes
            if get_game_state() is GameState.OVERWORLD and stolen_item() is not None:
                break
            yield

        self.assert_encounters(EncounterType.Land)
        # It only fights Pokémon that can hold an item
        for encounter in self.stats.logged_encounters:
            if len(encounter.pokemon.species.held_items) == 0:
                self.assertEqual(BattleOutcome.RanAway, encounter.outcome, encounter.species_name)
        # Thief took the opponent's item, and the bot moved it from the lead to the bag
        self.assertIsNotNone(stolen_item())
        self.assertIsNone(get_party()[0].held_item, "The lead still holds the stolen item.")
