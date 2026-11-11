from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestLevelGrind(BotTestCase):
    @with_master_test_states("Level Grind*.ss1")
    @with_frame_timeout(30000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.context import context
        from modules.modes.level_grind import LevelGrindMode
        from modules.pokemon_party import get_party

        # These states test evolving and learning a move, which would stop the bot by default
        context.config.battle = context.config.battle.model_copy(
            update={"new_move": "learn_best", "stop_evolution": False}
        )
        level_before = get_party()[0].level
        yield from self.run_mode(LevelGrindMode, 3)
        self.assert_encounters(EncounterType.Land)
        # The bot runs away when the leader has no usable move left (out of PP), so not every battle is won
        outcomes = [encounter.outcome for encounter in self.stats.logged_encounters]
        self.assertTrue(set(outcomes) <= {BattleOutcome.Won, BattleOutcome.RanAway}, outcomes)
        self.assertIn(BattleOutcome.Won, outcomes)
        self.assertGreater(get_party()[0].level, level_before, "The party leader didn't level up.")
