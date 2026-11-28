from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states

EGG_STATES = ("SGR*Wynaut*.ss1", "SGR*Togepi*.ss1")

# The mode's target names that are not a single species
SPECIES = {
    "Kanto Fossils": ("Omanyte", "Kabuto", "Aerodactyl"),
    "Hoenn Fossils": ("Lileep", "Anorith"),
}


class TestStaticGiftResets(BotTestCase):
    def run_gift_resets(self, number_of_encounters: int, encounter_type):
        from modules.modes.static_gift_resets import StaticGiftResetsMode, _get_targeted_encounter

        target = _get_targeted_encounter()
        yield from self.run_mode(StaticGiftResetsMode, number_of_encounters, save_game=True)
        expected_species = SPECIES.get(target[2], target[2])
        self.assert_encounters(encounter_type, None, species=expected_species)
        self.assert_single_species()

    @with_master_test_states("SGR*.ss1", exclude=EGG_STATES)
    @with_frame_timeout(20000)
    def test_it_gets_three_gifts_in_all_languages(self):
        from modules.battle_state import EncounterType

        yield from self.run_gift_resets(3, EncounterType.Gift)

    @with_master_test_states(*EGG_STATES)
    @with_frame_timeout(150000)
    def test_it_hatches_an_egg_in_all_languages(self):
        from modules.battle_state import EncounterType

        yield from self.run_gift_resets(1, EncounterType.Hatched)
