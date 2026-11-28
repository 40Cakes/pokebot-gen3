from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestDaycare(BotTestCase):
    @with_master_test_states("Daycare*.ss1")
    @with_frame_timeout(150000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.modes.daycare import DaycareMode

        yield from self.run_mode(DaycareMode, 1)
        self.assert_encounters(EncounterType.Hatched, None)
