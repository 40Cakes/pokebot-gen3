from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.encounter import handle_encounter
from modules.gui.multi_select_window import ask_for_choice, Selection
from modules.items import get_item_bag
from modules.map import get_map_objects
from modules.memory import get_event_flag, get_event_var
from modules.player import get_player, get_player_avatar, TileTransitionState
from modules.pokemon import get_opponent
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from modules.tasks import task_is_active
from . import BattleAction
from ._asserts import assert_has_pokemon_with_move, assert_save_game_exists, assert_saved_on_map, SavedMapLocation
from ._interface import BotMode, BotModeError
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    navigate_to,
    follow_path,
    walk_one_tile,
    ensure_facing_direction,
    wait_until_task_is_not_active,
    wait_for_script_to_start_and_finish,
    apply_white_flute_if_available,
    apply_repel,
    replenish_repel,
    RanOutOfRepels,
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
        self._using_repel = False

    def on_safari_zone_timeout(self) -> bool:
        self._in_safari_zone = False
        return True

    def on_battle_started(self) -> BattleAction | None:
        return handle_encounter(get_opponent(), disable_auto_battle=True)

    def on_repel_effect_ended(self) -> None:
        if self._using_repel:
            try:
                replenish_repel()
            except RanOutOfRepels:
                context.controller_stack.insert(len(context.controller_stack) - 1, self.reset_and_wait())

    def run(self) -> Generator:
        self._in_safari_zone = False
        self._using_repel = False

        if not get_event_flag("BADGE03_GET"):
            raise BotModeError(
                "You do not have the Dynamo Badge, which is necessary to use Rock Smash outside of battle."
            )

        assert_has_pokemon_with_move(
            "Rock Smash", "None of your party Pokémon know the move Rock Smash. Please teach it to someone."
        )

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

        if get_player_avatar().map_group_and_number == MapRSE.GRANITE_CAVE_B.value:
            if get_item_bag().number_of_repels > 0:
                mode = ask_for_choice(
                    [
                        Selection("Use Repel", get_sprites_path() / "items" / "Repel.png"),
                        Selection("Don't use Repel", get_sprites_path() / "items" / "None.png"),
                    ],
                    window_title="Choose Method..."
                )

                if mode == "Use Repel":
                    assert_save_game_exists("There is no saved game. Cannot soft reset.")
                    assert_saved_on_map(
                        SavedMapLocation(MapRSE.GRANITE_CAVE_B.value),
                        "In order to use Repel, you need to save on this map.",
                    )

                    save_data = get_save_data()
                    party = save_data.get_party()
                    if len(party) == 0 or party[0].is_egg or party[0].level < 13 or party[0].level > 16:
                        raise BotModeError(
                            "In order to use Repel, you must have a lead Pokémon with level 13-16. For best encounter rates, use Level 13!"
                        )

                    if save_data.get_item_bag().number_of_repels == 0:
                        raise BotModeError("In your saved game, you do not have any Repels.")

                    self._using_repel = True
                    yield from self.reset_and_wait()

        starting_cash = get_player().money
        while True:
            match get_player_avatar().map_group_and_number:
                case MapRSE.GRANITE_CAVE_B.value:
                    starting_frame = context.emulator.get_frame_count()
                    for _ in self.granite_cave():
                        # Detect reset
                        if context.emulator.get_frame_count() < starting_frame:
                            break
                        yield
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
    def reset_and_wait():
        context.emulator.reset_held_buttons()
        yield from soft_reset()
        yield from wait_for_unique_rng_value()
        while (
            get_map_objects() is None
            or "heldMovementFinished" not in get_map_objects()[0].flags
            or "heldMovementActive" not in get_map_objects()[0].flags
        ):
            yield

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
        if self._using_repel and get_event_var("REPEL_STEP_COUNT") <= 0:
            try:
                yield from apply_repel()
            except RanOutOfRepels:
                pass

        yield from navigate_to(6, 21)
        yield from ensure_facing_direction("Down")
        # With Repel active, White Flute boosts encounters by 30-40%, but without Repel it
        # actually _decreases_ encounter rates (due to so many regular encounters popping up
        # while walking around.) So we only enable White Flute if Repel is also active.
        if self._using_repel:
            yield from apply_white_flute_if_available()
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
        if self._using_repel:
            yield from apply_white_flute_if_available()
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
