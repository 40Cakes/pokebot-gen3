from typing import Generator

from modules.console import console
from modules.context import context
from modules.daycare import DaycareCompatibility, get_daycare_data
from modules.encounter import judge_encounter
from modules.items import get_item_bag, get_item_by_name, get_item_storage
from modules.map import get_map_objects
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_event_flag, get_game_state, get_game_state_symbol
from modules.player import get_player_avatar
from modules.pokemon import Pokemon, get_eggs_in_party, get_party
from modules.tasks import get_global_script_context, task_is_active
from ._interface import BotMode, BotModeError
from .util import (
    ensure_facing_direction,
    follow_path,
    deprecated_navigate_to_on_current_map,
    register_key_item,
    wait_for_player_avatar_to_be_controllable,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_until_task_is_active,
    walk_one_tile,
)


def _update_message():
    party_size = len(get_party())
    egg_count = get_eggs_in_party()
    if egg_count == 0 and party_size == 6:
        context.message = "Releasing..."
    elif egg_count == 0 and not get_event_flag("PENDING_DAYCARE_EGG"):
        context.message = "Waiting for the Daycare to have an egg..."
    elif party_size < 6:
        context.message = f"Hatching {egg_count} eggs..."
    else:
        context.message = f"Hatching {egg_count} eggs, then releasing..."


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
            return player_map == MapRSE.ROUTE117
        else:
            return player_map == MapFRLG.FOUR_ISLAND

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
        elif context.rom.is_rse:
            if (
                get_item_storage().quantity_of(get_item_by_name("Mach Bike")) > 0
                or get_item_storage().quantity_of(get_item_by_name("Acro Bike")) > 0
            ):
                raise BotModeError("Your bicycle is stored in the PC storage system. Please go and get it.")

            # Get the Mach Bike in Mauville City
            yield from deprecated_navigate_to_on_current_map(59, 8)
            yield from walk_one_tile("Right")

            # Go to bike shop and walk up to the guy
            yield from deprecated_navigate_to_on_current_map(35, 6)
            yield from walk_one_tile("Up")
            yield from deprecated_navigate_to_on_current_map(3, 5)
            yield from ensure_facing_direction("Left")

            # Talk to him. If the player didn't have any bike, the first option will be
            # the Mach Bike, and if they already have the Acro Bike it will just switch
            # it, so spamming A works either way.
            context.emulator.press_button("A")
            yield
            while get_global_script_context().is_active:
                context.emulator.press_button("A")
                yield
            yield

            # Go outside, and back to Route 117
            yield from deprecated_navigate_to_on_current_map(3, 8)
            yield from walk_one_tile("Down")
            yield from deprecated_navigate_to_on_current_map(0, 8)
            yield from walk_one_tile("Left")

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

        def pc_release():
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

            if not party_indices_to_release:
                context.message = "There are no more empty slots in your party!"
                context.set_manual_mode()

            if get_player_avatar().is_on_bike:
                context.emulator.press_button("Select")

            # Enter daycare
            yield from follow_path([daycare_house, daycare_door])
            yield from walk_one_tile("Up")
            # move to PC
            yield from deprecated_navigate_to_on_current_map(10, 2)
            yield from ensure_facing_direction("Up")

            # Interact with PC
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

            # Navigate to party list
            yield from wait_for_n_frames(50)
            for _ in range(2):
                context.emulator.press_button("Up")
                yield from wait_for_n_frames(10)
            context.emulator.press_button("A")
            yield from wait_for_n_frames(60)

            # Release 5 baby Pokémon
            for index in range(len(get_party())):
                if index not in party_indices_to_release:
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(20)
                else:
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    for _ in range(2):
                        yield from wait_for_n_frames(10)
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

            # Leave daycare
            yield from wait_for_player_avatar_to_be_controllable("B")

            yield from deprecated_navigate_to_on_current_map(*daycare_exit)
            yield from walk_one_tile("Down")

        def get_path():
            path_index = -1
            while True:
                if self._update_message_soon:
                    self._update_message_soon = False
                    _update_message()

                party_size = len(get_party())
                if get_event_flag("PENDING_DAYCARE_EGG") and party_size < 6:
                    yield daycare_man
                    break
                elif party_size == 6 and get_eggs_in_party() == 0:
                    yield daycare_house
                    break
                else:
                    path_index = (path_index + 1) % len(path)
                    yield path[path_index]

        if get_player_avatar().is_on_bike:
            context.emulator.press_button("Select")
            yield
            yield
        yield from deprecated_navigate_to_on_current_map(*daycare_man)
        while context.bot_mode != "Manual":
            self._update_message_soon = True

            if not get_player_avatar().is_on_bike and self._use_bike:
                context.emulator.press_button("Select")
                yield

            yield from follow_path(get_path())

            if get_eggs_in_party() == 0 and len(get_party()) == 6:
                yield from pc_release()
                yield from follow_path([daycare_house])

            if get_event_flag("PENDING_DAYCARE_EGG") and len(get_party()) < 6:
                yield from handle_egg_collecting()
                yield from follow_path([daycare_man])
