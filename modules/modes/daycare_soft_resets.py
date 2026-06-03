import os
import time
from typing import Generator

from modules.console import console
from modules.context import context
from modules.battle_state import EncounterType
from modules.encounter import EncounterInfo, handle_encounter
from modules.map_data import MapFRLG, MapRSE
from modules.map_path import calculate_path
from modules.memory import GameState, get_event_flag, get_game_state
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player, get_player_avatar
from modules.pokemon_party import get_party, get_party_size
from modules.save_data import get_save_data
from ._asserts import assert_empty_slot_in_party, assert_save_game_exists
from ._interface import BotMode, BotModeError
from .util import (
    follow_waypoints,
    navigate_to,
    soft_reset,
    wait_for_player_avatar_to_be_controllable,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_until_task_is_active,
    wait_until_task_is_not_active,
    wait_for_unique_rng_value,
)


class DaycareSoftResetsMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Daycare Soft Resets"

    @staticmethod
    def is_selectable() -> bool:
        if get_game_state() != GameState.OVERWORLD:
            return False

        player_map = get_player_avatar().map_group_and_number
        if context.rom.is_rse:
            return player_map == MapRSE.ROUTE117
        return player_map == MapFRLG.FOUR_ISLAND

    def __init__(self):
        super().__init__()
        self._egg_has_hatched = False
        self._target_party_index: int | None = None

    def on_egg_hatched(self, encounter: "EncounterInfo", party_index: int) -> bool | None:
        if party_index == self._target_party_index:
            self._egg_has_hatched = True
            return True
        return None

    def run(self) -> Generator:
        context.emulation_speed = 0

        if context.rom.is_emerald:
            daycare_route = MapRSE.ROUTE117
            message_box_task = "Task_DrawFieldMessage"
            yes_no_task = "Task_HandleYesNoInput"
        elif context.rom.is_rs:
            daycare_route = MapRSE.ROUTE117
            message_box_task = "Task_FieldMessageBox"
            yes_no_task = "Task_HandleYesNoInput"
        else:
            daycare_route = MapFRLG.FOUR_ISLAND
            message_box_task = "Task_DrawFieldMessageBox"
            yes_no_task = "Task_YesNoMenu_HandleInput"

        def get_shiny_egg_party_index() -> int | None:
            for index, pokemon in enumerate(get_party()):
                if pokemon.is_egg and pokemon.is_shiny:
                    return index
            return None

        shiny_egg_party_index_at_start = get_shiny_egg_party_index()

        assert_save_game_exists("There is no saved game. Cannot soft reset for daycare eggs.")
        if shiny_egg_party_index_at_start is None:
            assert_empty_slot_in_party(
                "This mode requires at least one empty party slot in the saved game.",
                check_in_saved_game=True,
            )

        save_data = get_save_data()
        if save_data.get_map_group_and_number() != daycare_route.value and shiny_egg_party_index_at_start is None:
            raise BotModeError("Save in front of the Daycare man before using this mode.")
        if not save_data.get_event_flag("PENDING_DAYCARE_EGG") and shiny_egg_party_index_at_start is None:
            raise BotModeError("Save in front of the Daycare man after he has an egg ready.")

        def registered_item_is_bike() -> bool:
            registered_item = get_player().registered_item
            return registered_item is not None and registered_item.name in ("Mach Bike", "Acro Bike", "Bicycle")

        def collect_egg() -> Generator:
            daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")
            if not daycare_egg_ready:
                raise BotModeError("The Daycare man does not have an egg ready.")

            if get_player_avatar().is_on_bike:
                context.emulator.press_button("Select")
                yield
                yield

            context.emulator.press_button("A")
            yield
            yield from wait_until_task_is_active(message_box_task, "A")
            yield from wait_until_task_is_not_active(message_box_task, "B")
            yield from wait_for_task_to_start_and_finish(yes_no_task, "A")
            yield from wait_for_task_to_start_and_finish("Task_Fanfare", "B")
            yield from wait_for_task_to_start_and_finish(message_box_task, "B")

            while get_event_flag("PENDING_DAYCARE_EGG"):
                context.emulator.press_button("B")
                yield from wait_for_n_frames(5)

        def hatch_egg() -> Generator:
            if context.rom.is_rse:
                point_a = (MapRSE.ROUTE117, (47, 7))
                point_b = (MapRSE.ROUTE117, (47, 8))
                point_c = (MapRSE.ROUTE117, (55, 8))
                point_d = (MapRSE.ROUTE117, (55, 7))
            else:
                point_a = (MapFRLG.FOUR_ISLAND, (12, 15))
                point_b = (MapFRLG.FOUR_ISLAND, (12, 16))
                point_c = (MapFRLG.FOUR_ISLAND, (16, 16))
                point_d = (MapFRLG.FOUR_ISLAND, (16, 15))

            from_a_to_b = calculate_path(point_a, point_b)
            from_b_to_c = calculate_path(point_b, point_c)
            from_c_to_d = calculate_path(point_c, point_d)
            from_d_to_a = calculate_path(point_d, point_a)

            yield from wait_for_player_avatar_to_be_controllable("B")
            yield from navigate_to(*point_a)
            if not get_player_avatar().is_on_bike and registered_item_is_bike():
                context.emulator.press_button("Select")
                yield
                yield

            def hatching_path() -> Generator:
                while True:
                    yield from from_a_to_b
                    yield from from_b_to_c
                    yield from from_c_to_d
                    yield from from_d_to_a

            self._egg_has_hatched = False
            for _ in follow_waypoints(hatching_path()):
                if self._egg_has_hatched:
                    break
                yield
            context.emulator.reset_held_buttons()

        def open_hatched_pokemon_summary() -> Generator:
            if self._target_party_index is None:
                return

            yield from wait_for_player_avatar_to_be_controllable("B")
            context.message = f"Opening shiny {get_party()[self._target_party_index].species.name} summary..."
            yield from StartMenuNavigator("POKEMON").step()
            yield from PokemonPartyMenuNavigator(self._target_party_index, "summary").step()

        timing_enabled = os.getenv("POKEBOT_DAYCARE_SR_TIMING") == "1"
        timing_attempts = 0
        timing_totals = {
            "soft_reset": 0.0,
            "unique_rng": 0.0,
            "collect_egg": 0.0,
            "party_wait": 0.0,
            "handle_encounter": 0.0,
        }

        def add_timing(step: str, started_at: float) -> None:
            if timing_enabled:
                timing_totals[step] += time.perf_counter() - started_at

        shiny_egg_party_index = get_shiny_egg_party_index()
        if shiny_egg_party_index is not None:
            self._target_party_index = shiny_egg_party_index
            egg = get_party()[self._target_party_index]
            console.print(f"[bold yellow]Shiny {egg.species.name} egg is already in the party. Hatching it now.[/]")
            context.message = f"Shiny {egg.species.name} egg found! Hatching..."
            yield from hatch_egg()
            yield from open_hatched_pokemon_summary()
            if context.bot_mode != "Manual":
                context.set_manual_mode()
            return

        while context.bot_mode != "Manual":
            context.message = "Soft resetting for a shiny daycare egg..."
            self._target_party_index = None

            step_started_at = time.perf_counter()
            yield from soft_reset(mash_random_keys=True)
            add_timing("soft_reset", step_started_at)

            step_started_at = time.perf_counter()
            yield from wait_for_unique_rng_value()
            add_timing("unique_rng", step_started_at)

            starting_party_size = get_party_size()
            step_started_at = time.perf_counter()
            yield from collect_egg()
            add_timing("collect_egg", step_started_at)

            step_started_at = time.perf_counter()
            while get_party_size() <= starting_party_size:
                yield
            add_timing("party_wait", step_started_at)

            self._target_party_index = starting_party_size
            egg = get_party()[self._target_party_index]
            step_started_at = time.perf_counter()
            active_bot_mode = context.bot_mode
            handle_encounter(
                EncounterInfo.create(egg, EncounterType.Hatched),
                disable_auto_catch=True,
                do_not_switch_to_manual=True,
            )
            if egg.is_shiny and context.bot_mode == "Manual":
                context.bot_mode = active_bot_mode
            add_timing("handle_encounter", step_started_at)
            if timing_enabled:
                timing_attempts += 1
                if timing_attempts % 10 == 0:
                    averages = " | ".join(
                        f"{step}: {timing_totals[step] / timing_attempts:.2f}s" for step in timing_totals
                    )
                    console.print(f"[cyan]Daycare SR timing after {timing_attempts} eggs:[/] {averages}")
            if not egg.is_shiny:
                context.message = f"{egg.species.name} egg is not shiny. Soft resetting..."
                yield
                continue

            console.print(f"[bold yellow]Shiny {egg.species.name} egg found! Hatching it now.[/]")
            context.message = f"Shiny {egg.species.name} egg found! Hatching..."
            yield from hatch_egg()
            yield from open_hatched_pokemon_summary()
            if context.bot_mode != "Manual":
                context.set_manual_mode()
            break
