from typing import Generator

from modules.data.map import MapRSE
from modules.console import console
from modules.context import context
from modules.daycare import DaycareCompatibility, get_daycare_data
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon import get_party
from ._asserts import (
    assert_registered_item,
)
from ._interface import BotMode, BotModeError
from ._util import (
    follow_path,
    wait_until_task_is_active,
    wait_for_task_to_start_and_finish,
    wait_for_n_frames,
)


def _get_targeted_encounter() -> tuple[tuple[int, int], tuple[int, int], str] | None:
    if context.rom.is_rse:
        encounters = [
            (MapRSE.ROUTE_117.value, (47, 6), "Daycare"),
        ]
    else:
        encounters = []

    targeted_tile = get_player_avatar().map_location_in_front
    for entry in encounters:
        if entry[0] == (targeted_tile.map_group, targeted_tile.map_number) and entry[1] == targeted_tile.local_position:
            return entry

    return None


class DaycareMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Daycare"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    @staticmethod
    def disable_default_battle_handler() -> bool:
        return True

    def run(self) -> Generator:
        self.navigator = None

        assert_registered_item(
            ["Mach Bike"],
            "You need to register the Mach Bike for the Select button.",
        )

        if get_daycare_data().compatibility[0] == DaycareCompatibility.Incompatible:
            raise BotModeError(
                f"The Pokemon in the daycare are not compatible. \n{get_daycare_data().compatibility[1]}."
            )
        if get_daycare_data().compatibility[0] == DaycareCompatibility.Low:
            console.print("[bold yellow]WARNING: Low compatibility between daycare pokemon.")
            console.print(f"[bold yellow]{get_daycare_data().compatibility[1]}")
            console.print("[bold yellow]Egg generation rates may be affected.")

        if get_party()[0].ability.name not in ["Flame Body", "Magma Armor"]:
            console.print(
                "[bold yellow]WARNING: First Pokemon in party does not have Flame Body / Magma Armor ability."
            )
            console.print("[bold yellow]This will slow down the egg hatching process.")

        def egg_in_party() -> int:
            total_eggs = 0
            for pokemon in get_party():
                if pokemon.is_egg:
                    total_eggs += 1
            return total_eggs

        def handle_egg_collecting():
            daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")
            while daycare_egg_ready:
                if get_player_avatar().is_on_bike:
                    context.emulator.press_button("Select")
                # navigate back to daycare man on R117
                yield from follow_path([(47, 8), (47, 7)], False)
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
                yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "A")
                yield from wait_for_task_to_start_and_finish("Task_Fanfare")
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "B")
                # loop until egg is received - necessary as extra dialogue without a task is active
                while daycare_egg_ready:
                    daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")
                    context.emulator.press_button("B")
                    yield from wait_for_n_frames(5)
                break

        def handle_movement(message: str):
            if not get_player_avatar().is_on_bike:
                context.emulator.press_button("Select")
            if len(get_party()) == 6:
                context.message = message + " then releasing..."
            else:
                context.message = message
            # TODO: Replace this with better navigation once pathing update goes live
            yield from follow_path([(47, 8), (30, 8), (20, 8), (10, 8), (3, 8)], False)
            yield from follow_path([(10, 8), (20, 8), (30, 8), (40, 8), (50, 8), (56, 8)], False)

        def pc_release(pokemon: str):
            from modules.stats import total_stats

            if get_player_avatar().is_on_bike:
                context.emulator.press_button("Select")
            # enter daycare
            yield from follow_path([(51, 8), (51, 6)])
            if get_player_avatar().local_coordinates[0] == 51 and get_player_avatar().local_coordinates[1] == 6:
                while get_player_avatar().local_coordinates[1] != 5:
                    context.emulator.press_button("Up")
                    yield from wait_for_n_frames(5)
            # move to PC
            yield from wait_for_task_to_start_and_finish("Task_ExitNonDoor")
            yield from wait_for_n_frames(60)
            yield from follow_path([(2, 4), (10, 4), (10, 2)])
            # interact with PC
            yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
            yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
            yield from wait_for_task_to_start_and_finish("Task_HandleMultichoiceInput", "A")
            yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
            yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")
            yield from wait_until_task_is_active("Task_PCMainMenu", "A")
            yield from wait_for_n_frames(30)
            for _ in range(2):
                context.emulator.press_button("Down")
                yield from wait_for_n_frames(5)
            yield from wait_until_task_is_active("Task_PokeStorageMain", "A")
            # navigate to party list
            yield from wait_for_n_frames(30)
            for _ in range(2):
                context.emulator.press_button("Up")
                yield from wait_for_n_frames(8)
            context.emulator.press_button("A")
            yield from wait_for_n_frames(60)
            context.emulator.press_button("Right")
            yield from wait_for_n_frames(8)
            # release 5 baby pokemon
            for _ in range(5):
                yield from wait_until_task_is_active("Task_OnSelectedMon", "A")
                yield from wait_for_n_frames(20)
                for _ in range(2):
                    context.emulator.press_button("Up")
                    yield from wait_for_n_frames(10)
                context.emulator.press_button("A")
                yield from wait_until_task_is_active("Task_ReleaseMon")
                context.emulator.press_button("Up")
                yield from wait_for_n_frames(10)
                context.emulator.press_button("A")
                yield from wait_until_task_is_active("Task_PokeStorageMain", "A")

            # leave daycare
            context.emulator.press_button("B")
            yield from wait_for_n_frames(20)
            context.emulator.press_button("B")
            yield from wait_for_task_to_start_and_finish("Task_HandleMultichoiceInput", "B")
            yield from wait_for_n_frames(20)
            yield from follow_path([(10, 4), (3, 4), (3, 8)])
            if get_player_avatar().local_coordinates[0] == 3 and get_player_avatar().local_coordinates[1] == 8:
                while get_player_avatar().local_coordinates[1] != 7:
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)

        while context.bot_mode != "Manual":
            daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")

            # if daycare does not have an egg, and you dont have one in party, run until one is created
            while not daycare_egg_ready and egg_in_party() == 0:
                daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")
                yield from handle_movement("Waiting for the Daycare to have an egg...")

            # check party size and release if full
            party_size = len(get_party())
            if party_size == 6 and egg_in_party() == 0:
                pokemon_hunting = get_party()[party_size - 1].species.name
                yield from pc_release(pokemon_hunting)
                yield from follow_path([(51, 8), (47, 8)])

            # collect eggs from daycare as soon as they are ready
            while daycare_egg_ready and party_size < 6:
                yield from handle_egg_collecting()
                break

            # if you have an egg, hatch it
            while egg_in_party() > 0:
                egg_count = egg_in_party()
                yield from handle_movement("Hatching " + str(egg_count) + " eggs...")
                break
