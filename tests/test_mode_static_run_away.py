from tests.utility import FRLG_GAMES, BotTestCase, with_frame_timeout, with_master_test_states


class TestStaticRunAway(BotTestCase):
    # In R/S a legendary you ran from doesn't come back, so the mode doesn't exist there
    @with_master_test_states("SSR_SRA*.ss1", "SRA*.ss1", games=("Emerald", *FRLG_GAMES))
    @with_frame_timeout(40000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.modes.static_run_away import StaticRunAway

        yield from self.run_mode(StaticRunAway, 3)
        self.assert_encounters(EncounterType.Static, BattleOutcome.RanAway)
        self.assert_single_species()
