from tests.utility import RSE_GAMES, BotTestCase, give_key_item, with_frame_timeout, with_master_test_states


class TestBunnyHop(BotTestCase):
    @with_master_test_states("Spin_Bunny-*.ss1", games=RSE_GAMES)
    @with_frame_timeout(20000)
    def test_it_gets_encounters_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.modes.bunny_hop import BunnyHopMode

        # Some states have the Mach Bike
        give_key_item("Acro Bike", instead_of="Mach Bike")
        yield from self.run_mode(BunnyHopMode, 3)
        self.assert_encounters(EncounterType.Land, BattleOutcome.RanAway, on_start_tile=True)
        self.assert_player_on_start_tile()
