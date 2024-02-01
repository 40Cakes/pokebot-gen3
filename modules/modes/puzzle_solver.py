from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.items import get_item_bag, get_item_by_name
from modules.map import get_map_objects
from modules.memory import get_event_flag, get_event_var, read_symbol, unpack_uint16
from modules.menu_parsers import CursorOptionEmerald, CursorOptionFRLG, CursorOptionRS
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon import get_move_by_name, get_party
from modules.save_data import get_save_data
from ._asserts import assert_no_auto_battle, assert_no_auto_pickup, assert_registered_item, assert_has_pokemon_with_move
from ._interface import BotMode, BotModeError
from ._util import (
    wait_for_task_to_start_and_finish,
    navigate_to,
    walk_one_tile,
    follow_path,
    wait_until_task_is_active,
    wait_for_n_frames,
)


class PuzzleSolverMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Puzzle Solver"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            return get_player_avatar().map_group_and_number in [
                MapRSE.SKY_PILLAR_A.value,
                MapRSE.ISLAND_CAVE.value,
                MapRSE.DESERT_RUINS.value,
                MapRSE.ANCIENT_TOMB.value,
                MapRSE.BIRTH_ISLAND.value,
                MapRSE.MIRAGE_TOWER.value,
            ]
        else:
            return False

    def run(self) -> Generator:
        assert_no_auto_battle("This mode should not be used with auto-battle.")
        assert_no_auto_pickup("This mode should not be used while auto-pickup is enabled.")
        useRepel = False

        # could probably move this into PokemonPartyMenuNavigator and use globally as I coded for all RSEFRLG HMs
        def use_hm_move(move_name: str):
            move_name_upper = move_name.upper()
            # badge checks
            if context.rom.is_rse:
                match move_name_upper:
                    case "CUT":
                        if not get_event_flag("BADGE01_GET"):
                            raise BotModeError("You do not have the Stone Badge to use Cut outside of battle.")
                    case "FLASH":
                        if not get_event_flag("BADGE02_GET"):
                            raise BotModeError("You do not have the Knuckle Badge to use Flash outside of battle.")
                    case "ROCK SMASH":
                        if not get_event_flag("BADGE03_GET"):
                            raise BotModeError("You do not have the Dynamo Badge to use Rock Smash outside of battle.")
                    case "STRENGTH":
                        if not get_event_flag("BADGE04_GET"):
                            raise BotModeError("You do not have the Heat Badge to use Strength outside of battle.")
                    case "SURF":
                        if not get_event_flag("BADGE05_GET"):
                            raise BotModeError("You do not have the Balance Badge to use Surf outside of battle.")
                    case "FLY":
                        if not get_event_flag("BADGE06_GET"):
                            raise BotModeError("You do not have the Feather Badge to use Fly outside of battle.")
                    case "DIVE":
                        if not get_event_flag("BADGE07_GET"):
                            raise BotModeError("You do not have the Mind Badge to use Dive outside of battle.")
                    case "WATERFALL":
                        if not get_event_flag("BADGE08_GET"):
                            raise BotModeError("You do not have the Rain Badge to use Waterfall outside of battle.")
            if context.rom.is_frlg:
                match move_name_upper:
                    case "FLASH":
                        if not get_event_flag("BADGE01_GET"):
                            raise BotModeError("You do not have the Boulder Badge to use Flash outside of battle.")
                    case "CUT":
                        if not get_event_flag("BADGE02_GET"):
                            raise BotModeError("You do not have the Cascade Badge to use Cut outside of battle.")
                    case "FLY":
                        if not get_event_flag("BADGE03_GET"):
                            raise BotModeError("You do not have the Thunder Badge to use Fly outside of battle.")
                    case "STRENGTH":
                        if not get_event_flag("BADGE04_GET"):
                            raise BotModeError("You do not have the Rainbow Badge to use Strength outside of battle.")
                    case "SURF":
                        if not get_event_flag("BADGE05_GET"):
                            raise BotModeError("You do not have the Soul Badge to use Surf outside of battle.")
                    case "ROCK SMASH":
                        if not get_event_flag("BADGE06_GET"):
                            raise BotModeError("You do not have the Marsh Badge to use Rock Smash outside of battle.")
                    case "WATERFALL":
                        if not get_event_flag("BADGE07_GET"):
                            raise BotModeError("You do not have the Volcano Badge to use Waterfall outside of battle.")

            yield from StartMenuNavigator("POKEMON").step()

            # find pokemon with desired HM move
            move_pokemon = None
            move_wanted = get_move_by_name(move_name)
            for index in range(len(get_party())):
                for learned_move in get_party()[index].moves:
                    if learned_move is not None and learned_move.move == move_wanted:
                        move_pokemon = index
                        break
            # use the move
            if move_name_upper == "CUT":  # hm01
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.CUT).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.CUT).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.CUT).step()
            elif move_name_upper == "FLY":  # hm02
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.FLY).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.FLY).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.FLY).step()
            elif move_name_upper == "SURF":  # hm03
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.SURF).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.SURF).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.SURF).step()
            elif move_name_upper == "STRENGTH":  # hm04
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.STRENGTH).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.STRENGTH).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.STRENGTH).step()
            elif move_name_upper == "FLASH":  # hm05
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.FLASH).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.FLASH).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.FLASH).step()
            elif move_name_upper == "ROCK SMASH":  # hm06
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.ROCK_SMASH).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.ROCK_SMASH).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.ROCK_SMASH).step()
            elif move_name_upper == "WATERFALL":  # hm07
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.WATERFALL).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.WATERFALL).step()
                elif context.rom.is_frlg:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionFRLG.WATERFALL).step()
            elif move_name_upper == "DIVE":  # hm08
                if context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionEmerald.DIVE).step()
                elif context.rom.is_rse and not context.rom.is_emerald:
                    yield from PokemonPartyMenuNavigator(move_pokemon, "", CursorOptionRS.DIVE).step()
                # no Dive in FRLG
            return

        match get_player_avatar().map_group_and_number:
            # Mirage Tower
            case MapRSE.MIRAGE_TOWER.value:
                context.message = "Solving Mirage Tower..."
                useRepel = True
                assert_registered_item("Mach Bike", "This mode requires the Mach Bike.")
                assert_has_pokemon_with_move("Rock Smash", "This mode requires Pokemon with Rock Smash.")

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
                    yield from use_hm_move("Rock Smash")
                    yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                    yield from follow_path([(3, 4), (2, 4)])
                    yield from wait_for_task_to_start_and_finish("Task_ExitNonDoor")
                    yield from wait_for_n_frames(10)
                    yield from follow_path([(2, 4), (2, 7), (5, 7)])
                    yield from use_hm_move("Rock Smash")
                    yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                    yield from wait_for_n_frames(540)
                    yield from navigate_to(6, 6)
                    if get_player_avatar().local_coordinates == (6, 6):
                        context.message = "Mirage Tower puzzle complete."
                        context.bot_mode = "Manual"

            # Sky Pillar
            case MapRSE.SKY_PILLAR_A.value:
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
                    context.message = "Sky Pillar puzzle complete."
                    context.bot_mode = "Manual"

            # Regirock
            case MapRSE.DESERT_RUINS.value:
                context.message = "Solving Regirock Puzzle..."

                def path():
                    yield from navigate_to(8, 21)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("B")
                    if context.rom.is_emerald:
                        assert_has_pokemon_with_move(
                            "Rock Smash", "Regirock Puzzle (Emerald) requires Pokemon with Rock Smash."
                        )
                        context.message = "Two Left, Two Down, Rock Smash..."
                        yield from follow_path([(6, 21), (6, 23)])
                        # use rock smash
                        yield from use_hm_move("Rock Smash")
                        yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                        if get_event_flag("SYS_REGIROCK_PUZZLE_COMPLETED"):
                            context.message = "Regirock puzzle complete."
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")
                    if context.rom.is_rse and not context.rom.is_emerald:
                        assert_has_pokemon_with_move(
                            "Strength", "Regirock Puzzle (Ruby/Sapphire) requires Pokemon with Strength."
                        )
                        context.message = "Two Right, Two Down, Strength..."
                        yield from follow_path([(10, 21), (10, 23)])
                        yield from use_hm_move("Strength")
                        yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry")
                        yield from navigate_to(8, 21)
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Regirock puzzle complete."
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Regice
            case MapRSE.ISLAND_CAVE.value:
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
                            context.message = "Regice puzzle complete."
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")
                    if context.rom.is_rse and not context.rom.is_emerald:
                        context.message = "Waiting 2 minutes game time..."
                        yield from wait_for_n_frames(7300)
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Regice puzzle complete."
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Registeel
            case MapRSE.ANCIENT_TOMB.value:
                context.message = "Solving Registeel Puzzle..."

                def path():
                    yield from navigate_to(8, 21)
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("B")
                    if context.rom.is_emerald:
                        assert_has_pokemon_with_move("Flash", "Registeel Puzzle (Emerald) requires Pokemon with Flash.")
                        context.message = "Using Flash..."
                        yield from navigate_to(8, 25)
                        yield from use_hm_move("Flash")
                        yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                        if get_event_flag("SYS_REGISTEEL_PUZZLE_COMPLETED"):
                            context.message = "Registeel puzzle complete."
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

                    if context.rom.is_rse and not context.rom.is_emerald:
                        assert_has_pokemon_with_move(
                            "Fly", "Regirock Puzzle (Ruby/Sapphire) requires Pokemon with Fly."
                        )
                        yield from navigate_to(8, 25)
                        yield from use_hm_move("Fly")
                        yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry")
                        yield from navigate_to(8, 21)
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Registeel puzzle complete."
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(8, 29)
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Deoxys
            case MapRSE.BIRTH_ISLAND.value:
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
                    yield from navigate_to(15, 11)

                    if get_map_objects()[1].current_coords == (15, 10):
                        context.message = "Deoxys puzzle complete."
                        context.bot_mode = "Manual"
                    else:
                        yield from navigate_to(15, 24)
                        yield from walk_one_tile("Down")
                        yield from walk_one_tile("Up")

            case _:
                raise BotModeError("You are not on the right map.")

        def repelCheck():
            repel_steps = get_event_var("REPEL_STEP_COUNT")
            item_bag = get_save_data().get_item_bag()
            repels_in_bag = (
                item_bag.quantity_of(get_item_by_name("Max Repel"))
                + item_bag.quantity_of(get_item_by_name("Super Repel"))
                + item_bag.quantity_of(get_item_by_name("Repel"))
            )
            if repel_steps < 1 and repels_in_bag > 0:
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

            yield from path()

            while len(get_map_objects()) > 1:
                context.emulator.press_button("A")
                yield

            while "heldMovementActive" not in get_map_objects()[0].flags:
                context.emulator.press_button("B")
                yield
