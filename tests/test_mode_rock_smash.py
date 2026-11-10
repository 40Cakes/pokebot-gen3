from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestRockSmash(BotTestCase):
    @with_master_test_states("RockSmash-Nosepass*.ss1")
    @with_frame_timeout(40000)
    def test_granite_cave_in_all_languages(self):
        from modules.battle_state import BattleOutcome
        from modules.map_data import MapRSE
        from modules.modes.rock_smash import RockSmashMode

        yield from self.run_mode(RockSmashMode, 3, choices=["No Repel"])
        self.assert_encounters(outcome=BattleOutcome.RanAway, maps=[MapRSE.GRANITE_CAVE_B2F])

    # Shuckle is only found with Rock Smash in Emerald
    @with_master_test_states("RockSmash-Shuckle*.ss1", games=("Emerald",))
    @with_frame_timeout(40000)
    def test_shuckle_in_all_languages(self):
        import modules.modes.rock_smash as rock_smash
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.map_data import MapRSE
        from modules.modes import BotModeError
        from modules.modes._asserts import SavedMapLocation, assert_saved_on_map
        from modules.modes.util import leave_safari_zone, save_the_game

        # The mode soft resets to enter the Safari Zone again, so it needs a save game made in the
        # entrance building. The states are inside the Safari Zone.
        try:
            assert_saved_on_map(SavedMapLocation(MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE), "")
        except BotModeError:
            yield from leave_safari_zone()
            yield from save_the_game()

        # Skip the warning about not having much money
        rock_smash._displayed_warning_about_too_little_cash = True
        try:
            yield from self.run_mode(rock_smash.RockSmashMode, 3)
        finally:
            rock_smash._displayed_warning_about_too_little_cash = False
        self.assert_encounters(EncounterType.RockSmash, BattleOutcome.RanAway, species="Shuckle")
