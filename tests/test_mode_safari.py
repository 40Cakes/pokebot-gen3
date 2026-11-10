from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestSafari(BotTestCase):
    @with_master_test_states("Safari*.ss1")
    @with_frame_timeout(40000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.map_data import MapFRLG, MapRSE
        from modules.modes.safari import SafariMode

        yield from self.run_mode(SafariMode, 3, choices=["No Feeder", "No Repel"], save_game=True)
        safari_maps = [m for m in (*MapRSE, *MapFRLG) if "SAFARI_ZONE" in m.name and "ENTRANCE" not in m.name]
        self.assert_encounters(EncounterType.Land, BattleOutcome.RanAway, maps=safari_maps)
