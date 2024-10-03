from enum import Enum
from typing import Generator, Union, Callable

from modules.context import context
from modules.debug import debug
from modules.map_data import PokemonCenter
from modules.memory import get_event_flag, get_game_state_symbol, unpack_uint32, read_symbol, get_game_state, GameState
from modules.menu_parsers import CursorOptionEmerald, CursorOptionFRLG, CursorOptionRS
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.modes.util.sleep import wait_for_n_frames
from modules.player import get_player_avatar, get_player, TileTransitionState, RunningState
from modules.pokemon import get_party
from modules.region_map import FlyDestinationFRLG, FlyDestinationRSE, get_map_cursor, get_map_region
from modules.tasks import get_task, task_is_active
from ._util_helper import isolate_inputs
from .items import scroll_to_item_in_bag
from .tasks_scripts import (
    wait_for_task_to_start_and_finish,
    wait_for_yes_no_question,
    wait_for_no_script_to_run,
    wait_until_task_is_active,
    wait_for_fade_to_finish,
)
from .walking import navigate_to, wait_for_player_avatar_to_be_standing_still
from .._interface import BotModeError
from ...game import get_symbol_name_before
from ...items import Item, get_item_bag, ItemPocket
from ...mart import get_mart_buyable_items, get_mart_buy_menu_scroll_position, get_mart_main_menu_scroll_position


@isolate_inputs
@debug.track
def fly_to(destination: Union[FlyDestinationRSE, FlyDestinationFRLG]) -> Generator:
    if context.rom.is_frlg:
        has_necessary_badge = get_event_flag("BADGE03_GET")
        menu_index = CursorOptionFRLG.FLY
    else:
        has_necessary_badge = get_event_flag("BADGE03_GET")
        if context.rom.is_rs:
            menu_index = CursorOptionRS.FLY
        else:
            menu_index = CursorOptionEmerald.FLY

    if not has_necessary_badge:
        raise BotModeError("Player does not have the badge required for flying.")

    if not get_event_flag(destination.get_flag_name()):
        raise BotModeError(f"Player cannot fly to {destination.name} because that location is not yet available.")

    flying_pokemon_index = -1
    for index in range(len(get_party())):
        pokemon = get_party()[index]
        for learned_move in pokemon.moves:
            if learned_move is not None and learned_move.move.name == "Fly":
                flying_pokemon_index = index
                break
        if flying_pokemon_index > -1:
            break
    if flying_pokemon_index == -1:
        raise BotModeError("Player does not have any Pokémon that knows Fly in their party.")

    # Select field move FLY
    yield from StartMenuNavigator("POKEMON").step()
    yield from PokemonPartyMenuNavigator(flying_pokemon_index, "", menu_index).step()

    # Wait for region map to load.
    while (
        get_game_state_symbol() not in ("CB2_FLYMAP", "CB2_REGIONMAP", "CB2_FLYREGIONMAP") or get_map_cursor() is None
    ):
        yield

    destination_region = destination.get_map_region()
    if get_map_region() != destination_region:
        raise BotModeError(f"Player cannot fly to {destination.name} because they are in the wrong region.")

    # Select destination on the region map
    x, y = destination.value
    while get_map_cursor() != (x, y):
        context.emulator.reset_held_buttons()
        if get_map_cursor()[0] < x:
            context.emulator.hold_button("Right")
        elif get_map_cursor()[0] > x:
            context.emulator.hold_button("Left")
        elif get_map_cursor()[1] < y:
            context.emulator.hold_button("Down")
        elif get_map_cursor()[1] > y:
            context.emulator.hold_button("Up")
        yield
    context.emulator.reset_held_buttons()

    # Wait for journey to finish
    if context.rom.is_rs:
        yield from wait_for_task_to_start_and_finish("Task_MapNamePopup", "A")
    else:
        yield from wait_for_task_to_start_and_finish("Task_FlyIntoMap", "A")

    yield


class TaskFishing(Enum):
    INIT = 0
    GET_ROD_OUT = 1
    WAIT_BEFORE_DOTS = 2
    INIT_DOTS = 3
    SHOW_DOTS = 4
    CHECK_FOR_BITE = 5
    GOT_BITE = 6
    WAIT_FOR_A = 7
    CHECK_MORE_DOTS = 8
    MON_ON_HOOK = 9
    START_ENCOUNTER = 10
    NOT_EVEN_NIBBLE = 11
    GOT_AWAY = 12
    NO_MON = 13
    PUT_ROD_AWAY = 14
    END_NO_MON = 15


