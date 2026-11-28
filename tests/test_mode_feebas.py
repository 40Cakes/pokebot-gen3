from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestFeebas(BotTestCase):
    @with_master_test_states("Feebas*.ss1")
    @with_frame_timeout(60000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome
        from modules.modes.feebas import FeebasMode

        yield from self.run_mode(FeebasMode, 3)
        self.assertTrue(all(encounter.type.is_fishing for encounter in self.stats.logged_encounters))
        self.assert_encounters(outcome=BattleOutcome.RanAway)
