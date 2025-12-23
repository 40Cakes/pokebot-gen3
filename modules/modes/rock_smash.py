import contextlib
from collections import deque
from typing import Generator

from modules.battle_state import BattleOutcome
from modules.context import context
from modules.debug import debug
from modules.encounter import handle_encounter, EncounterInfo
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.items import get_item_bag, get_item_by_name
from modules.map_data import MapRSE, is_safari_map
from modules.map_path import calculate_path
from modules.memory import get_event_flag, read_symbol, unpack_uint16
from modules.player import TileTransitionState, get_player, get_player_avatar, AvatarFlags, get_player_location
from modules.runtime import get_sprites_path
from modules.safari_strategy import get_safari_balls_left
from modules.save_data import get_save_data
from modules.tasks import task_is_active, get_global_script_context
from . import BattleAction
from ._asserts import (
    SavedMapLocation,
    assert_has_pokemon_with_any_move,
    assert_save_game_exists,
    assert_saved_on_map,
    assert_player_has_poke_balls,
    assert_boxes_or_party_can_fit_pokemon,
    assert_item_exists_in_bag,
)
from ._interface import BotMode, BotModeError
from .util import (
    navigate_to,
    follow_waypoints,
    RanOutOfRepels,
    apply_repel,
    repel_is_active,
    apply_white_flute_if_available,
    ensure_facing_direction,
    follow_path,
    soft_reset,
    wait_for_player_avatar_to_be_standing_still,
    wait_for_script_to_start_and_finish,
    wait_for_unique_rng_value,
    wait_until_task_is_not_active,
    walk_one_tile,
    leave_safari_zone,
)


class RockSmashMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Rock Smash"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_frlg:
            return False

        player_map = get_player_avatar().map_group_and_number

        if context.rom.is_rs:
            return player_map == MapRSE.GRANITE_CAVE_B2F

        allowed_maps = {
            MapRSE.GRANITE_CAVE_B2F,
            MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE,
            MapRSE.SAFARI_ZONE_SOUTH,
            MapRSE.SAFARI_ZONE_NORTHEAST,
            MapRSE.SAFARI_ZONE_SOUTHEAST,
        }

        return player_map in allowed_maps

    def __init__(self):
        super().__init__()
        self._in_safari_zone = False
        self._using_repel = False
        self._using_mach_bike = False
        self._nosepass_frames: deque[int] = deque(maxlen=1000)

        self._should_delay_a_frame: bool = False
        self._duplicates_found: int = 0

    def on_safari_zone_timeout(self) -> bool:
        self._in_safari_zone = False
        return True

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        # Because we might be soft-resetting fairly often in this mode, and it can take a
        # while to get an encounter, there's a decent chance to end up with the same RNG
        # value at some point even though the starting value was different. (This might
        # happen to random overworld events and the like.)
        #
        # For that reason, we will do the expensive thing of checking each encounter with
        # the stats DB to identify duplicates. If a duplicate has been found, we will wait
        # for a single frame after the battle is over so we're not in sync with a previous
        # RNG sequence any more.
        #
        # Also, after each reset we will delay one frame for each duplicate that we have
        # previously encountered.
        if context.stats.has_encounter_with_personality_value(encounter.pokemon.personality_value):
            self._should_delay_a_frame = True
            self._duplicates_found += 1

        if encounter.pokemon.species.name == "Nosepass":
            self._nosepass_frames.append(context.frame)
            if len(self._nosepass_frames) > 1:
                first_recorded_frame = self._nosepass_frames[0]
                last_recorded_frame = self._nosepass_frames[-1]
                frame_diff = last_recorded_frame - first_recorded_frame
                average_frames_per_encounter = frame_diff / (len(self._nosepass_frames) - 1)
                average_seconds_per_encounter = average_frames_per_encounter / 59.727500569606
                if average_seconds_per_encounter > 0:
                    encounter_rate_at_1x = round(3600 / average_seconds_per_encounter, 1)
                else:
                    encounter_rate_at_1x = 0

                debug.debug_values["Nosepass per Hour"] = encounter_rate_at_1x
        return handle_encounter(encounter)

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if outcome is BattleOutcome.Caught and not context.config.battle.save_after_catching:
            context.message = (
                "A Pokémon has been caught. Switching to manual mode so we don't lose it when soft-resetting."
            )
            context.set_manual_mode()

        if outcome is not BattleOutcome.Lost:
            assert_player_has_poke_balls()
            assert_boxes_or_party_can_fit_pokemon()

    def on_repel_effect_ended(self) -> None:
        if self._using_repel:
            try:
                yield from apply_repel()
            except RanOutOfRepels:
                yield from self.reset_and_wait()

    def run(self) -> Generator:
        self._in_safari_zone = False
        self._using_repel = False

        if not get_event_flag("BADGE03_GET"):
            raise BotModeError(
                "You do not have the Dynamo Badge, which is necessary to use Rock Smash outside of battle."
            )

        assert_boxes_or_party_can_fit_pokemon()
        assert_has_pokemon_with_any_move(
            ["Rock Smash"], "None of your party Pokémon know the move Rock Smash. Please teach it to someone."
        )

        if get_player_avatar().map_group_and_number in (
            MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE,
            MapRSE.SAFARI_ZONE_SOUTH,
            MapRSE.SAFARI_ZONE_NORTHEAST,
            MapRSE.SAFARI_ZONE_SOUTHEAST,
        ):
            assert_save_game_exists("There is no saved game. Cannot soft reset.")
            assert_boxes_or_party_can_fit_pokemon(check_in_saved_game=True)
            assert_saved_on_map(
                SavedMapLocation(MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE),
                "In order to rock smash for Shuckle you should save in the entrance building to the Safari Zone.",
            )
            assert_item_exists_in_bag(
                "Pokéblock Case", error_message="You need to own the Pokéblock Case in order to enter the Safari Zone."
            )
            assert_item_exists_in_bag(
                "Pokéblock Case",
                error_message="You need to own the Pokéblock Case in order to enter the Safari Zone.",
                check_in_saved_game=True,
            )

        # TODO: Remove and use the assert_player_has_poke_balls when RSE safari auto catch is implemented
        # Shuckle catch rate is 35%. So 10 balls should be enough to catch it
        if is_safari_map() and get_safari_balls_left() < 10:
            raise BotModeError("Cannot rock smash with less than 10 safari balls")
        else:
            assert_player_has_poke_balls()

        if get_player_avatar().map_group_and_number == MapRSE.GRANITE_CAVE_B2F and get_item_bag().number_of_repels > 0:
            mode = ask_for_choice(
                [
                    Selection("Use Repel", get_sprites_path() / "items" / "Repel.png"),
                    Selection("No Repel", get_sprites_path() / "other" / "No Repel.png"),
                ],
                window_title="Use Repel?",
            )

            if mode == "Use Repel":
                assert_save_game_exists("There is no saved game. Cannot soft reset.")
                assert_player_has_poke_balls(check_in_saved_game=True)
                assert_boxes_or_party_can_fit_pokemon(check_in_saved_game=True)
                assert_saved_on_map(
                    SavedMapLocation(MapRSE.GRANITE_CAVE_B2F),
                    "In order to use Repel, you need to save on this map.",
                )

                save_data = get_save_data()
                party = save_data.get_party()
                first_pokemon = next((p for p in party if not p.is_egg and p.current_hp > 0), None)

                if first_pokemon is None or 16 < first_pokemon.level < 13:
                    raise BotModeError(
                        "In order to use Repel, you must have a lead Pokémon with level 13-16. "
                        "For best encounter rates, use Level 13!"
                    )

                if save_data.get_item_bag().number_of_repels == 0:
                    raise BotModeError("In your saved game, you do not have any Repels.")

                self._using_repel = True
                yield from self.reset_and_wait()

        self._using_mach_bike = get_player().registered_item == get_item_by_name("Mach Bike")

        while True:
            match get_player_avatar().map_group_and_number:
                case MapRSE.GRANITE_CAVE_B2F:
                    starting_frame = context.emulator.get_frame_count()
                    for _ in self.granite_cave():
                        # Detect reset
                        if context.emulator.get_frame_count() < starting_frame:
                            break
                        yield
                case MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE:
                    current_cash = get_player().money
                    if current_cash < 500:
                        yield from soft_reset()
                        yield from wait_for_unique_rng_value()
                        # See note in `on_battle_started()`
                        for _ in range(5 + self._duplicates_found):
                            yield
                    yield from self.enter_safari_zone()
                case MapRSE.SAFARI_ZONE_NORTHEAST:
                    self._in_safari_zone = True
                    for _ in self.safari_zone():
                        # See note in `on_battle_started()`
                        if self._should_delay_a_frame:
                            self._should_delay_a_frame = False
                            yield
                        if self._in_safari_zone:
                            yield
                        else:
                            break
                case MapRSE.SAFARI_ZONE_SOUTH | MapRSE.SAFARI_ZONE_SOUTHEAST:
                    self._in_safari_zone = True

                    def is_near_entrance_door():
                        return (
                            get_player_avatar().map_group_and_number == MapRSE.SAFARI_ZONE_SOUTH
                            and get_player_avatar().local_coordinates in ((32, 33), (32, 34))
                        )

                    if is_near_entrance_door() or (
                        get_player_avatar().map_group_and_number == MapRSE.SAFARI_ZONE_SOUTH
                        and get_global_script_context().is_active
                    ):
                        while is_near_entrance_door() or get_global_script_context().is_active:
                            yield
                        yield from wait_for_player_avatar_to_be_standing_still()

                    self._in_safari_zone = True
                    if self._using_mach_bike:
                        self._in_safari_zone = True
                        for _ in navigate_to(MapRSE.SAFARI_ZONE_NORTHEAST, (15, 7)):
                            if self._in_safari_zone:
                                yield
                            else:
                                break
                        yield from self.unmount_bicycle()
                    else:
                        for _ in navigate_to(MapRSE.SAFARI_ZONE_NORTHEAST, (12, 7)):
                            if self._in_safari_zone:
                                yield
                            else:
                                break

    @staticmethod
    @debug.track
    def reset_and_wait():
        context.emulator.reset_held_buttons()
        yield from soft_reset()
        yield from wait_for_unique_rng_value()
        yield from wait_for_player_avatar_to_be_standing_still()

    @staticmethod
    @debug.track
    def smash(flag_name):
        if not get_event_flag(flag_name):
            if context.rom.is_rs:
                while not get_event_flag(flag_name):
                    context.emulator.press_button("A")
                    yield
            else:
                yield from wait_for_script_to_start_and_finish("EventScript_RockSmash", "A")
            while get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING:
                yield
            if task_is_active("Task_ReturnToFieldNoScript"):
                yield from wait_until_task_is_not_active("Task_ReturnToFieldNoScript")
            if task_is_active("Task_ExitNonDoor"):
                yield from wait_until_task_is_not_active("Task_ExitNonDoor")
        yield

    @debug.track
    def mount_bicycle(self) -> Generator:
        while AvatarFlags.OnMachBike not in get_player_avatar().flags:
            context.emulator.press_button("Select")
            yield
        yield

    @debug.track
    def unmount_bicycle(self) -> Generator:
        while AvatarFlags.OnMachBike in get_player_avatar().flags:
            context.emulator.press_button("Select")
            yield
        yield

    @debug.track
    def granite_cave(self) -> Generator:
        if self._using_repel and not repel_is_active():
            with contextlib.suppress(RanOutOfRepels):
                yield from apply_repel()

        if self._using_mach_bike:
            yield from self.mount_bicycle()
        yield from navigate_to(MapRSE.GRANITE_CAVE_B2F, (7, 22))
        if self._using_mach_bike:
            yield from self.unmount_bicycle()

        # With Repel active, White Flute boosts encounters by 30-40%, but without Repel it
        # actually _decreases_ encounter rates (due to so many regular encounters popping up
        # while walking around.) So we only enable White Flute if Repel is also active.
        if self._using_repel:
            yield from apply_white_flute_if_available()
        yield from ensure_facing_direction("Left")
        yield from self.smash("TEMP_16")

        yield from follow_path([(7, 21), (4, 21)])
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

        if self._using_mach_bike:
            yield from self.mount_bicycle()
        yield from navigate_to(MapRSE.GRANITE_CAVE_B2F, (29, 13))

        if self._using_mach_bike:
            yield from self.unmount_bicycle()
        yield from walk_one_tile("Up")
        yield from walk_one_tile("Down")

        if self._using_mach_bike:
            yield from self.mount_bicycle()
        yield from navigate_to(MapRSE.GRANITE_CAVE_B2F, (7, 13))
        yield from ensure_facing_direction("Up")

        if self._using_mach_bike:
            yield from self.unmount_bicycle()
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

        if self._using_mach_bike:
            yield from self.mount_bicycle()
        yield from navigate_to(MapRSE.GRANITE_CAVE_B2F, (28, 21))
        yield from wait_for_player_avatar_to_be_standing_still()

        if self._using_mach_bike:
            yield from self.unmount_bicycle()
        yield from walk_one_tile("Down")
        yield from walk_one_tile("Up")

    @debug.track
    def enter_safari_zone(self):
        if get_player().money < 500:
            raise BotModeError("You do not have enough cash to re-enter the Safari Zone.")
        yield from navigate_to(MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE, (9, 4))
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

    @debug.track
    def safari_zone(self):
        yield from navigate_to(MapRSE.SAFARI_ZONE_NORTHEAST, (12, 7))
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

        # This mode is only available on Emerald anyway. I'm still leaving the symbol name for R/S
        # and FR/LG in here though, in case someone wants to copy/paste this at some point.
        steps_remaining_symbol = "sSafariZoneStepCounter" if context.rom.is_emerald else "gSafariZoneStepCounter"
        steps_remaining = unpack_uint16(read_symbol(steps_remaining_symbol))
        if steps_remaining < 161:
            yield from leave_safari_zone()
            self._in_safari_zone = False
            return

        if self._using_mach_bike:
            yield from self.mount_bicycle()

            def bike_waypoints():
                point_a = (MapRSE.SAFARI_ZONE_SOUTHEAST, (8, 0))
                point_b = (MapRSE.SAFARI_ZONE_SOUTHEAST, (7, 0))
                point_c = (MapRSE.SAFARI_ZONE_NORTHEAST, (15, 7))

                yield from calculate_path(get_player_location(), point_a)
                yield from calculate_path(point_a, point_b)
                yield from calculate_path(point_b, point_c)

            yield from follow_waypoints(bike_waypoints())
            yield from self.unmount_bicycle()
        else:
            yield from navigate_to(MapRSE.SAFARI_ZONE_SOUTHEAST, (8, 0))