@debug.track
def fish() -> Generator:
    task_fishing = get_task("Task_Fishing")
    if task_fishing is not None:
        match task_fishing.data[0]:
            case TaskFishing.WAIT_FOR_A.value | TaskFishing.END_NO_MON.value:
                context.emulator.press_button("A")
            case TaskFishing.NOT_EVEN_NIBBLE.value:
                context.emulator.press_button("B")
            case TaskFishing.START_ENCOUNTER.value:
                context.emulator.press_button("A")
    else:
        context.emulator.press_button("Select")
    yield


def spin(stop_condition: Callable[[], bool] | None = None):
    directions = ["Up", "Right", "Down", "Left"]
    while True:
        avatar = get_player_avatar()
        if (
            get_game_state() == GameState.OVERWORLD
            and avatar.tile_transition_state == TileTransitionState.NOT_MOVING
            and avatar.running_state == RunningState.NOT_MOVING
        ):
            if stop_condition is not None and stop_condition():
                return

            direction_index = (directions.index(avatar.facing_direction) + 1) % len(directions)
            context.emulator.press_button(directions[direction_index])
        yield


@debug.track
def heal_in_pokemon_center(pokemon_center_door_location: PokemonCenter) -> Generator:
    # Walk to and enter the Pokémon centre
    yield from navigate_to(pokemon_center_door_location.value[0], pokemon_center_door_location.value[1])

    # Walk up to the nurse and talk to her
    yield from navigate_to(get_player_avatar().map_group_and_number, (7, 4))
    yield
    context.emulator.press_button("A")
    yield from wait_for_yes_no_question("Yes")
    yield from wait_for_no_script_to_run("B")
    yield from wait_for_player_avatar_to_be_standing_still("B")

    # Get out
    yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))


@debug.track
def change_lead_party_pokemon(slot: int) -> Generator:
    if context.rom.is_emerald:
        cursor_option_switch = CursorOptionEmerald.SWITCH
        party_menu_task = "Task_HandleChooseMonInput"
        switch_pokemon_task = "Task_HandleChooseMonInput"
        slide_animation_task = "Task_SlideSelectedSlotsOnscreen"
        start_menu_task = "Task_ShowStartMenu"
    elif context.rom.is_rs:
        cursor_option_switch = CursorOptionRS.SWITCH
        party_menu_task = "HandleDefaultPartyMenu"
        switch_pokemon_task = "HandlePartyMenuSwitchPokemonInput"
        slide_animation_task = "sub_806D198"
        start_menu_task = "sub_80712B4"
    else:
        cursor_option_switch = CursorOptionFRLG.SWITCH
        party_menu_task = "Task_HandleChooseMonInput"
        switch_pokemon_task = "Task_HandleChooseMonInput"
        slide_animation_task = "Task_SlideSelectedSlotsOnscreen"
        start_menu_task = "Task_StartMenuHandleInput"

    yield from StartMenuNavigator("POKEMON").step()
    yield from wait_until_task_is_active(party_menu_task)
    yield
    yield from wait_for_fade_to_finish()
    yield from PokemonPartyMenuNavigator(0, "", cursor_option_switch).step()
    yield from wait_until_task_is_active(switch_pokemon_task)
    match slot:
        case 1:
            context.emulator.press_button("Right")
            yield from wait_for_n_frames(4)
            context.emulator.press_button("A")
            yield from wait_for_n_frames(4)
        case _ if slot != 1:
            context.emulator.press_button("Right")
            yield from wait_for_n_frames(4)
            for _ in range(slot - 1):
                context.emulator.press_button("Down")
                yield from wait_for_n_frames(4)
            context.emulator.press_button("A")
            yield from wait_for_n_frames(4)

    yield from wait_for_task_to_start_and_finish(slide_animation_task, "A")
    yield from wait_for_task_to_start_and_finish(start_menu_task, "B")
    yield from wait_for_n_frames(10)


