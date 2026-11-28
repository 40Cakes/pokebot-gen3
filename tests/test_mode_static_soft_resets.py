from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestStaticSoftResets(BotTestCase):
    # The mode doesn't handle Groudon, Kyogre and Ho-Oh outside R/S, these states are for Static Run Away
    @with_master_test_states("SSR*.ss1", exclude=("SSR_SRA-Groudon*", "SSR_SRA-Kyogre*", "SSR_SRA-Ho-*"))
    @with_frame_timeout(20000)
    def test_it_gets_three_encounters_in_all_languages(self):
        from modules.battle_state import EncounterType
        from modules.modes.static_soft_resets import StaticSoftResetsMode, _get_targeted_encounter

        target = _get_targeted_encounter()
        yield from self.run_mode(StaticSoftResetsMode, 3, save_game=True)
        # The bot resets before the battle ends, so there's no outcome. Names like 'Latios/Latias'
        # mean either.
        self.assert_encounters(EncounterType.Static, None, species=target.name.split("/"))
        self.assert_single_species()
