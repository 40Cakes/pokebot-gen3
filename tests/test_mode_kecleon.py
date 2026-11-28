from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestKecleon(BotTestCase):
    # In R/S the Kecleon is gone after a whiteout, so the mode is Emerald only
    @with_master_test_states("Kecleon*.ss1", games=("Emerald",))
    @with_frame_timeout(30000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.modes.kecleon import KecleonMode

        yield from self.run_mode(KecleonMode, 3)
        # The mode loses on purpose, which the game counts as a draw
        self.assert_encounters(EncounterType.Static, BattleOutcome.Draw, species="Kecleon")