@debug.track
def save_the_game():
    """
    Uses the in-game save function.

    This expects the game to be in the overworld with the start menu _closed_. It will
    open the start menu itself.

    It will confirm everything, including when warned that there is already a different
    save file (after restarting the game.)
    """

    yield from StartMenuNavigator("SAVE").step()

    if context.rom.is_frlg:
        save_dialogue_callback_name = "sSaveDialogCB"
        overwrite_callback = "SaveDialogCB_AskOverwriteOrReplacePreviousFileHandleInput"
        start_menu_task = "Task_StartMenuHandleInput"
    elif context.rom.is_emerald:
        save_dialogue_callback_name = "sSaveDialogCallback"
        overwrite_callback = "SaveOverwriteInputCallback"
        start_menu_task = "Task_ShowStartMenu"
    else:
        save_dialogue_callback_name = "saveDialogCallback"
        overwrite_callback = "SaveDialogCB_ProcessOverwriteYesNoMenu"
        start_menu_task = "sub_80712B4"

    while True:
        save_callback = get_symbol_name_before(unpack_uint32(read_symbol(save_dialogue_callback_name)))
        if not task_is_active(start_menu_task):
            break
        elif save_callback != overwrite_callback:
            context.emulator.press_button("A")
            yield
        else:
            context.emulator.press_button("Up")
            yield
            yield
            context.emulator.press_button("A")
            yield
            yield

    yield


@debug.track
def buy_in_shop(shopping_list: list[tuple[Item, int]]):
    """
    This can be used to walk through the Mart's buying menu and purchase one or
    more items.

    It expects the _main menu_ of the Mart to be open (the one where it asks Buy/Sell/Leave.)

    Call it like this:
    ```python
    yield from buy_in_shop([
        (get_item_by_name("Poké Ball"), 10),
        (get_item_by_name("Potion"), 20),
    ])
    ```

    :param shopping_list: A list of tuples where the first entry is the item to by, and the
                          second entry is the quantity for that item (max. 99, if you need
                          more create several entries in the list.)
    """

    if context.rom.is_rs:
        shop_menu_task = "Task_DoBuySellMenu"
        buy_menu_cb2 = "MAINCB2"
        select_quantity_task = "Shop_PrintPrice"
        buy_menu_task = "Shop_DoCursorAction"
        return_task = "Task_ReturnToMartMenu"
    else:
        shop_menu_task = "Task_ShopMenu"
        buy_menu_cb2 = "CB2_BUYMENU"
        select_quantity_task = "Task_BuyHowManyDialogueHandleInput"
        buy_menu_task = "Task_BuyMenu"
        return_task = "Task_ReturnToShopMenu"

    if not task_is_active(shop_menu_task):
        raise BotModeError(f"Cannot buy things in mart because `{shop_menu_task}` is not active.")

    buyable_items = get_mart_buyable_items()
    total_cost = 0
    for item, quantity in shopping_list:
        if item not in buyable_items:
            raise BotModeError(f"Cannot buy item {item.name} at this shop.")
        if quantity < 0 or quantity > 99:
            raise BotModeError(f"Cannot by {quantity} items: Invalid quantity.")
        total_cost += quantity * item.price

    player_money = get_player().money
    if player_money < total_cost:
        raise BotModeError(f"This shopping list would total ${total_cost:,}, but player only has ${player_money:,}")

    # Scroll to the 'Buy' option
    while get_mart_main_menu_scroll_position() > 0:
        context.emulator.press_button("Up")
        yield

    # Wait for 'Buy' menu to open
    context.emulator.press_button("A")
    while get_game_state_symbol() != buy_menu_cb2:
        yield
    for _ in range(22):
        yield

    for item, quantity in shopping_list:
        slot = buyable_items.index(item)
        while get_mart_buy_menu_scroll_position() != slot:
            if get_mart_buy_menu_scroll_position() > slot:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("Down")
            yield

        yield from wait_until_task_is_active(select_quantity_task, "A")

        reverse_scroll = quantity > 50
        if reverse_scroll:
            context.emulator.press_button("Down")
            yield
            yield
        while get_task(select_quantity_task).data_value(1) != quantity:
            current_quantity = get_task(select_quantity_task).data_value(1)
            if abs(current_quantity - quantity) > 7:
                context.emulator.press_button("Left" if reverse_scroll else "Right")
            else:
                context.emulator.press_button("Down" if reverse_scroll else "Up")
            yield

        yield from wait_until_task_is_active(buy_menu_task, "A")
        yield
        yield

    yield from wait_for_task_to_start_and_finish(return_task, "B")
    yield from wait_until_task_is_active(shop_menu_task)
    yield


