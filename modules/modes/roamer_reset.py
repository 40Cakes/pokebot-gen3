from typing import Generator

from modules.data.map import MapFRLG, MapRSE

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.gui.multi_select_window import ask_for_choice, Selection
from modules.items import get_item_bag, get_item_by_name
from modules.map import get_map_objects
from modules.memory import get_game_state, GameState, unpack_uint16, get_save_block, read_symbol, get_game_state_symbol
from modules.menu_parsers import CursorOptionFRLG, CursorOptionEmerald
from modules.menuing import StartMenuNavigator, PokemonPartyMenuNavigator
from modules.player import get_player, get_player_avatar
from modules.pokemon import get_party, get_move_by_name, get_opponent
from modules.region_map import get_map_cursor
from modules.roamer import get_roamer
from modules.runtime import get_sprites_path
from modules.tasks import get_global_script_context
from ._asserts import assert_save_game_exists, assert_saved_on_map, SavedMapLocation
from ._interface import BotMode, BotModeError
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    navigate_to,
    ensure_facing_direction,
    walk_one_tile,
    wait_until_task_is_active,
    wait_for_task_to_start_and_finish,
)


def _get_allowed_starting_map() -> tuple[int, int]:
    if context.rom.is_frlg:
        return MapFRLG.ONE_ISLAND_A.value
    elif context.rom.is_emerald:
        if get_player().gender == "female":
            return MapRSE.LITTLEROOT_TOWN_D.value
        else:
            return MapRSE.LITTLEROOT_TOWN_B.value
    else:
        # No R/S yet
        return -1, -1


class RoamerResetMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Roamer (Reset)"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_group_and_number == _get_allowed_starting_map()

    @staticmethod
    def disable_default_battle_handler() -> bool:
        return True

    def run(self) -> Generator:
        assert_save_game_exists("There is no saved game. Cannot soft reset.")

        if context.rom.is_frlg:
            location_error = "The game has not been saved while standing in the Pokemon Net Center on One Island."
        else:
            location_error = "The game has not been saved while standing on the top floor of the player's house."
        assert_saved_on_map(SavedMapLocation(_get_allowed_starting_map()), error_message=location_error)

        item_bag = get_item_bag()
        number_of_repels = (
            item_bag.quantity_of(get_item_by_name("Max Repel"))
            + item_bag.quantity_of(get_item_by_name("Super Repel"))
            + item_bag.quantity_of(get_item_by_name("Repel"))
        )
        if number_of_repels == 0:
            raise BotModeError("You do not have any repels in your item bag. Go and get some first!")

        has_flying_pokemon = False
        move_fly = get_move_by_name("Fly")
        for party_member in get_party():
            for learned_move in party_member.moves:
                if learned_move is not None and learned_move.move == move_fly:
                    has_flying_pokemon = True
                    break
        if not has_flying_pokemon:
            raise BotModeError("None of your party Pokémon know the move Fly. Please teach it to someone.")

        if context.rom.is_frlg:
            yield from self.run_frlg()
        elif context.rom.is_emerald:
            yield from self.run_emerald()
        else:
            context.message = "This game is not yet supported."
            context.set_manual_mode()

    def run_emerald(self):
        roamer_choice = ask_for_choice(
            [
                Selection("Latias", get_sprites_path() / "pokemon" / "normal" / "Latias.png"),
                Selection("Latios", get_sprites_path() / "pokemon" / "normal" / "Latios.png"),
            ],
            window_title="Select a Pokémon...",
        )
        if roamer_choice is None:
            return

        if get_player().gender == "female":
            yield from navigate_to(1, 2)
        else:
            yield from navigate_to(7, 2)

        yield from walk_one_tile("Up")

        yield from wait_until_task_is_active("Task_HandleMultichoiceInput", "B")
        if roamer_choice == "Latios":
            yield
            context.emulator.press_button("Down")
            yield
            yield

        while get_global_script_context().is_active:
            context.emulator.press_button("A")
            yield

        while "heldMovementFinished" not in get_map_objects()[0].flags or "frozen" in get_map_objects()[0].flags:
            yield

        if get_player().gender == "female":
            yield from navigate_to(2, 8)
        else:
            yield from navigate_to(8, 8)

        yield from walk_one_tile("Down")

        # Select field move FLY
        yield from StartMenuNavigator("POKEMON").step()
        yield from PokemonPartyMenuNavigator(1, "", CursorOptionEmerald.FLY).step()

        while get_game_state_symbol() != "CB2_FLYMAP":
            yield

        # Select Pallet Town on the region map
        while get_map_cursor() is None:
            yield
        while get_map_cursor() != (9, 13) and get_map_cursor() != (9, 12):
            context.emulator.reset_held_buttons()
            if get_map_cursor()[0] < 9:
                context.emulator.hold_button("Right")
            elif get_map_cursor()[0] > 9:
                context.emulator.hold_button("Left")
            elif get_map_cursor()[1] < 12:
                context.emulator.hold_button("Down")
            elif get_map_cursor()[1] > 13:
                context.emulator.hold_button("Up")
            yield
        context.emulator.reset_held_buttons()

        # Fly to Pallet Town
        yield from wait_for_task_to_start_and_finish("Task_FlyIntoMap", "A")
        yield

        yield from navigate_to(15, 0)

        def inner_loop():
            yield from walk_one_tile("Up")
            yield from navigate_to(14, 97)
            directions = ["Down", "Right", "Up", "Left"]
            for index in range(10):
                yield from ensure_facing_direction(directions[index % 4])
            yield from navigate_to(15, 99)
            yield from walk_one_tile("Down")

        def apply_repel():
            # Look up location of a Repel item in the item bag
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
                raise BotModeError("You've run out of repels.")

            # Open item bag and select the best Repel item there is (Max > Super > Regular)
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

        def get_repel_steps_remaining():
            return unpack_uint16(get_save_block(1, offset=0x139C + (0x21 * 2), size=2))

        while get_game_state() != GameState.BATTLE:
            for _ in inner_loop():
                if get_game_state() == GameState.BATTLE:
                    break
                global_ctx = get_global_script_context()
                if global_ctx.is_active:
                    previous_inputs = context.emulator.reset_held_buttons()
                    yield
                    while global_ctx.is_active:
                        if global_ctx.native_function_name == "WaitForAorBPress":
                            context.emulator.press_button("A")
                        yield
                        global_ctx = get_global_script_context()
                    context.emulator.restore_held_buttons(previous_inputs)
                    yield
                if get_repel_steps_remaining() <= 0:
                    previous_inputs = context.emulator.reset_held_buttons()
                    yield
                    for __ in apply_repel():
                        if get_game_state() == GameState.BATTLE:
                            break
                        yield
                    context.emulator.restore_held_buttons(previous_inputs)
                    yield
                yield

        yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry")
        if get_opponent().is_shiny:
            encounter_pokemon(get_opponent())
            if context.bot_mode != "Manual":
                context.set_manual_mode()
            return
        else:
            encounter_pokemon(get_opponent(), log_only=True)

    def run_frlg(self):
        while True:
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            # No idea.
            for _ in range(5):
                yield

            yield from navigate_to(14, 6)
            yield from ensure_facing_direction("Right")

            context.emulator.press_button("A")
            yield

            while get_roamer() is None:
                context.emulator.press_button("B")
                yield

            # Leave the building
            yield from navigate_to(9, 9)
            yield from walk_one_tile("Down")

            # Walk to the ferry terminal and up to the sailor
            yield from navigate_to(12, 18)
            yield from walk_one_tile("Down")
            yield from navigate_to(8, 5)

            # Talk to the sailor
            while get_game_state() == GameState.OVERWORLD:
                context.emulator.press_button("A")
                yield

            # Wait for the ferry cutscene to finish
            while get_game_state() != GameState.OVERWORLD:
                yield

            # Select field move FLY
            yield from StartMenuNavigator("POKEMON").step()
            yield from PokemonPartyMenuNavigator(1, "", CursorOptionFRLG.FLY).step()
            yield from wait_until_task_is_active("Task_FlyMap")

            # Select Pallet Town on the region map
            while get_map_cursor() is None:
                yield
            while get_map_cursor() != (4, 11):
                context.emulator.reset_held_buttons()
                if get_map_cursor()[0] < 4:
                    context.emulator.hold_button("Right")
                elif get_map_cursor()[0] > 4:
                    context.emulator.hold_button("Left")
                elif get_map_cursor()[1] < 11:
                    context.emulator.hold_button("Down")
                elif get_map_cursor()[1] > 11:
                    context.emulator.hold_button("Up")
                yield
            context.emulator.reset_held_buttons()

            # Fly to Pallet Town
            yield from wait_for_task_to_start_and_finish("Task_UseFly", "A")
            yield from wait_for_task_to_start_and_finish("Task_FlyIntoMap")

            # Go to the north of the map, just before Route 1 starts
            yield from walk_one_tile("Right")
            yield from navigate_to(12, 0)

            def inner_loop():
                yield from walk_one_tile("Up")
                directions = ["Left", "Down", "Right", "Up"]
                for index in range(10):
                    yield from ensure_facing_direction(directions[index % 4])
                yield from walk_one_tile("Down")

            def apply_repel():
                # Look up location of a Repel item in the item bag
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
                    raise BotModeError("You've run out of repels.")

                # Open item bag and select the best Repel item there is (Max > Super > Regular)
                yield from StartMenuNavigator("BAG").step()
                yield from wait_until_task_is_active("Task_BagMenu_HandleInput")
                while read_symbol("gBagMenuState")[6] != 0:
                    context.emulator.press_button("Left")
                    yield
                while read_symbol("gBagMenuState")[8] != slot_to_use:
                    if read_symbol("gBagMenuState")[8] < slot_to_use:
                        context.emulator.press_button("Down")
                    else:
                        context.emulator.press_button("Up")
                    yield

                yield from wait_for_task_to_start_and_finish("Task_ContinueTaskAfterMessagePrints", "A")
                yield from wait_for_task_to_start_and_finish("Task_StartMenuHandleInput", "B")

            def get_repel_steps_remaining():
                return unpack_uint16(get_save_block(1, offset=0x1000 + (0x20 * 2), size=2))

            while get_game_state() != GameState.BATTLE:
                for _ in inner_loop():
                    if get_game_state() == GameState.BATTLE:
                        break
                    steps_remaining = get_repel_steps_remaining()
                    if steps_remaining == 0:
                        previous_inputs = context.emulator.reset_held_buttons()
                        yield
                        context.emulator.press_button("B")
                        yield

                        for __ in apply_repel():
                            if get_game_state() == GameState.BATTLE:
                                break
                            yield

                        context.emulator.restore_held_buttons(previous_inputs)
                    yield

            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry")
            if get_opponent().is_shiny:
                encounter_pokemon(get_opponent())
                if context.bot_mode != "Manual":
                    context.set_manual_mode()
                return
            else:
                encounter_pokemon(get_opponent(), log_only=True)
