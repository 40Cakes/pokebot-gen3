import unittest

from tests.utility import (
    FRLG_GAMES,
    RSE_GAMES,
    BotTestCase,
    choose_option,
    master_test_states,
    use_unique_rng_values,
    with_frame_timeout,
    with_save_state,
)

# R/S/E have a state saved in the Safari Zone's entrance building. FR/LG only have states inside the
# Safari Zone, which the tests leave to save in the entrance building, as the mode starts from there.
RSE_STATES = master_test_states("Safari*.ss1", games=RSE_GAMES)
STATES = [*RSE_STATES, *master_test_states("Fish-Safari*.ss1", games=FRLG_GAMES)]


def with_safari_states(states: list[str]):
    return with_save_state(states) if states else unittest.skip("No Master Tests state for the Safari Zone")


def ensure_two_pokeblocks_of_a_type() -> None:
    """The mode only offers the feeder for a Pokéblock type the player has two of: copy one if needed."""
    from collections import Counter

    from modules.context import context
    from modules.items import get_pokeblocks
    from modules.memory import get_save_block, write_to_save_block

    if any(count >= 2 for count in Counter(pokeblock.type for pokeblock in get_pokeblocks()).values()):
        return
    # The Pokéblock case: 40 Pokéblocks of 8 bytes (colour, 5 flavours, feel, padding) in Save Block 1
    offset = 0x848 if context.rom.is_emerald else 0x7F8
    case = bytearray(get_save_block(1, offset=offset, size=40 * 8))
    filled = [index for index in range(40) if case[index * 8] != 0]
    # A red (spicy) Pokéblock if there is none
    pokeblock = bytes(case[filled[0] * 8 : filled[0] * 8 + 8]) if filled else bytes([1, 20, 0, 0, 0, 0, 20, 0])
    empty = [index for index in range(40) if case[index * 8] == 0]
    for index in empty[: 1 if filled else 2]:
        case[index * 8 : index * 8 + 8] = pokeblock
    write_to_save_block(bytes(case), 1, offset)
    context.state_cache.reset()


