from tests.utility import BotTestCase, use_unique_rng_values, with_frame_timeout, with_master_test_states

# Like 'Sky Pillar puzzle complete!' or '1000 ashes collected! ...'
SUCCESS_MESSAGE = r"complete|collected"


class TestPuzzleSolver(BotTestCase):
    @with_master_test_states("Puzzle-*.ss1")
    @with_frame_timeout(60000)
    def test_it_solves_the_puzzle_in_all_languages(self):
        from modules.context import context
        from modules.modes.puzzle_solver import PuzzleSolverMode

        if not PuzzleSolverMode.is_selectable():
            self.skipTest("The mode is not selectable in this state.")
        use_unique_rng_values()

        # Puzzles end in Manual mode with a message, or with an encounter
        self.bot_mode.allow_ending_on_manual_mode = True
        mode = PuzzleSolverMode()
        self.bot_mode.forward_hooks_to(mode)
        for _ in mode.run():
            if len(self.stats.logged_encounters) > 0 or context.bot_mode == "Manual":
                break
            yield
        if len(self.stats.logged_encounters) == 0:
            self.assertRegex(context.message, SUCCESS_MESSAGE)
