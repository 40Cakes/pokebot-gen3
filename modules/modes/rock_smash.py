from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.memory import get_event_flag
from modules.player import get_player, get_player_avatar, TileTransitionState
from modules.tasks import task_is_active, get_global_script_context
from ._asserts import assert_has_pokemon_with_move
from ._interface import BotMode, BotModeError
from ._util import (
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
            MapRSE.SAFARI_ZONE_C.value,
            MapRSE.SAFARI_ZONE_E.value,
            MapRSE.SAFARI_ZONE_F.value,
        )

    def run(self) -> Generator:
        if not get_event_flag("BADGE03_GET"):
            raise BotModeError(
                "You do not have the Dynamo Badge, which is necessary to use Rock Smash outside of battle."
            )

        assert_has_pokemon_with_move(
            "Rock Smash", "None of your party Pokémon know the move Rock Smash. Please teach it to someone."
        )

        if context.config.battle.pickup:
            raise BotModeError("This mode should not be used while auto-pickup is enabled.")

        def smash(flag_name):
            if not get_event_flag(flag_name):
                yield from wait_for_script_to_start_and_finish("EventScript_RockSmash", "A")
                while get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING:
                    yield
                if task_is_active("Task_ReturnToFieldNoScript"):
                    yield from wait_until_task_is_not_active("Task_ReturnToFieldNoScript")
            yield

        while True:
            match get_player_avatar().map_group_and_number:
                case MapRSE.GRANITE_CAVE_B.value:
                    yield from self.granite_cave()
                case MapRSE.SAFARI_ZONE_E.value:
                    for _ in self.safari_zone():
                        ctx = get_global_script_context()
                        if ctx.is_active and ctx.script_function_name == "SafariZone_EventScript_TimesUp":
                            context.emulator.reset_held_buttons()
                            while (
                                get_player_avatar().local_coordinates != (9, 4)
                                or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
                            ):
                                context.emulator.press_button("B")
                                yield
                            if get_player().money < 500:
                                raise BotModeError("You do not have enough cash to re-enter the Safari Zone.")
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
                            break
                        yield
                case MapRSE.SAFARI_ZONE_C.value:
                    yield from navigate_to(39, 16)
                    yield from walk_one_tile("Right")
                case MapRSE.SAFARI_ZONE_F.value:
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
