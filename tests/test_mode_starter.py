from tests.utility import (
    BotTestCase,
    set_next_choice,
    set_next_rng_seed,
    with_frame_timeout,
    with_master_test_states,
    with_save_state,
)


class TestStarter(BotTestCase):
    def run_starters(self, starter: str):
        from modules.battle_state import EncounterType
        from modules.modes.starters import StartersMode

        yield from self.run_mode(StartersMode, 3, choices=[starter], save_game=True)
        self.assert_encounters(EncounterType.Gift, species=starter)

    @with_save_state(
        [
            "emerald/in_front_of_starter_pokemon_bag.ss1",
            "ruby/in_front_of_starter_pokemon_bag.ss1",
            "firered/in_front_of_starter_pokemon_table.ss1",
        ]
    )
    @with_frame_timeout(10000)
    def test_it_runs_three_times(self):
        yield from self.run_starters("Mudkip" if self.rom.is_rse else "Squirtle")

    @with_master_test_states("Starters-Hoenn*.ss1")
    @with_frame_timeout(20000)
    def test_hoenn_starters_in_all_languages(self):
        yield from self.run_starters("Mudkip")

    @with_master_test_states("Starters-Johto*.ss1")
    @with_frame_timeout(20000)
    def test_johto_starters_in_all_languages(self):
        yield from self.run_starters("Totodile")

    @with_master_test_states("Starters-Kanto*.ss1")
    @with_frame_timeout(20000)
    def test_kanto_starters_in_all_languages(self):
        yield from self.run_starters("Squirtle")

    @with_save_state(
        [
            "emerald/in_front_of_starter_pokemon_bag.ss1",
            "ruby/in_front_of_starter_pokemon_bag.ss1",
            "firered/in_front_of_starter_pokemon_table.ss1",
        ]
    )
    @with_frame_timeout(10000)
    def test_it_stops_when_encountering_shiny(self):
        from modules.modes.starters import StartersMode

        # The RNG advances while text is printed, so in some languages another seed gives the shiny
        # (the English states are continued in other languages with `POKEBOT_TEST_LANGUAGE`)
        language = self.rom.language.value
        if self.rom.is_emerald:
            rng_seed = {"D": 0x0DFD87CD, "F": 0x0DFD87CD}.get(language, 0x2FAB1EEB)
            expected_species = "Treecko"
        elif self.rom.is_ruby:
            rng_seed = 0x327B87DF
            expected_species = "Treecko"
        elif self.rom.is_fr:
            rng_seed = {"D": 0xCC32BE74, "F": 0xE4B82B0C, "I": 0x6A8B044C, "J": 0xF7C63010, "S": 0x6B6A1D0A}.get(
                language, 0x2031F790
            )
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
