from tests.utility import BotTestCase, use_unique_rng_values, with_frame_timeout, with_master_test_states

# Like 'Sky Pillar puzzle complete!' or '1000 ashes collected! ...'
SUCCESS_MESSAGE = r"puzzle complete!|ashes collected!"


class TestPuzzleSolver(BotTestCase):
    @with_master_test_states("Puzzle-*.ss1")
    @with_frame_timeout(60000)
    def test_it_solves_the_puzzle_in_all_languages(self):
        from modules.context import context
        from modules.modes.puzzle_solver import PuzzleSolverMode

        if not PuzzleSolverMode.is_selectable():
            self.fail("The mode can't be selected in this state.")
        use_unique_rng_values()

        # Puzzles end in Manual mode with a success message. Wild Pokémon met on the way don't end the test:
        # the bot fights or runs from them and goes on with the puzzle.
        self.bot_mode.allow_ending_on_manual_mode = True
        mode = PuzzleSolverMode()
        self.bot_mode.forward_hooks_to(mode)
        for _ in mode.run():
            if context.bot_mode == "Manual":
                break
            yield
        last_encounter = self.stats.last_encounter
        if last_encounter is not None and last_encounter.is_shiny:
            # Stopping for a shiny is the expected behaviour
            return
        self.assertRegex(context.message, SUCCESS_MESSAGE)
