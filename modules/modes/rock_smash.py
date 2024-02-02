from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.memory import get_event_flag
from modules.player import get_player, get_player_avatar, TileTransitionState
from modules.tasks import task_is_active
from ._asserts import assert_has_pokemon_with_move, assert_save_game_exists, assert_saved_on_map, SavedMapLocation
from ._interface import BotMode, BotModeError, BattleAction
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    navigate_to,
    follow_path,
    walk_one_tile,
    ensure_facing_direction,
    wait_until_task_is_not_active,
    wait_for_script_to_start_and_finish,
)


class RockSmashMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Rock Smash"

    @staticmethod
    def is_selectable() -> bool:
        if not context.rom.is_rse:
            return False

        return get_player_avatar().map_group_and_number in (
            MapRSE.GRANITE_CAVE_B.value,
            MapRSE.ROUTE_121_A.value,
            MapRSE.SAFARI_ZONE_C.value,
            MapRSE.SAFARI_ZONE_E.value,
            MapRSE.SAFARI_ZONE_F.value,
        )

    def __init__(self):
        super().__init__()
        self._in_safari_zone = False

    def on_battle_started(self) -> BattleAction | None:
        return BattleAction.RunAway

    def on_safari_zone_timeout(self) -> bool:
        self._in_safari_zone = False
        return True

    def run(self) -> Generator:
        self._in_safari_zone = False

        if not get_event_flag("BADGE03_GET"):
            raise BotModeError(
                "You do not have the Dynamo Badge, which is necessary to use Rock Smash outside of battle."
            )

        assert_has_pokemon_with_move(
            "Rock Smash", "None of your party Pokémon know the move Rock Smash. Please teach it to someone."
        )

        if context.config.battle.pickup:
            raise BotModeError("This mode should not be used while auto-pickup is enabled.")

        if get_player_avatar().map_group_and_number in (
            MapRSE.ROUTE_121_A.value,
            MapRSE.SAFARI_ZONE_C.value,
            MapRSE.SAFARI_ZONE_E.value,
            MapRSE.SAFARI_ZONE_F.value,
        ):
            assert_save_game_exists("There is no saved game. Cannot soft reset.")
            assert_saved_on_map(
                SavedMapLocation(MapRSE.ROUTE_121_A.value),
                "In order to rock smash for Shuckle you should save in the entrance building to the Safari Zone.",
            )

        starting_cash = get_player().money
        while True:
            match get_player_avatar().map_group_and_number:
                case MapRSE.GRANITE_CAVE_B.value:
                    yield from self.granite_cave()
                case MapRSE.ROUTE_121_A.value:
                    current_cash = get_player().money
                    if current_cash < 500 or starting_cash - current_cash > 25000:
                        yield from soft_reset()
                        yield from wait_for_unique_rng_value()
                        for _ in range(5):
                            yield
                        starting_cash = get_player().money
                    yield from self.enter_safari_zone()
                case MapRSE.SAFARI_ZONE_E.value:
                    self._in_safari_zone = True
                    for _ in self.safari_zone():
                        if self._in_safari_zone:
                            yield
                        else:
                            break
                case MapRSE.SAFARI_ZONE_C.value:
                    self._in_safari_zone = True
                    yield from navigate_to(39, 16)
                    yield from walk_one_tile("Right")
                case MapRSE.SAFARI_ZONE_F.value:
                    self._in_safari_zone = True
                    yield from navigate_to(8, 0)
                    yield from walk_one_tile("Up")

    @staticmethod
    def smash(flag_name):
        if not get_event_flag(flag_name):
            yield from wait_for_script_to_start_and_finish("EventScript_RockSmash", "A")
            while get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING:
                yield
            if task_is_active("Task_ReturnToFieldNoScript"):
                yield from wait_until_task_is_not_active("Task_ReturnToFieldNoScript")
            if task_is_active("Task_ExitNonDoor"):
                yield from wait_until_task_is_not_active("Task_ExitNonDoor")
        yield

    def granite_cave(self) -> Generator:
        yield from navigate_to(6, 21)
        yield from ensure_facing_direction("Down")
        yield from self.smash("TEMP_16")

        yield from follow_path([(4, 21)])
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_17")
        yield from ensure_facing_direction("Down")
        yield from self.smash("TEMP_15")

        yield from follow_path([(4, 16), (3, 16)])
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_13")

        yield from follow_path([(3, 15)])
        yield from ensure_facing_direction("Up")
        yield from self.smash("TEMP_12")

        yield from follow_path([(5, 15)])
        yield from ensure_facing_direction("Up")
        yield from self.smash("TEMP_11")

        yield from follow_path([(7, 15), (7, 13)])
        yield from ensure_facing_direction("Up")
        yield from self.smash("TEMP_14")

        yield from navigate_to(29, 14)
        yield from walk_one_tile("Up")
        yield from walk_one_tile("Up")
        yield from walk_one_tile("Down")
        yield from navigate_to(7, 13)
        yield from ensure_facing_direction("Up")
        yield from self.smash("TEMP_14")

        yield from follow_path([(7, 14), (6, 14)])
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_11")

        yield from follow_path([(4, 14)])
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_12")

        yield from follow_path([(4, 16), (3, 16)])
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_13")

        yield from follow_path([(4, 16), (4, 21)])
        yield from ensure_facing_direction("Down")
        yield from self.smash("TEMP_15")
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_17")

        yield from follow_path([(6, 21)])
        yield from ensure_facing_direction("Down")
        yield from self.smash("TEMP_16")

        yield from navigate_to(28, 20)
        yield from walk_one_tile("Down")
        yield from walk_one_tile("Down")
        yield from walk_one_tile("Up")

    def enter_safari_zone(self):
        if get_player().money < 500:
            raise BotModeError("You do not have enough cash to re-enter the Safari Zone.")
        yield from navigate_to(9, 4)
        yield from ensure_facing_direction("Left")
        context.emulator.hold_button("Left")
        for _ in range(10):
            yield
        context.emulator.release_button("Left")
        yield
        yield from wait_for_script_to_start_and_finish(
            "Route121_SafariZoneEntrance_EventScript_EntranceCounterTrigger", "A"
        )
        yield from wait_for_script_to_start_and_finish(
            "Route121_SafariZoneEntrance_EventScript_TryEnterSafariZone", "A"
        )
        while (
            get_player_avatar().local_coordinates != (32, 35)
            or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
        ):
            yield

    def safari_zone(self):
        yield from navigate_to(12, 7)
        yield from ensure_facing_direction("Down")
        yield from self.smash("TEMP_12")

        yield from follow_path([(10, 7)])
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_11")

        yield from follow_path([(10, 11)])
        yield from ensure_facing_direction("Right")
        yield from self.smash("TEMP_15")

        yield from follow_path([(8, 11)])
        yield from ensure_facing_direction("Up")
        yield from self.smash("TEMP_14")

        yield from follow_path([(8, 12)])
        yield from ensure_facing_direction("Down")
        yield from self.smash("TEMP_13")

        yield from navigate_to(8, 39)
        yield from walk_one_tile("Down")
        yield from walk_one_tile("Up")
