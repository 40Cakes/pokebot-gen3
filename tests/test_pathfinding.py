from tests.utility import BotTestCase, with_save_state, with_frame_timeout


class TestPathfinding(BotTestCase):
    @with_save_state(
        [
            "emerald/new_game_inside_player_house.ss1",
            "ruby/new_game_inside_player_house.ss1",
            "firered/new_game_inside_player_house.ss1",
        ]
    )
    @with_frame_timeout(1000)
    def test_basic_pathfinding(self):
        from modules.map_data import MapRSE, MapFRLG
        from modules.modes.util import navigate_to
        from modules.player import get_player_location, player_avatar_is_controllable, player_avatar_is_standing_still

        if self.rom.is_rse:
            destination = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (9, 4)
        else:
            destination = MapFRLG.PALLET_TOWN_PLAYERS_HOUSE_1F, (8, 5)

        yield from navigate_to(*destination)
        self.assertEqual(destination, get_player_location())
        self.assertTrue(player_avatar_is_controllable(), "Player avatar is not controllable")
        self.assertTrue(player_avatar_is_standing_still(), "Player avatar is not standing still")

    @with_save_state(
        [
            "emerald/new_game_inside_player_house.ss1",
            "ruby/new_game_inside_player_house.ss1",
            "firered/new_game_inside_player_house.ss1",
        ]
    )
    @with_frame_timeout(1000)
    def test_will_follow_warps(self):
        from modules.map_data import MapRSE, MapFRLG
        from modules.modes.util import navigate_to
        from modules.player import get_player_location, player_avatar_is_controllable, player_avatar_is_standing_still

        if self.rom.is_rse:
            warp_tile = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (2, 2)
            destination = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F, (1, 2)
        else:
            warp_tile = MapFRLG.PALLET_TOWN_PLAYERS_HOUSE_1F, (10, 2)
            destination = MapFRLG.PALLET_TOWN_PLAYERS_HOUSE_2F, (10, 2)

        yield from navigate_to(*warp_tile)
        self.assertEqual(destination, get_player_location())
        self.assertTrue(player_avatar_is_controllable(), "Player avatar is not controllable")
        self.assertTrue(player_avatar_is_standing_still(), "Player avatar is not standing still")

    @with_save_state(
        [
            "emerald/new_game_inside_player_house.ss1",
            "ruby/new_game_inside_player_house.ss1",
            "firered/new_game_inside_player_house.ss1",
        ]
    )
    @with_frame_timeout(1000)
    def test_will_raise_exception_for_blocked_tile(self):
        from modules.map_data import MapRSE, MapFRLG
        from modules.modes import BotModeError
        from modules.modes.util import navigate_to

        if self.rom.is_rse:
            destination = MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (6, 6)
        else:
            destination = MapFRLG.PALLET_TOWN_PLAYERS_HOUSE_1F, (7, 5)

        with self.assertRaises(BotModeError):
            yield from navigate_to(*destination)

    @with_save_state(
        [
            "emerald/in_front_of_player_house_after_getting_starter.ss1",
            "ruby/in_front_of_player_house_after_getting_starter.ss1",
            "firered/in_front_of_viridian_pokemon_center.ss1",
        ]
    )
    @with_frame_timeout(1000)
    def test_will_move_across_connected_maps(self):
        from modules.map_data import MapRSE, MapFRLG
        from modules.modes.util import navigate_to
        from modules.player import get_player_location

        if self.rom.is_rse:
            destination = MapRSE.ROUTE101, (10, 11)
        else:
            destination = MapFRLG.ROUTE1, (7, 4)

        yield from navigate_to(*destination)
        self.assertEqual(get_player_location(), destination)

    @with_save_state("emerald/water_currents.ss1")
    def test_rse_water_currents(self):
        from modules.map_data import MapRSE
        from modules.modes.util import navigate_to
        from modules.player import get_player_location

        yield from navigate_to(MapRSE.ROUTE134, (61, 31))
        self.assertEqual(get_player_location(), (MapRSE.ROUTE134, (61, 31)))

    @with_save_state("emerald/diving.ss1")
    def test_rse_diving(self):
        from modules.map import get_map_data_for_current_position
        from modules.modes.util import dive, surface_from_dive

        yield from dive()
        self.assertEqual(get_map_data_for_current_position().map_type, "Underwater")
        yield from surface_from_dive()
        self.assertEqual(get_map_data_for_current_position().map_type, "Underground")
