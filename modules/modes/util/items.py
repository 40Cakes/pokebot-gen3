from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.items import Item, ItemPocket, get_item_bag, get_item_by_name
from modules.memory import GameState, get_event_flag, get_game_state, read_symbol, unpack_uint16
from modules.menuing import StartMenuNavigator, scroll_to_item_in_bag as real_scroll_to_item
from modules.player import get_player
from modules.pokemon import get_party
from modules.tasks import task_is_active
from ._util_helper import isolate_inputs
from .sleep import wait_for_n_frames
from .tasks_scripts import wait_for_task_to_start_and_finish, wait_until_task_is_active
from .._interface import BotModeError


@debug.track
def scroll_to_item_in_bag(item: Item) -> Generator:
    """
    This will select the correct bag pocket and scroll to the correct position therein.

    It will _not_ activate the item (pressing A) and it does _not_ open the bag menu.
    It is assumed that the bag menu is already open.

    :param item: Item to scroll to
    """
    if get_item_bag().quantity_of(item) == 0:
        raise BotModeError(f"Cannot use {item.name} because there is none in the item bag.")

    yield from real_scroll_to_item(item)


class RanOutOfRepels(BotModeError):
    pass


@isolate_inputs
@debug.track
def use_item_from_bag(item: Item) -> Generator:
    yield from StartMenuNavigator("BAG").step()
    yield from scroll_to_item_in_bag(item)

    if context.rom.is_rs:
        confirmation_after_use_item_task = "sub_80F9090"
        start_menu_task = "sub_80712B4"
    elif context.rom.is_emerald:
        confirmation_after_use_item_task = "Task_ContinueTaskAfterMessagePrints"
        start_menu_task = "Task_ShowStartMenu"
    else:
        confirmation_after_use_item_task = "Task_ContinueTaskAfterMessagePrints"
        start_menu_task = "Task_StartMenuHandleInput"

    yield from wait_for_task_to_start_and_finish(confirmation_after_use_item_task, "A")
    yield from wait_for_task_to_start_and_finish(start_menu_task, "B")
    yield


@debug.track
def register_key_item(item: Item) -> Generator:
    """
    Ensures that a Key Item is registered to the Select button.
    :param item: The item to register
    """
    if item.pocket != ItemPocket.KeyItems:
        raise BotModeError(f"Cannot register {item.name} as it is not a Key Item.")

    if get_item_bag().quantity_of(item) <= 0:
        raise BotModeError(f"Cannot register {item.name} as it is not in the item bag.")

    previously_registered_item = get_player().registered_item
    if previously_registered_item is not None and previously_registered_item.index == item.index:
        return

    yield from StartMenuNavigator("BAG").step()
    yield from scroll_to_item_in_bag(item)
    context.emulator.press_button("A")
    if context.rom.is_rs:
        yield from wait_for_n_frames(4)
        context.emulator.press_button("Right")
        yield from wait_for_n_frames(3)
    elif context.rom.is_emerald:
        yield from wait_for_n_frames(3)
        context.emulator.press_button("Right")
        yield from wait_for_n_frames(3)
    else:
        yield from wait_for_n_frames(6)
        context.emulator.press_button("Down")
        yield from wait_for_n_frames(2)

    context.emulator.press_button("A")

    if context.rom.is_rs:
        start_menu_task = "sub_80712B4"
    elif context.rom.is_emerald:
        start_menu_task = "Task_ShowStartMenu"
    else:
        start_menu_task = "Task_StartMenuHandleInput"

    yield from wait_for_task_to_start_and_finish(start_menu_task, "B")
    yield


@debug.track
def apply_white_flute_if_available() -> Generator:
    if context.rom.is_frlg and get_event_flag("SYS_WHITE_FLUTE_ACTIVE"):
        return
    elif context.rom.is_rse and get_event_flag("SYS_ENC_UP_ITEM"):
        return

    white_flute = get_item_by_name("White Flute")
    if get_item_bag().quantity_of(white_flute) > 0:
        yield from use_item_from_bag(white_flute)


