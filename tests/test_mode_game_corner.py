from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestGameCorner(BotTestCase):
    @with_master_test_states("Game Corner*.ss1")
    @with_frame_timeout(30000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.modes.game_corner import GameCornerMode

        yield from self.run_mode(GameCornerMode, 3, save_game=True)
        self.assert_encounters(EncounterType.Gift, None)
        self.assert_single_species()
