from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestSweetScent(BotTestCase):
    @with_master_test_states("Sweet Scent*.ss1")
    @with_frame_timeout(20000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.modes.sweet_scent import SweetScentMode

        yield from self.run_mode(SweetScentMode, 3)
        self.assert_encounters(EncounterType.Land, BattleOutcome.RanAway, on_start_tile=True)
        self.assert_player_on_start_tile()
