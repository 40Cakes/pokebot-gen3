from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.map import get_map_objects
from modules.map_data import MapFRLG, MapRSE
from modules.memory import get_event_flag, get_event_var
from modules.menuing import use_party_hm_move
from modules.player import get_player_avatar
from modules.tasks import get_global_script_context
from ._asserts import assert_has_pokemon_with_move, assert_no_auto_battle, assert_no_auto_pickup, assert_registered_item
from ._interface import BotMode, BotModeError
from .util import (
    follow_path,
    ensure_facing_direction,
    navigate_to,
    wait_for_player_avatar_to_be_controllable,
    wait_for_n_frames,
    wait_for_script_to_start_and_finish,
    wait_for_task_to_start_and_finish,
    walk_one_tile,
    apply_repel,
    replenish_repel,
)


@debug.track
def mount_bike() -> Generator:
    while not get_player_avatar().is_on_bike:
        context.emulator.press_button("Select")
        yield


@debug.track
def unmount_bike() -> Generator:
    while get_player_avatar().is_on_bike:
        context.emulator.press_button("Select")
        yield


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

    def on_repel_effect_ended(self) -> None:
        replenish_repel()

    def run(self) -> Generator:
        assert_no_auto_battle("This mode should not be used with auto-battle.")
        assert_no_auto_pickup("This mode should not be used while auto-pickup is enabled.")
        use_repel = False

        match get_player_avatar().map_group_and_number:
            # Mirage Tower
            case MapRSE.MIRAGE_TOWER_1F:
                context.message = "Solving Mirage Tower..."
                use_repel = True
                assert_registered_item("Mach Bike", "This mode requires the Mach Bike registered to the Select button.")
                assert_has_pokemon_with_move("Rock Smash", "This mode requires Pokémon with Rock Smash.")

                def path():
                    # floor 1
                    yield from mount_bike()
                    yield from navigate_to(MapRSE.MIRAGE_TOWER_1F, (15, 2))
                    # floor 2
                    yield from navigate_to(MapRSE.MIRAGE_TOWER_2F, (18, 12))
                    # floor 3
                    yield from navigate_to(MapRSE.MIRAGE_TOWER_3F, (3, 8))
                    yield from ensure_facing_direction("Up")
                    yield from use_party_hm_move("Rock Smash")
                    yield from wait_for_script_to_start_and_finish("EventScript_SmashRock")
                    yield
                    yield from navigate_to(MapRSE.MIRAGE_TOWER_3F, (2, 4))
                    # floor 4
                    yield from navigate_to(MapRSE.MIRAGE_TOWER_4F, (5, 7))
                    yield from ensure_facing_direction("Right")
                    yield from use_party_hm_move("Rock Smash")
                    yield from wait_for_script_to_start_and_finish("EventScript_SmashRock")
                    yield
                    yield from unmount_bike()
                    yield from navigate_to(MapRSE.MIRAGE_TOWER_4F, (6, 4))
                    context.message = "Mirage Tower puzzle complete!"
                    context.bot_mode = "Manual"

            # Sky Pillar
            case MapRSE.SKY_PILLAR_OUTSIDE:
                context.message = "Solving Sky Pillar..."
                use_repel = True
                assert_registered_item("Mach Bike", "This mode requires the Mach Bike registered to the Select button.")

                def path():
                    yield from walk_one_tile("Up")
                    # floor 1
                    yield from mount_bike()
                    yield from navigate_to(MapRSE.SKY_PILLAR_1F, (10, 1))
                    # floor 2
                    yield from navigate_to(MapRSE.SKY_PILLAR_2F, (3, 1))
                    # floor 3
                    yield from navigate_to(MapRSE.SKY_PILLAR_3F, (11, 1))
                    # floor 4
                    yield from navigate_to(MapRSE.SKY_PILLAR_4F, (5, 4))
                    # after falling down to floor 3
                    yield from mount_bike()
                    yield from navigate_to(MapRSE.SKY_PILLAR_3F, (7, 1))
                    # back on floor 4
                    yield from navigate_to(MapRSE.SKY_PILLAR_4F, (3, 1))
                    # floor 5
                    yield from navigate_to(MapRSE.SKY_PILLAR_5F, (10, 1))
                    context.message = "Sky Pillar puzzle complete!"
                    context.bot_mode = "Manual"

            # Regirock
            case MapRSE.DESERT_RUINS:
                context.message = "Solving Regirock Puzzle..."

                def path():
                    yield from navigate_to(MapRSE.DESERT_RUINS, (8, 21))
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
                            yield from navigate_to(MapRSE.DESERT_RUINS, (8, 29))
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
                        yield from navigate_to(MapRSE.DESERT_RUINS, (8, 21))
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Regirock puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(MapRSE.DESERT_RUINS, (8, 29))
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Regice
            case MapRSE.ISLAND_CAVE:
                context.message = "Solving Regice Puzzle..."

                def path():
                    yield from navigate_to(MapRSE.ISLAND_CAVE, (8, 21))
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
                            yield from navigate_to(MapRSE.ISLAND_CAVE, (8, 29))
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
                            yield from navigate_to(MapRSE.ISLAND_CAVE, (8, 29))
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Registeel
            case MapRSE.ANCIENT_TOMB:
                context.message = "Solving Registeel Puzzle..."

                def path():
                    yield from navigate_to(MapRSE.ANCIENT_TOMB, (8, 21))
                    context.emulator.press_button("A")
                    yield from wait_for_n_frames(5)
                    context.emulator.press_button("B")
                    if context.rom.is_emerald:
                        assert_has_pokemon_with_move("Flash", "Registeel Puzzle (Emerald) requires Pokémon with Flash.")
                        context.message = "Using Flash..."
                        yield from navigate_to(MapRSE.ANCIENT_TOMB, (8, 25))
                        yield from use_party_hm_move("Flash")
                        yield from wait_for_task_to_start_and_finish("Task_DoFieldMove_RunFunc")
                        if get_event_flag("SYS_REGISTEEL_PUZZLE_COMPLETED"):
                            context.message = "Registeel puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(MapRSE.ANCIENT_TOMB, (8, 29))
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

                    if context.rom.is_rs:
                        assert_has_pokemon_with_move(
                            "Fly", "Regirock Puzzle (Ruby/Sapphire) requires Pokémon with Fly."
                        )
                        yield from navigate_to(MapRSE.ANCIENT_TOMB, (8, 25))
                        yield from use_party_hm_move("Fly")
                        yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry")
                        yield from navigate_to(MapRSE.ANCIENT_TOMB, (8, 21))
                        yield from walk_one_tile("Up")
                        if get_player_avatar().local_coordinates == (8, 11):
                            context.message = "Registeel puzzle complete!"
                            context.bot_mode = "Manual"
                        else:
                            yield from navigate_to(MapRSE.ANCIENT_TOMB, (8, 29))
                            yield from walk_one_tile("Down")
                            yield from walk_one_tile("Up")

            # Deoxys
            case MapRSE.BIRTH_ISLAND_EXTERIOR:
                context.message = "Solving Deoxys Puzzle..."

                def path():
                    yield from navigate_to(MapRSE.BIRTH_ISLAND_EXTERIOR, (15, 13))
                    context.emulator.press_button("A")
                    yield from navigate_to(MapRSE.BIRTH_ISLAND_EXTERIOR, (11, 13))
                    context.emulator.press_button("Down")
                    yield
                    context.emulator.press_button("A")
                    yield from follow_path([(15, 13), (15, 9)])
                    context.emulator.press_button("A")
                    yield from follow_path([(19, 9), (19, 13)])
                    context.emulator.press_button("A")
                    yield from follow_path([(19, 11), (13, 11)])
                    context.emulator.press_button("A")
                    yield from navigate_to(MapRSE.BIRTH_ISLAND_EXTERIOR, (17, 11))
                    context.emulator.press_button("A")
                    yield from follow_path([(15, 11), (15, 13)])
                    context.emulator.press_button("A")
                    yield from follow_path([(15, 14), (12, 14)])
                    context.emulator.press_button("A")
                    yield from navigate_to(MapRSE.BIRTH_ISLAND_EXTERIOR, (18, 14))
                    context.emulator.press_button("A")
                    yield from navigate_to(MapRSE.BIRTH_ISLAND_EXTERIOR, (15, 14))
                    context.emulator.press_button("Down")
                    yield
                    context.emulator.press_button("A")
                    # yield from navigate_to(15, 11)
                    yield from wait_for_n_frames(60)
                    if get_map_objects()[1].current_coords == (15, 10):
                        context.message = "Deoxys puzzle complete!"
                        context.bot_mode = "Manual"
                    else:
                        yield from navigate_to(MapRSE.BIRTH_ISLAND_EXTERIOR, (15, 24))
                        yield from walk_one_tile("Down")
                        yield from walk_one_tile("Up")

            # Tanoby Key
            case MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY:
                context.message = "Solving Tanoby Key..."

                def path():
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 7))
                    yield from use_party_hm_move("Strength")
                    yield from wait_for_script_to_start_and_finish("EventScript_UseStrength", "B")
                    yield
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")

                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (5, 6))
                    yield from walk_one_tile("Right")
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 7))
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (6, 4))
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Right")

                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (9, 6))
                    yield from walk_one_tile("Left")
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 7))
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (8, 4))
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Left")

                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 10))
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 6))
                    yield from walk_one_tile("Left")

                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 10))
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 6))
                    yield from walk_one_tile("Right")

                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (9, 11))
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")

                    yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (5, 11))
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
                        yield from navigate_to(MapFRLG.SEVEN_ISLAND_SEVAULT_CANYON_TANOBY_KEY, (7, 13))
                        yield from walk_one_tile("Down")
                        yield from walk_one_tile("Up")

            case _:
                raise BotModeError("You are not on the right map.")

        while True and context.bot_mode != "Manual":
            if use_repel and get_event_var("REPEL_STEP_COUNT") == 0:
                yield from apply_repel()

            yield from path()

            while len(get_map_objects()) > 1:
                context.emulator.press_button("A")
                yield

            yield from wait_for_player_avatar_to_be_controllable("B")
