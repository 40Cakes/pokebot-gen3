from typing import Generator

from modules.context import context
from modules.items import get_item_bag
from modules.map import get_map_objects
from modules.map_data import MapFRLG, MapRSE
from modules.memory import get_event_flag, get_event_var, read_symbol, unpack_uint16
from modules.menuing import StartMenuNavigator, use_party_hm_move
from modules.player import get_player_avatar
from modules.save_data import get_save_data
from modules.tasks import get_global_script_context
from ._asserts import assert_no_auto_battle, assert_no_auto_pickup, assert_registered_item, assert_has_pokemon_with_move
from ._interface import BotMode, BotModeError
from ._util import (
    wait_for_task_to_start_and_finish,
    navigate_to,
    walk_one_tile,
    follow_path,
    wait_until_task_is_active,
    wait_for_n_frames,
    wait_for_script_to_start_and_finish,
)


class PuzzleSolverMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Puzzle Solver"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            return get_player_avatar().map_group_and_number in [
                MapRSE.SKY_PILLAR_OUTSIDE,
                MapRSE.ISLAND_CAVE,
                MapRSE.DESERT_RUINS,
                MapRSE.ANCIENT_TOMB,
                MapRSE.BIRTH_ISLAND_EXTERIOR,
                MapRSE.MIRAGE_TOWER_1F,
            ]
        elif context.rom.is_frlg:
            return get_player_avatar().map_group_and_number in [
                MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY,
            ]
        else:
            return False

    def run(self) -> Generator:
        assert_no_auto_battle("This mode should not be used with auto-battle.")
        assert_no_auto_pickup("This mode should not be used while auto-pickup is enabled.")
        useRepel = False

        match get_player_avatar().map_group_and_number:
            # Mirage Tower
            case MapRSE.MIRAGE_TOWER_1F:
                context.message = "Solving Mirage Tower..."
                useRepel = True
                assert_registered_item("Mach Bike", "This mode requires the Mach Bike.")
                assert_has_pokemon_with_move("Rock Smash", "This mode requires Pokémon with Rock Smash.")

                def path():
                    # floor 1
                    yield from follow_path([(10, 13), (4, 13), (4, 2), (15, 2)])
                    # floor 2
                    yield from wait_for_task_to_start_and_finish("Task_ExitNonDoor")
                    while not get_player_avatar().is_on_bike:
                        context.emulator.press_button("Select")
                        yield
                    yield from follow_path(
                        [(6, 2), (6, 4), (2, 4), (2, 11), (4, 11), (4, 14), (16, 14), (16, 12), (18, 12)]
                    )
                    # floor 3
                    yield from wait_for_task_to_start_and_finish("Task_ExitNonDoor")
                    while get_player_avatar().is_on_bike:
                        context.emulator.press_button("Select")
                        yield
                    yield from follow_path([(15, 12), (15, 14), (14, 14), (4, 9), (3, 9), (3, 8)])
                    yield from use_party_hm_move("Rock Smash")
                    yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                    yield from follow_path([(3, 4), (2, 4)])
                    yield from wait_for_task_to_start_and_finish("Task_ExitNonDoor")
                    yield from wait_for_n_frames(10)
                    yield from follow_path([(2, 4), (2, 7), (5, 7)])
                    yield from use_party_hm_move("Rock Smash")
                    yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                    yield from wait_for_n_frames(180)
                    yield from navigate_to(6, 6)
                    if get_player_avatar().local_coordinates == (6, 6):
                        context.message = "Mirage Tower puzzle complete!"
                        context.bot_mode = "Manual"

            # Sky Pillar
            case MapRSE.SKY_PILLAR_OUTSIDE:
                context.message = "Solving Sky Pillar..."
                useRepel = True
                assert_registered_item("Mach Bike", "This mode requires the Mach Bike.")

                def path():
                    yield from walk_one_tile("Up")
                    # floor 1
                    yield from follow_path(
                        [(1, 13), (1, 8), (3, 8), (3, 4), (2, 4), (2, 2), (6, 2), (6, 4), (10, 4), (10, 2)]
                    )
                    yield from walk_one_tile("Up")
                    # floor 2
                    while not get_player_avatar().is_on_bike:
                        context.emulator.press_button("Select")
                        yield
                    yield from follow_path([(11, 2), (11, 13), (0, 13), (0, 7), (3, 7), (3, 2)])
                    yield from walk_one_tile("Up")
                    # floor 3
                    while get_player_avatar().is_on_bike:
                        context.emulator.press_button("Select")
                        yield
                    yield from follow_path([(3, 5), (1, 5), (1, 11), (4, 11), (4, 12), (12, 12), (12, 2), (11, 2)])
                    yield from walk_one_tile("Up")
                    # floor 4
                    while not get_player_avatar().is_on_bike:
                        context.emulator.press_button("Select")
                        yield
                    yield from follow_path([(11, 8), (11, 12), (3, 12), (3, 4), (6, 4), (8, 4), (7, 4), (7, 2)])
                    yield from walk_one_tile("Up")
                    yield from navigate_to(7, 2)
                    yield from walk_one_tile("Up")
                    yield from navigate_to(3, 2)
                    yield from walk_one_tile("Up")
                    # floor 5
                    yield from follow_path(
                        [
                            (1, 2),
                            (1, 5),
                            (2, 5),
                            (2, 8),
                            (1, 8),
                            (1, 12),
                            (8, 12),
                            (8, 13),
                            (13, 13),
                            (13, 7),
                            (12, 7),
                            (12, 2),
                            (10, 2),
                        ]
                    )
                    yield from walk_one_tile("Up")
                    context.message = "Sky Pillar puzzle complete!"
                    context.bot_mode = "Manual"

            # Regirock
            case MapRSE.DESERT_RUINS:
                context.message = "Solving Regirock Puzzle..."

                def path():
                    yield from navigate_to(8, 21)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("B")
                    if context.rom.is_emerald:
                        assert_has_pokemon_with_move(
                            "Rock Smash", "Regirock Puzzle (Emerald) requires Pokémon with Rock Smash."
                        )
                        context.message = "Two Left, Two Down, Rock Smash..."
                        yield from follow_path([(6, 21), (6, 23)])
                        # use rock smash
                        yield from use_party_hm_move("Rock Smash")
                        yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                        if get_event_flag("SYS_REGIROCK_PUZZLE_COMPLETED"):
                            context.message = "Regirock puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")
                    if context.rom.is_rs:
                        assert_has_pokemon_with_move(
                            "Strength", "Regirock Puzzle (Ruby/Sapphire) requires Pokémon with Strength."
                        )
                        context.message = "Two Right, Two Down, Strength..."
                        yield from follow_path([(10, 21), (10, 23)])
                        yield from use_party_hm_move("Strength")
                        yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry")
                        yield from navigate_to(8, 21)
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Regirock puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Regice
            case MapRSE.ISLAND_CAVE:
                context.message = "Solving Regice Puzzle..."

                def path():
                    yield from navigate_to(8, 21)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("B")
                    if context.rom.is_emerald:
                        context.message = "Doing a lap..."
                        yield from follow_path(
                            [
                                (8, 21),
                                (4, 23),
                                (3, 23),
                                (3, 27),
                                (4, 27),
                                (4, 29),
                                (12, 29),
                                (12, 27),
                                (13, 27),
                                (13, 23),
                                (12, 23),
                                (12, 21),
                                (8, 21),
                            ]
                        )
                        if get_event_flag("SYS_BRAILLE_REGICE_COMPLETED"):
                            context.message = "Regice puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")
                    if context.rom.is_rs:
                        context.message = "Waiting 2 minutes in-game time..."
                        yield from wait_for_n_frames(7300)
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Regice puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Registeel
            case MapRSE.ANCIENT_TOMB:
                context.message = "Solving Registeel Puzzle..."

                def path():
                    yield from navigate_to(8, 21)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("B")
                    if context.rom.is_emerald:
                        assert_has_pokemon_with_move("Flash", "Registeel Puzzle (Emerald) requires Pokémon with Flash.")
                        context.message = "Using Flash..."
                        yield from navigate_to(8, 25)
                        yield from use_party_hm_move("Flash")
                        yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                        if get_event_flag("SYS_REGISTEEL_PUZZLE_COMPLETED"):
                            context.message = "Registeel puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

                    if context.rom.is_rs:
                        assert_has_pokemon_with_move(
                            "Fly", "Regirock Puzzle (Ruby/Sapphire) requires Pokémon with Fly."
                        )
                        yield from navigate_to(8, 25)
                        yield from use_party_hm_move("Fly")
                        yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry")
                        yield from navigate_to(8, 21)
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Registeel puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Deoxys
            case MapRSE.BIRTH_ISLAND_EXTERIOR:
                context.message = "Solving Deoxys Puzzle..."

                def path():
                    yield from navigate_to(15, 13)
                    context.emulator.press_button("A")
                    yield from navigate_to(11, 13)
                    context.emulator.press_button("Down")
                    yield
                    context.emulator.press_button("A")
                    yield from follow_path([(15, 13), (15, 9)])
                    context.emulator.press_button("A")
                    yield from follow_path([(19, 9), (19, 13)])
                    context.emulator.press_button("A")
                    yield from follow_path([(19, 11), (13, 11)])
                    context.emulator.press_button("A")
                    yield from navigate_to(17, 11)
                    context.emulator.press_button("A")
                    yield from follow_path([(15, 11), (15, 13)])
                    context.emulator.press_button("A")
                    yield from follow_path([(15, 14), (12, 14)])
                    context.emulator.press_button("A")
                    yield from navigate_to(18, 14)
                    context.emulator.press_button("A")
                    yield from navigate_to(15, 14)
                    context.emulator.press_button("Down")
                    yield
                    context.emulator.press_button("A")
                    # yield from navigate_to(15, 11)
                    yield from wait_for_n_frames(60)
                    if get_map_objects()[1].current_coords == (15, 10):
                        context.message = "Deoxys puzzle complete!"
                        context.bot_mode = "Manual"
                    else:
                        yield from navigate_to(15, 24)
                        yield from walk_one_tile("Down")
                        yield from walk_one_tile("Up")

            # Tanoby Key
            case MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY:
                context.message = "Solving Tanoby Key..."

                def path():
                    yield from navigate_to(7, 8)
                    yield from navigate_to(7, 7)
                    yield from use_party_hm_move("Strength")
                    yield from wait_for_script_to_start_and_finish("EventScript_UseStrength", "B")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from follow_path([(7, 4), (5, 4), (5, 6)])
                    yield from walk_one_tile("Right")
                    yield from follow_path([(6, 7), (7, 7)])
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from follow_path([(7, 6), (5, 6), (5, 4), (6, 4)])
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Right")
                    yield from follow_path([(9, 4), (9, 6)])
                    yield from walk_one_tile("Left")
                    yield from follow_path([(8, 6), (8, 7), (7, 7)])
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from follow_path([(7, 6), (9, 6), (9, 4)])
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Left")
                    yield from follow_path([(7, 4), (7, 10)])
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from follow_path([(7, 7), (7, 6)])
                    yield from walk_one_tile("Left")
                    yield from follow_path([(6, 10), (7, 10)])
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from follow_path([(7, 7), (7, 6)])
                    yield from walk_one_tile("Right")
                    yield from follow_path([(7, 12), (9, 12), (9, 11)])
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from follow_path([(7, 12), (5, 12), (5, 11)])
                    yield from walk_one_tile("Up")
                    while (
                        "SevenIsland_SevaultCanyon_TanobyKey_EventScript_PuzzleSolved"
                        not in get_global_script_context().stack
                    ):
                        context.emulator.press_button("Up")
                        yield
                    yield from wait_for_script_to_start_and_finish(
                        "SevenIsland_SevaultCanyon_TanobyKey_EventScript_PuzzleSolved", "B"
                    )
                    if get_event_flag("SYS_UNLOCKED_TANOBY_RUINS"):
                        context.message = "Tanoby Key puzzle complete!"
                        context.bot_mode = "Manual"
                    else:
                        yield from navigate_to(7, 13)
                        yield from walk_one_tile("Down")
                        yield from walk_one_tile("Up")

            case _:
                raise BotModeError("You are not on the right map.")

        def repelCheck():
            repel_steps = get_event_var("REPEL_STEP_COUNT")
            if repel_steps < 1 and get_save_data().get_item_bag().number_of_repels > 0:
                # use repel
                first_max_repel = None
                first_super_repel = None
                first_repel = None
                index = 0
                for slot in get_item_bag().items:
                    if first_max_repel is None and slot.item.name == "Max Repel":
                        first_max_repel = index
                    elif first_super_repel is None and slot.item.name == "Super Repel":
                        first_super_repel = index
                    elif first_repel is None and slot.item.name == "Repel":
                        first_repel = index
                    index += 1
                if first_max_repel is not None:
                    slot_to_use = first_max_repel
                elif first_super_repel is not None:
                    slot_to_use = first_super_repel
                elif first_repel is not None:
                    slot_to_use = first_repel
                else:
                    raise BotModeError("No repels left.")

                yield from StartMenuNavigator("BAG").step()
                yield from wait_until_task_is_active("Task_BagMenu_HandleInput")
                while read_symbol("gBagPosition")[5] != 0:
                    context.emulator.press_button("Left")
                    yield
                while True:
                    bag_position = read_symbol("gBagPosition")
                    current_slot = unpack_uint16(bag_position[8:10]) + unpack_uint16(bag_position[18:20])
                    if current_slot == slot_to_use:
                        break
                    if current_slot < slot_to_use:
                        context.emulator.press_button("Down")
                    else:
                        context.emulator.press_button("Up")
                    yield
                yield from wait_for_task_to_start_and_finish("Task_ContinueTaskAfterMessagePrints", "A")
                yield from wait_for_task_to_start_and_finish("Task_ShowStartMenu", "B")
                yield

        while True and context.bot_mode != "Manual":
            if useRepel == True:
                yield from repelCheck()

            for _ in path():
                if context.rom.is_rs:
                    repel_script = "S_RepelWoreOff"
                if context.rom.is_emerald:
                    repel_script = "EventScript_RepelWoreOff"
                if context.rom.is_frlg:
                    repel_script = "EventScript_RepelWoreOff"
                if repel_script in get_global_script_context().stack:
                    context.emulator.press_button("A")
                    yield
                yield

            while len(get_map_objects()) > 1:
                context.emulator.press_button("A")
                yield

            while "heldMovementActive" not in get_map_objects()[0].flags:
                context.emulator.press_button("B")
                yield
