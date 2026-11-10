from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states

ROAMERS = ("Latias", "Latios", "Raikou", "Entei", "Suicune")


class TestRoamerReencounter(BotTestCase):
    # The states have a roaming roamer, a lead of the right level, Max Repels and Poké Balls
    @with_master_test_states("Roamer-Reencounter*.ss1")
    @with_frame_timeout(100000)
    def test_it_finds_the_roamer_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.context import context
        from modules.items import get_item_bag, get_item_by_name
        from modules.memory import write_symbol
        from modules.modes.roamer_reencounter import RoamerReencounterMode
        from modules.modes.util import repel_is_active
        from modules.player import get_player_avatar
        from modules.roamer import get_roamer

        if not RoamerReencounterMode.is_selectable():
            self.skipTest("The mode is not selectable in this state.")
        roamer = get_roamer()
        # The roamer moves at random when the player changes maps: start it on the player's map, so that the
        # test doesn't depend on luck (the save game doesn't keep where it is, so it would start nowhere)
        write_symbol("sRoamerLocation", bytes(get_player_avatar().map_group_and_number))
        max_repel = get_item_by_name("Max Repel")
        max_repels_at_start = get_item_bag().quantity_of(max_repel)

        # It goes back to Manual mode as soon as the roamer appears
        self.bot_mode.allow_ending_on_manual_mode = True
        mode = RoamerReencounterMode()
        self.bot_mode.forward_hooks_to(mode)
        for _ in mode.run():
            if context.bot_mode == "Manual":
                break
            yield
        self.assertIsInManualMode()
        # The mode stops when the battle starts, the encounter is logged once the opponent is visible
        for _ in range(1000):
            if self.stats.last_encounter is not None:
                break
            yield
        self.assertIsNotNone(self.stats.last_encounter, f"Manual mode without an encounter: {context.message!r}")

        self.assert_encounters(EncounterType.Roamer, species=ROAMERS)
        self.assertEqual(roamer.species.name, self.stats.last_encounter.species_name)
        # Repels keep other Pokémon away
        self.assertEqual(1, len(self.stats.logged_encounters), "Another Pokémon was met before the roamer.")
        self.assertLess(get_item_bag().quantity_of(max_repel), max_repels_at_start, "No Max Repel was used.")
        self.assertTrue(repel_is_active())