@debug.track
def sell_in_shop(items_to_sell: list[tuple[Item, int]]):
    """
    This can be used to walk through the Mart's selling menu and sell one or more
    items from the player's item bag.

    It expects the _main menu_ of the Mart to be open (the one where it asks Buy/Sell/Leave.)

    Call it like this:
    ```python
    yield from sell_in_shop([
        (get_item_by_name("Moon Stone"), 1),
        (get_item_by_name("Nugget"), 5),
    ])
    ```

    :param items_to_sell: A list of tuples where the first entry is the item to sell,
                          and the second one the quantity. If multiple stacks of this
                          item exist in the item menu, this function will automatically
                          go through as many stacks as necessary to reach the desired
                          quantity.
    """

    if context.rom.is_rs:
        shop_menu_task = "Task_DoBuySellMenu"
        sell_menu_cb2 = "SUB_80A3118"
        select_quantity_task = "Task_BuyHowManyDialogueHandleInput"
        select_quantity_index = 1
        sell_menu_task = "sub_80A50C8"
        return_task = "Task_ReturnToMartMenu"
    else:
        shop_menu_task = "Task_ShopMenu"
        sell_menu_cb2 = "CB2_BAGMENURUN"
        if context.rom.is_emerald:
            select_quantity_task = "Task_BuyHowManyDialogueHandleInput"
        else:
            select_quantity_task = "Task_SelectQuantityToSell"
        select_quantity_index = 8
        sell_menu_task = "Task_BagMenu_HandleInput"
        return_task = "Task_ReturnToShopMenu"

    if not task_is_active(shop_menu_task):
        raise BotModeError(f"Cannot sell things in mart because `{shop_menu_task}` is not active.")

    player_items = get_item_bag()
    for item, quantity in items_to_sell:
        if player_items.quantity_of(item) < quantity:
            raise BotModeError(
                f"Cannot sell {quantity}× {item.name} because player only owns {player_items.quantity_of(item)}."
            )
        if item.pocket is ItemPocket.KeyItems:
            raise BotModeError(f"Cannot sell {item.name} because it is a key item.")
        if item.pocket is ItemPocket.TmsAndHms and item.name.startswith("HM"):
            raise BotModeError(f"Cannot sell {item.name} because it is an HM.")

    # Scroll to the 'Sell' option
    while get_mart_main_menu_scroll_position() != 1:
        if get_mart_main_menu_scroll_position() > 1:
            context.emulator.press_button("Up")
        else:
            context.emulator.press_button("Down")
        yield

    # Wait for Sell menu to open
    context.emulator.press_button("A")
    while get_game_state_symbol() != sell_menu_cb2:
        yield
    for _ in range(25):
        yield

    for item, quantity in items_to_sell:
        already_sold = 0
        while already_sold < quantity:
            pocket = get_item_bag().pocket_for(item)
            slot = get_item_bag().first_slot_index_for(item)
            slot_quantity = pocket[slot].quantity

            if slot_quantity > quantity - already_sold:
                to_sell = quantity - already_sold
            else:
                to_sell = slot_quantity

            yield from scroll_to_item_in_bag(item)
            context.emulator.press_button("A")
            yield from wait_until_task_is_active(select_quantity_task)
            reverse_scroll = to_sell > slot_quantity / 2
            if reverse_scroll:
                context.emulator.press_button("Down")
                yield
                yield
            while get_task(select_quantity_task).data_value(select_quantity_index) != to_sell:
                current_quantity = get_task(select_quantity_task).data_value(select_quantity_index)
                if abs(current_quantity - to_sell) > 7:
                    context.emulator.press_button("Left" if reverse_scroll else "Right")
                else:
                    context.emulator.press_button("Down" if reverse_scroll else "Up")
                yield
            yield from wait_until_task_is_active(sell_menu_task, "A")
            yield

            already_sold += to_sell

    yield from wait_for_task_to_start_and_finish(return_task, "B")
    yield from wait_until_task_is_active(shop_menu_task)
    yield
