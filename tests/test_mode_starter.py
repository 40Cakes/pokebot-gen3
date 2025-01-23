from tests.utility import BotTestCase, with_save_state, with_frame_timeout, set_next_choice, set_next_rng_seed


class TestStarter(BotTestCase):
    @with_save_state(
        [
            "emerald/in_front_of_starter_pokemon_bag.ss1",
            "ruby/in_front_of_starter_pokemon_bag.ss1",
            "firered/in_front_of_starter_pokemon_table.ss1",
        ]
    )
    @with_frame_timeout(10000)
    def test_it_runs_three_times(self):
        from modules.modes import BattleAction
        from modules.modes.starters import StartersMode

        if self.rom.is_rse:
            expected_species = "Mudkip"
            set_next_choice(expected_species)
        else:
            expected_species = "Squirtle"

        starters_mode = StartersMode()
        self.bot_mode.set_on_battle_started(lambda e: BattleAction.CustomAction)

        for _ in starters_mode.run():
            if len(self.stats.logged_encounters) > 3:
                for encounter in self.stats.logged_encounters:
                    self.assertEqual(expected_species, encounter.species_name)
                return None
            else:
                yield

    @with_save_state(
        [
            "emerald/in_front_of_starter_pokemon_bag.ss1",
            "ruby/in_front_of_starter_pokemon_bag.ss1",
            "firered/in_front_of_starter_pokemon_table.ss1",
        ]
    )
    @with_frame_timeout(10000)
    def test_it_stops_when_encountering_shiny(self):
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.starters import StartersMode

        if self.rom.is_emerald:
            rng_seed = 0x2FAB1EEB
            expected_species = "Treecko"
        elif self.rom.is_ruby:
            rng_seed = 0x327B87DF
            expected_species = "Treecko"
        elif self.rom.is_fr:
            rng_seed = 0x2031F790
            expected_species = "Squirtle"
        else:
            self.fail("No pre-calculated shiny seed available for this game.")

        set_next_choice(expected_species)
        set_next_rng_seed(rng_seed)

        starters_mode = StartersMode()
        self.bot_mode.set_on_battle_started(lambda e: BattleAction.CustomAction)
        self.bot_mode.allow_ending_on_manual_mode = True

        for _ in starters_mode.run():
            if self.stats.last_encounter is not None:
                self.assertEqual(expected_species, self.stats.last_encounter.species_name)
                self.assertTrue(self.stats.last_encounter.is_shiny, "Encountered starter Pokémon was not shiny.")
                self.assertIsInManualMode()
                return
            yield