class TestSafari(BotTestCase):
    def prepare_save_game(self):
        """The mode needs a save game made in the Safari Zone's entrance building."""
        from modules.map_data import is_safari_map
        from modules.modes.util import leave_safari_zone, save_the_game, wait_for_player_avatar_to_be_controllable

        if is_safari_map():
            yield from leave_safari_zone()
        yield from save_the_game()
        # The save menu may still be closing
        yield from wait_for_player_avatar_to_be_controllable()

    def find_target(self, mode, condition=lambda target: True):
        """The first Safari Pokémon hunted with this mode that the save game allows (rod, Surf, bikes...)"""
        from modules.context import context
        from modules.modes import BotModeError
        from modules.modes.safari import SafariMode
        from modules.safari_strategy import get_safari_zone_config

        safari_mode = SafariMode()
        for target in get_safari_zone_config(context.rom)["safari_pokemon_list"].available_pokemon():
            if target.value.mode is not mode or not condition(target):
                continue
            try:
                safari_mode._check_mode_requirement(target.value.mode, target.value.hunting_object)
                safari_mode._check_map_requirement(target.value.map_location)
            except BotModeError:
                continue
            return target
        self.skipTest(f"No Safari Pokémon can be hunted with {mode.value} in this state.")

    def run_safari(self, target, *choices: str):
        from modules.modes.safari import SafariMode

        yield from self.run_mode(SafariMode, 3, choices=[target.value.species.name, *choices])

    def assert_hunted_at(self, target, encounter_type) -> None:
        # Walking to the hunting spot can already give encounters in the grass, so only the map is checked
        from modules.battle_state import BattleOutcome

        self.assert_encounters(encounter_type, BattleOutcome.RanAway, maps=[target.value.map_location])

    @with_safari_states(STATES)
    @with_frame_timeout(40000)
    def test_spin_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.safari_strategy import SafariHuntingMode

        yield from self.prepare_save_game()
        target = self.find_target(SafariHuntingMode.SPIN)
        yield from self.run_safari(target, "No Feeder", "No Repel")
        self.assert_hunted_at(target, EncounterType.Land)

    @with_safari_states(STATES)
    @with_frame_timeout(40000)
    def test_fishing_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.safari_strategy import SafariHuntingMode

        yield from self.prepare_save_game()
        target = self.find_target(SafariHuntingMode.FISHING)
        yield from self.run_safari(target, "No Feeder")
        rods = {
            "Old Rod": EncounterType.FishingWithOldRod,
            "Good Rod": EncounterType.FishingWithGoodRod,
            "Super Rod": EncounterType.FishingWithSuperRod,
        }
        self.assert_hunted_at(target, rods[target.value.hunting_object])

    @with_safari_states(STATES)
    @with_frame_timeout(40000)
    def test_surf_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.context import context
        from modules.debug_utilities import debug_create_pokemon, debug_write_party
        from modules.pokemon import LearnedMove, get_move_by_name
        from modules.pokemon_party import get_party
        from modules.safari_strategy import SafariHuntingMode

        if not get_party().has_pokemon_with_move("Surf"):
            # The Fire Red state has no Pokémon with Surf: the lead learns it, in its last move slot
            party = list(get_party())
            lead = party[0]
            moves = [move for move in lead.moves[:3] if move is not None] + [
                LearnedMove.create(get_move_by_name("Surf"))
            ]
            party[0] = debug_create_pokemon(lead.species, lead.level, original_pokemon=lead, moves=moves)
            debug_write_party(party)
            context.state_cache.reset()
        yield from self.prepare_save_game()
        target = self.find_target(SafariHuntingMode.SURF)
        yield from self.run_safari(target, "No Feeder", "No Repel")
        self.assert_hunted_at(target, EncounterType.Surfing)

    # FR/LG have no Pokéblocks
    @with_safari_states(RSE_STATES)
    @with_frame_timeout(40000)
    def test_feeder_in_all_languages(self):
        from collections import Counter

        from modules.battle_state import EncounterType
        from modules.items import get_pokeblocks
        from modules.modes.safari import SafariMode
        from modules.pokeblock_feeder import get_all_active_pokeblock_feeders
        from modules.safari_strategy import RSESafariStrategy, SafariHuntingMode

        ensure_two_pokeblocks_of_a_type()
        yield from self.prepare_save_game()
        counts = Counter(pokeblock.type for pokeblock in get_pokeblocks())
        pokeblock_type = next(pokeblock_type for pokeblock_type, count in counts.items() if count >= 2)
        target = self.find_target(
            SafariHuntingMode.SPIN,
            lambda target: RSESafariStrategy.get_facing_direction_for_position(target.value.tile_location),
        )
        pokeblocks_at_start = len(get_pokeblocks())

        def feeders_on_map():
            return [f for f in get_all_active_pokeblock_feeders() if f.on_map == target.value.map_location]

        # Walking to the spot can already give encounters, so the mode runs until the Pokéblock is in the
        # feeder and two more Pokémon were met (a new run would try to fill the feeder again)
        use_unique_rng_values()
        choose_option(target.value.species.name, "Use Feeder", pokeblock_type.name, "No Repel")
        mode = SafariMode()
        self.bot_mode.forward_hooks_to(mode)
        encounters_with_feeder = None
        for _ in mode.run():
            if encounters_with_feeder is None and len(feeders_on_map()) > 0:
                encounters_with_feeder = len(self.stats.logged_encounters)
            if encounters_with_feeder is not None and len(self.stats.logged_encounters) >= encounters_with_feeder + 2:
                break
            yield
        self.assertIsNotNone(encounters_with_feeder, "The mode stopped before using the feeder.")

        # One Pokéblock of that type is in the feeder next to the hunting spot
        feeders = feeders_on_map()
        self.assertEqual(1, len(feeders), "There is no Pokéblock in a feeder of the hunting map.")
        self.assertEqual(pokeblock_type, feeders[0].pokeblock.type)
        x, y = target.value.tile_location
        self.assertEqual(1, abs(feeders[0].coordinates[0] - x) + abs(feeders[0].coordinates[1] - y))
        self.assertEqual(pokeblocks_at_start - 1, len(get_pokeblocks()))
        self.assert_hunted_at(target, EncounterType.Land)

    @with_safari_states(STATES)
    @with_frame_timeout(40000)
    def test_repel_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.context import context
        from modules.debug_utilities import debug_create_pokemon, debug_write_item_bag, debug_write_party
        from modules.items import ItemSlot, get_item_bag, get_item_by_name
        from modules.modes.util import repel_is_active
        from modules.pokemon_party import get_party
        from modules.safari_strategy import SafariHuntingMode

        # A low level lead, so that Repel only keeps some of the Safari Zone's Pokémon away
        lead_level = 25
        party = list(get_party())
        party[0] = debug_create_pokemon(party[0].species, lead_level, original_pokemon=party[0])
        debug_write_party(party)
        bag = get_item_bag()
        max_repel = get_item_by_name("Max Repel")
        items = [ItemSlot(max_repel, 10)] + [slot for slot in bag.items if slot.item is not max_repel]
        debug_write_item_bag(items, bag.key_items, bag.poke_balls, bag.tms_hms, bag.berries)
        context.state_cache.reset()
        # The mode checks that the save game has Repels, as it soft resets to get more
        yield from self.prepare_save_game()

        target = self.find_target(SafariHuntingMode.SPIN)
        yield from self.run_safari(target, "No Feeder", "Use Repel")

        self.assertTrue(repel_is_active())
        self.assertLess(get_item_bag().quantity_of(max_repel), 10, "No Max Repel was used.")
        self.assert_hunted_at(target, EncounterType.Land)
        # Repel keeps away the wild Pokémon of a lower level than the lead
        for encounter in self.stats.logged_encounters:
            self.assertGreaterEqual(encounter.pokemon.level, lead_level, encounter.species_name)
