from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestSudowoodo(BotTestCase):
    @with_master_test_states("Sudowoodo*.ss1")
    @with_frame_timeout(30000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.modes.sudowoodo import SudowoodoMode

        yield from self.run_mode(SudowoodoMode, 3, save_game=True)
        self.assert_encounters(EncounterType.Static, None, species="Sudowoodo")
        self.assert_player_on_start_tile()
