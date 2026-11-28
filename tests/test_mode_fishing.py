from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestFishing(BotTestCase):
    @with_master_test_states("Fish-*.ss1")
    @with_frame_timeout(30000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome
        from modules.modes.fishing import FishingMode

        yield from self.run_mode(FishingMode, 3, choices=["Super Rod", "Good Rod", "Old Rod"])
        fishing_types = {encounter.type for encounter in self.stats.logged_encounters}
        self.assertTrue(all(encounter_type.is_fishing for encounter_type in fishing_types), fishing_types)
        self.assertEqual(1, len(fishing_types), f"Fished with several rods: {fishing_types}")
        self.assert_encounters(outcome=BattleOutcome.RanAway, on_start_tile=True)
        self.assert_player_on_start_tile()
