from tests.utility import BotTestCase, with_frame_timeout, with_save_state, set_next_rng_seed


class TestSpin(BotTestCase):
    @with_save_state(
        [
            "emerald/in_tall_grass_after_receiving_pokeballs.ss1",
            "ruby/in_tall_grass_after_receiving_pokeballs.ss1",
            "firered/in_tall_grass_after_receiving_pokeballs.ss1",
        ]
    )
    @with_frame_timeout(5000)
    def test_it_gets_three_encounters(self):
        from modules.modes.spin import SpinMode

        spin_mode = SpinMode()
        for _ in spin_mode.run():
            if len(self.stats.logged_encounters) > 3:
                return None
            else:
                yield

    @with_save_state(
        [
            "emerald/in_tall_grass_after_receiving_pokeballs.ss1",
            "ruby/in_tall_grass_after_receiving_pokeballs.ss1",
            "firered/in_tall_grass_after_receiving_pokeballs.ss1",
        ]
    )
    @with_frame_timeout(5000)
    def test_it_catches_shinies(self):
        from modules.battle_state import BattleOutcome
        from modules.modes.spin import SpinMode

        while True:
            if self.rom.is_emerald:
                rng_seed = 0x5EC05F1D
            elif self.rom.is_ruby:
                rng_seed = 0x7D5F2333
            elif self.rom.is_fr:
                rng_seed = 0x1ED06561
            else:
                self.fail("No pre-calculated shiny seed available for this game.")

            spin_mode = SpinMode()
            set_next_rng_seed(rng_seed)
            checked_encounter = False
            for _ in spin_mode.run():
                if self.stats.last_encounter is not None:
                    if not checked_encounter:
                        self.assertTrue(
                            self.stats.last_encounter.is_shiny, "Encountered starter Pokémon was not shiny."
                        )
                        checked_encounter = True
                    if self.stats.last_encounter.outcome is not None:
                        self.assertEqual(BattleOutcome.Caught, self.stats.last_encounter.outcome)
                        return
                else:
                    set_next_rng_seed(rng_seed)
                yield
