import unittest

from modules.modes.util import *
from modules.player import get_player_location
from tests.run import with_save_state


class TestPathfinding(unittest.TestCase):
    @with_save_state("states/emerald/new_game_inside_player_house.ss1")
    def test_basic_pathfinding(self):
        yield from navigate_to(MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (9, 4))
        self.assertEqual(get_player_location(), (MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (9, 4)))

    @with_save_state("states/emerald/new_game_inside_player_house.ss1")
    def test_will_follow_warps(self):
        yield from navigate_to(MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (2, 2))
        self.assertEqual(get_player_location(), (MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F, (1, 2)))

    @with_save_state("states/emerald/new_game_inside_player_house.ss1")
    def test_will_raise_exception_for_blocked_tile(self):
        with self.assertRaises(BotModeError):
            yield from navigate_to(MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_1F, (6, 6))

    @with_save_state("states/emerald/in_front_of_player_house_after_getting_starter.ss1")
    def test_will_move_across_connected_maps(self):
        yield from navigate_to(MapRSE.ROUTE101, (10, 11))
        self.assertEqual(get_player_location(), (MapRSE.ROUTE101, (10, 11)))

    @with_save_state("states/emerald/water_currents.ss1")
    def test_rse_water_currents(self):
        yield from navigate_to(MapRSE.ROUTE134, (61, 31))
        self.assertEqual(get_player_location(), (MapRSE.ROUTE134, (61, 31)))

    @with_save_state("states/emerald/diving.ss1")
    def test_rse_diving(self):
        yield from dive()
        self.assertEqual(get_map_data_for_current_position().map_type, "Underwater")
        yield from surface_from_dive()
        self.assertEqual(get_map_data_for_current_position().map_type, "Underground")
