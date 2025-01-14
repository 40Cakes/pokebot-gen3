import random
import unittest

from modules.context import context
from modules.modes import BattleAction
from modules.modes.starters import StartersMode
from modules.player import get_player
from tests.run import with_save_state, with_frame_timeout, mock_values


def get_shiny_seed(frame_delay: int) -> int:
    player = get_player()

    while True:
        seed = random.randint(0, 0xFFFF_FFFF)

        rng_value = seed
        for _ in range(frame_delay):
            rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
        pv_upper = rng_value >> 16
        rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF
        pv_lower = rng_value >> 16

        if player.trainer_id ^ player.secret_id ^ pv_upper ^ pv_lower < 8:
            return seed


class TestStarter(unittest.TestCase):
    @with_save_state("states/emerald/in_front_of_starter_pokemon_bag.ss1")
    @with_frame_timeout(5000)
    def test_runs_three_times(self):
        mock_values.choice = "Mudkip"

        starters_mode = StartersMode()
        context.bot_mode_instance.on_battle_started = lambda e: BattleAction.CustomAction

        for _ in starters_mode.run():
            if len(context.stats.logged_encounters) > 3:
                for encounter in context.stats.logged_encounters:
                    self.assertEqual(encounter.species_name, "Mudkip")
                return None
            else:
                yield

    @with_save_state("states/emerald/in_front_of_starter_pokemon_bag.ss1")
    @with_frame_timeout(5000)
    def test_stops_when_encountering_shiny(self):
        mock_values.choice = "Treecko"
        mock_values.rng_seed = get_shiny_seed(30)

        starters_mode = StartersMode()
        bot_mode = context.bot_mode_instance
        context.bot_mode_instance.on_battle_started = lambda e: BattleAction.CustomAction

        yield from starters_mode.run()
        self.assertIsNotNone(context.stats.last_encounter)
        self.assertTrue(context.stats.last_encounter.is_shiny, "Encountered starter Pokémon was not shiny.")
        self.assertEqual(context.stats.last_encounter.species_name, "Treecko")
        self.assertEqual(context.bot_mode, "Manual")
        bot_mode.allow_ending_on_manual_mode = True
