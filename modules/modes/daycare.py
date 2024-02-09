from typing import Generator

from modules.data.map import MapRSE, MapFRLG

from modules.console import console
from modules.context import context
from modules.daycare import DaycareCompatibility, get_daycare_data
from modules.encounter import judge_encounter
from modules.items import get_item_bag, get_item_by_name
from modules.map import get_map_objects
from modules.memory import get_event_flag, get_game_state_symbol, get_game_state, GameState
from modules.player import get_player_avatar
from modules.pokemon import get_party, Pokemon
from modules.tasks import task_is_active
from ._interface import BotMode, BotModeError
from ._util import (
    walk_one_tile,
    follow_path,
    navigate_to,
    ensure_facing_direction,
    register_key_item,
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
        if get_game_state() != GameState.OVERWORLD:
            return False

        player_map = get_player_avatar().map_group_and_number
        if context.rom.is_rse:
            return player_map == MapRSE.ROUTE_117.value
        else:
            return player_map == MapFRLG.FOUR_ISLAND.value

    def __init__(self):
        super().__init__()
        self._use_bike = False
        self._update_message_soon = False

    def on_egg_hatched(self, pokemon: "Pokemon", party_index: int) -> None:
        self._update_message_soon = True

    def run(self) -> Generator:
        if context.rom.is_emerald:
            path = ((0, 8), (59, 8))
            daycare_man_map_object_id = 3
            daycare_man = (47, 8)
            daycare_house = (51, 8)
            daycare_door = (51, 6)
            daycare_exit = (3, 8)
            message_box_task = "Task_DrawFieldMessage"
            yes_no_task = "Task_HandleYesNoInput"
        elif context.rom.is_rs:
            path = ((15, 8), (59, 8))
            daycare_man_map_object_id = 3
            daycare_man = (47, 8)
            daycare_house = (51, 8)
            daycare_door = (51, 6)
            daycare_exit = (3, 8)
            message_box_task = "Task_FieldMessageBox"
            yes_no_task = "Task_HandleYesNoInput"
        else:
            path = ((9, 15), (28, 15))
            daycare_man_map_object_id = 1
            daycare_man = (16, 15)
            daycare_house = (12, 15)
            daycare_door = (12, 14)
            daycare_exit = (4, 7)
            message_box_task = "Task_DrawFieldMessageBox"
            yes_no_task = "Task_YesNoMenu_HandleInput"

        if get_daycare_data().compatibility[0] == DaycareCompatibility.Incompatible:
            raise BotModeError(
                f"The Pokemon in the daycare are not compatible. \n{get_daycare_data().compatibility[1]}."
            )
        if get_daycare_data().compatibility[0] == DaycareCompatibility.Low:
            console.print("[bold yellow]WARNING: Low compatibility between daycare pokemon.")
            console.print(f"[bold yellow]{get_daycare_data().compatibility[1]}")
            console.print("[bold yellow]Egg generation rates may be affected.")

        if context.rom.is_emerald and get_party()[0].ability.name not in ["Flame Body", "Magma Armor"]:
            console.print(
                "[bold yellow]WARNING: First Pokemon in party does not have Flame Body / Magma Armor ability."
            )
            console.print("[bold yellow]This will slow down the egg hatching process.")

        item_bag = get_item_bag()
        if item_bag.quantity_of(get_item_by_name("Mach Bike")) > 0:
            yield from register_key_item(get_item_by_name("Mach Bike"))
            self._use_bike = True
        elif item_bag.quantity_of(get_item_by_name("Bicycle")) > 0:
            yield from register_key_item(get_item_by_name("Bicycle"))
            self._use_bike = True
        elif item_bag.quantity_of(get_item_by_name("Acro Bike")) > 0:
            console.print("[bold yellow]WARNING: You do not have the Mach Bike, so we will just be running.")
            console.print("[bold yellow]This will slow down the egg hatching process.")
        else:
            console.print("[bold yellow]WARNING: You do not have a bicycle, so we will just be running.")
            console.print("[bold yellow]This will slow down the egg hatching process.")

        def handle_egg_collecting():
            daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")
            while daycare_egg_ready:
                if get_player_avatar().is_on_bike:
                    context.emulator.press_button("Select")
                x, y = 0, 0
                for map_object in get_map_objects():
                    if map_object.local_id == daycare_man_map_object_id:
                        x, y = map_object.current_coords
                        break
                if x == 0 or y == 0:
                    raise BotModeError("Could not find Daycare Man")
                # navigate back to daycare man on R117
                yield from follow_path([daycare_man, (x, y + 1)])
                yield from ensure_facing_direction("Up")
                yield from wait_for_task_to_start_and_finish(message_box_task, "A")
                yield from wait_for_task_to_start_and_finish(yes_no_task, "A")
                yield from wait_for_task_to_start_and_finish("Task_Fanfare")
                yield from wait_for_task_to_start_and_finish(message_box_task, "B")
                # loop until egg is received - necessary as extra dialogue without a task is active
                while daycare_egg_ready:
                    daycare_egg_ready = get_event_flag("PENDING_DAYCARE_EGG")
                    context.emulator.press_button("B")
                    yield from wait_for_n_frames(5)
                break

        def pc_release(pokemon: str):
            party_indices_to_release = []
            for index in range(len(get_party())):
                pokemon = get_party()[index]
                if (
                    index != 0
                    and not pokemon.is_egg
                    and pokemon.level_met == 0
                    and pokemon.level == 5
                    and pokemon.exp_fraction_to_next_level == 0
                    and not judge_encounter(pokemon).is_of_interest
                ):
                    party_indices_to_release.append(index)

            if len(party_indices_to_release) == 0:
                context.message = "There are no more empty slots in your party!"
                context.set_manual_mode()

            if get_player_avatar().is_on_bike:
                context.emulator.press_button("Select")
            # enter daycare
            yield from follow_path([daycare_house, daycare_door])
            yield from walk_one_tile("Up")
            # move to PC
            yield from navigate_to(10, 2)
            yield from ensure_facing_direction("Up")
            # interact with PC
            if context.rom.is_rs:
                yield from wait_until_task_is_active("Task_PokemonStorageSystem", "A")
            else:
                yield from wait_until_task_is_active("Task_PCMainMenu", "A")
            yield from wait_for_n_frames(8)
            for _ in range(2):
                context.emulator.press_button("Down")
                yield from wait_for_n_frames(5)
            while not task_is_active("Task_PokeStorageMain") and get_game_state_symbol() != "SUB_8096B38":
                context.emulator.press_button("A")
                yield
            # navigate to party list
            yield from wait_for_n_frames(50)
            for _ in range(2):
                context.emulator.press_button("Up")
                yield from wait_for_n_frames(10)
            context.emulator.press_button("A")
            yield from wait_for_n_frames(60)
            # release 5 baby pokemon
            for index in range(len(get_party())):
                if index not in party_indices_to_release:
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(20)
                else:
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(7)
                    for _ in range(2):
                        context.emulator.press_button("Up")
                        yield from wait_for_n_frames(2)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(4)
                    context.emulator.press_button("Up")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("A")
                    party_size_before = len(get_party())
                    while len(get_party()) == party_size_before:
                        yield from wait_for_n_frames(10)
                    for _ in range(2):
                        yield from wait_for_n_frames(3)
                        context.emulator.press_button("A")
                    yield from wait_for_n_frames(20)

            # leave daycare
            while get_game_state() != GameState.OVERWORLD or "heldMovementActive" not in get_map_objects()[0].flags:
                context.emulator.press_button("B")
                yield

            yield from navigate_to(*daycare_exit)
            yield from walk_one_tile("Down")

        def get_path():
            path_index = -1
            while True:
                if self._update_message_soon:
                    self._update_message_soon = False
                    self._update_message()

                party_size = len(get_party())
                if get_event_flag("PENDING_DAYCARE_EGG") and party_size < 6:
                    yield daycare_man
                    break
                elif party_size == 6 and self.egg_in_party() == 0:
                    yield daycare_house
                    break
                else:
                    path_index = (path_index + 1) % len(path)
                    yield path[path_index]

        if get_player_avatar().is_on_bike:
            context.emulator.press_button("Select")
            yield
            yield
        yield from navigate_to(*daycare_man)
        while context.bot_mode != "Manual":
            self._update_message_soon = True

            if not get_player_avatar().is_on_bike and self._use_bike:
                context.emulator.press_button("Select")
                yield

            yield from follow_path(get_path())

            if self.egg_in_party() == 0 and len(get_party()) == 6:
                pokemon_hunting = get_party()[len(get_party()) - 1].species.name
                yield from pc_release(pokemon_hunting)
                yield from follow_path([daycare_house])

            if get_event_flag("PENDING_DAYCARE_EGG") and len(get_party()) < 6:
                yield from handle_egg_collecting()
                yield from follow_path([daycare_man])

    def egg_in_party(self) -> int:
        total_eggs = 0
        for pokemon in get_party():
            if pokemon.is_egg:
                total_eggs += 1
        return total_eggs

    def _update_message(self):
        party_size = len(get_party())
        egg_count = self.egg_in_party()
        if egg_count == 0 and party_size == 6:
            context.message = "Releasing..."
        elif egg_count == 0 and not get_event_flag("PENDING_DAYCARE_EGG"):
            context.message = "Waiting for the Daycare to have an egg..."
        elif party_size < 6:
            context.message = f"Hatching {egg_count} eggs..."
        else:
            context.message = f"Hatching {egg_count} eggs, then releasing..."