@isolate_inputs
@debug.track
def apply_repel() -> Generator:
    """
    Tries to use the strongest Repel available in the player's item bag (i.e. it will
    prefer Max Repel over Super Repel over Repel.)

    If the player does not have any Repel items, it raises a `RanOutOfRepels` error.
    """
    item_bag = get_item_bag()
    repel_item = get_item_by_name("Max Repel")
    repel_slot = item_bag.first_slot_index_for(repel_item)
    if repel_slot is None:
        repel_item = get_item_by_name("Super Repel")
        repel_slot = item_bag.first_slot_index_for(repel_item)
    if repel_slot is None:
        repel_item = get_item_by_name("Repel")
        repel_slot = item_bag.first_slot_index_for(repel_item)
    if repel_slot is None:
        raise RanOutOfRepels("Player is out or Repels.")

    yield from use_item_from_bag(repel_item)


def replenish_repel() -> None:
    """
    This can be used in a bot mode's `on_repel_effect_ended()` callback to re-enable the repel
    effect as soon as it expires.

    It should not be used anywhere else.
    """

    if get_item_bag().number_of_repels == 0:
        raise RanOutOfRepels("Player ran out of repels")
    else:

        def apply_repel_and_reset_inputs():
            yield from apply_repel()
            context.emulator.reset_held_buttons()

        context.controller_stack.insert(len(context.controller_stack) - 1, apply_repel_and_reset_inputs())


@debug.track
def teach_hm_or_tm(hm_or_tm: Item, party_index: int, move_index_to_replace: int = 3) -> Generator:
    """
    Attempts to teach an HM or TM move to a party Pokémon.

    This assumes that the game is currently in the overworld and the player is controllable.

    :param hm_or_tm: Item reference of the HM/TM to teach.
    :param party_index: Party index (0-5) of the Pokémon that this move should be taught to.
    :param move_index_to_replace: Index of a move (0-3) that should be replaced. If the
                                  Pokémon still has an empty move slot, this is not used.
    """

    yield from StartMenuNavigator("BAG").step()

    if context.rom.is_rse:
        yield from scroll_to_item_in_bag(hm_or_tm)
    else:
        # On FR/LG, there is a special 'TM Case' item which contains the actual HM/TM bag.
        # Open it, then scroll to the right position.
        yield from scroll_to_item_in_bag(get_item_by_name("TM Case"))
        yield from wait_until_task_is_active("Task_HandleListInput", "A")
        yield from wait_for_n_frames(25)
        target_slot_index = get_item_bag().first_slot_index_for(hm_or_tm)
        while True:
            tm_case_state = read_symbol("sTMCaseStaticResources", offset=8, size=4)
            cursor_offset = unpack_uint16(tm_case_state[:2])
            scroll_offset = unpack_uint16(tm_case_state[2:4])
            current_slot_index = cursor_offset + scroll_offset
            if current_slot_index < target_slot_index:
                context.emulator.press_button("Down")
                yield
            elif current_slot_index > target_slot_index:
                context.emulator.press_button("Up")
                yield
            else:
                break

    while get_game_state() != GameState.PARTY_MENU:
        context.emulator.press_button("A")
        yield

    # Select the target Pokémon in Party Menu
    while True:
        if context.rom.is_rs:
            current_slot_index = context.emulator.read_bytes(0x0202002F + len(get_party()) * 136 + 3, length=1)[0]
        else:
            current_slot_index = read_symbol("gPartyMenu", offset=9, size=1)[0]
        if current_slot_index < party_index:
            context.emulator.press_button("Down")
            yield
        elif current_slot_index > party_index:
            context.emulator.press_button("Up")
            yield
        else:
            break

    # Wait for either the 'Which move should be replaced' screen or for being
    # back at the item bag screen (if no move needed to be replaced, or if an
    # 'Pokémon already knows this move' error appeared.)
    press_a = True
    while (
        not task_is_active("Task_DuckBGMForPokemonCry")
        and get_game_state() != GameState.BAG_MENU
        and not task_is_active("Task_HandleListInput")
    ):
        if press_a:
            context.emulator.press_button("A")
        if task_is_active("sub_809E260"):
            press_a = False
        yield

    # Handle move replacing.
    if task_is_active("Task_DuckBGMForPokemonCry"):
        for _ in range(move_index_to_replace):
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(3 if context.rom.is_rse else 15)
        context.emulator.press_button("A")
        yield

    # Back to overworld.
    if context.rom.is_rs:
        yield from wait_for_task_to_start_and_finish("sub_80712B4", "B")
    elif context.rom.is_frlg:
        yield from wait_for_task_to_start_and_finish("Task_StartMenuHandleInput", "B")
    else:
        yield from wait_for_task_to_start_and_finish("Task_ShowStartMenu", "B")
    yield
