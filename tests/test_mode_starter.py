from tests.utility import (
    BotTestCase,
    with_save_state,
    with_frame_timeout,
    set_next_choice,
    set_next_rng_seed,
    use_unique_rng_values,
    with_master_test_states,
    ensure_save_game,
)


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
        from modules.modes.starters import StartersMode

        if self.rom.is_rse:
            expected_species = "Mudkip"
            set_next_choice(expected_species)
        else:
            expected_species = "Squirtle"

        use_unique_rng_values()
        starters_mode = StartersMode()
        self.bot_mode.forward_hooks_to(starters_mode)

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
        self.bot_mode.forward_hooks_to(starters_mode)
        self.bot_mode.allow_ending_on_manual_mode = True

        for _ in starters_mode.run():
            if self.stats.last_encounter is not None:
                self.assertEqual(expected_species, self.stats.last_encounter.species_name)
                self.assertTrue(self.stats.last_encounter.is_shiny, "Encountered starter Pokémon was not shiny.")
                self.assertIsInManualMode()
                return
            yield


class TestStarterAllLanguages(BotTestCase):
    """Runs the Starters mode with Johnnie's Master Tests states, in every game and language."""

    def run_until_three_encounters(self, choice: str, expected_species: str):
        from modules.modes.starters import StartersMode

        yield from ensure_save_game()
        use_unique_rng_values()
        set_next_choice(choice)

        starters_mode = StartersMode()
        self.bot_mode.forward_hooks_to(starters_mode)
        for _ in starters_mode.run():
            if len(self.stats.logged_encounters) >= 3:
                for encounter in self.stats.logged_encounters:
                    self.assertEqual(expected_species, encounter.species_name)
                return
            yield

    @with_master_test_states("Starters-Hoenn*.ss1")
    @with_frame_timeout(20000)
    def test_hoenn_starters(self):
        yield from self.run_until_three_encounters("Mudkip", "Mudkip")

    @with_master_test_states("Starters-Johto*.ss1")
    @with_frame_timeout(20000)
    def test_johto_starters(self):
        yield from self.run_until_three_encounters("Totodile", "Totodile")

    @with_master_test_states("Starters-Kanto*.ss1")
    @with_frame_timeout(20000)
    def test_kanto_starters(self):
        yield from self.run_until_three_encounters("Squirtle", "Squirtle")
