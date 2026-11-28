from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestRoamerReset(BotTestCase):
    # Leaves out the Roamer Re-Encounter states, where the roamer already roams
    @with_master_test_states("Roam*.ss1", exclude=("Roamer-Reencounter*",))
    @with_frame_timeout(150000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.modes.roamer_reset import RoamerResetMode

        yield from self.run_mode(RoamerResetMode, 1, save_game=True)
        roamers = ("Latias", "Latios", "Raikou", "Entei", "Suicune")
        self.assert_encounters(EncounterType.Roamer, species=roamers)
