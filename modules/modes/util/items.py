from typing import Generator

from modules.battle_evolution_scene import handle_evolution_scene
from modules.battle_move_replacing import handle_move_replacement_dialogue
from modules.battle_strategies import DefaultBattleStrategy, BattleStrategy
from modules.context import context
from modules.debug import debug
from modules.items import Item, ItemPocket, get_item_bag, get_item_by_name, get_item_by_move_id
from modules.memory import GameState, get_event_flag, get_game_state, read_symbol, unpack_uint16, get_event_var
from modules.menuing import StartMenuNavigator, scroll_to_item_in_bag as real_scroll_to_item, is_fade_active
from modules.modes._interface import BotModeError
from modules.player import get_player
from modules.pokemon import LearnedMove
from modules.pokemon_party import get_party, get_party_size, PartyPokemon
from modules.tasks import task_is_active
from ._util_helper import isolate_inputs
from .sleep import wait_for_n_frames
from .tasks_scripts import wait_for_task_to_start_and_finish, wait_until_task_is_active


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
def use_item_from_bag(item: Item, wait_for_start_menu_to_reappear: bool = True) -> Generator:
    if get_game_state() is not GameState.BAG_MENU:
        yield from StartMenuNavigator("BAG").step()
    yield from scroll_to_item_in_bag(item)

    if context.rom.is_rs:
        confirmation_menu_task = "sub_80A5414"
        start_menu_task = "sub_80712B4"
    elif context.rom.is_emerald:
        confirmation_menu_task = "Task_ItemContext_MultipleRows"
        start_menu_task = "Task_ShowStartMenu"
    else:
        confirmation_menu_task = "Task_FieldItemContextMenuHandleInput"
        start_menu_task = "Task_StartMenuHandleInput"

    yield from wait_for_task_to_start_and_finish(confirmation_menu_task, "A")
    if wait_for_start_menu_to_reappear:
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
    if get_event_var("REPEL_STEP_COUNT") > 0:
        return

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


def repel_is_active() -> bool:
    """
    Checks if a Repel is currently active.

    Returns:
        bool: True if the Repel is active (REPEL_STEP_COUNT > 0), False otherwise.
    """
    repel_step_count = get_event_var("REPEL_STEP_COUNT")
    return repel_step_count > 0


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

    if hm_or_tm.tm_hm_move_id is None:
        raise BotModeError(f"{hm_or_tm.name} is not a TM or HM.")

    if get_item_bag().quantity_of(hm_or_tm) == 0:
        raise BotModeError(f"Cannot teach {hm_or_tm.name} because the player does not own it.")

    party = get_party()
    if len(party) <= party_index:
        raise BotModeError(
            f"Cannot teach {hm_or_tm.name} to party Pokémon #{party_index} because there aren't that many Pokémon in the party."
        )

    target = get_party()[party_index]
    if not target.species.can_learn_tm_hm(hm_or_tm):
        raise BotModeError(f"{target.name} is not able to learn {hm_or_tm.tm_hm_move().name}.")

    for index in range(len(target.moves)):
        learned_move = target.moves[index]
        if index == move_index_to_replace and learned_move is not None:
            move_item = get_item_by_move_id(learned_move.move.index)
            if move_item is not None and move_item.name.startswith("HM"):
                raise BotModeError(
                    f"{target.name} cannot forget move #{move_index_to_replace} ({learned_move.move.name}) because it is an HM move."
                )
        elif learned_move.move.index == hm_or_tm.tm_hm_move_id:
            raise BotModeError(f"{target.name} cannot learn move {learned_move.move.name} because it already knows it.")

    target_move: LearnedMove | None = target.moves[move_index_to_replace]
    if target.moves[3] is not None and target_move is not None:
        move_item = get_item_by_move_id(target_move.move.index)
        if move_item is not None and move_item.name.startswith("HM"):
            raise BotModeError(
                f"{target.name} cannot forget move #{move_index_to_replace} ({target_move.move.name}) because it is an HM move."
            )

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
            current_slot_index = context.emulator.read_bytes(0x0202002F + get_party_size() * 136 + 3, length=1)[0]
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
            yield from wait_for_n_frames(4 if context.rom.is_rse else 15)
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


def apply_rare_candy(
    target: PartyPokemon,
    quantity: int = 1,
    battle_strategy: BattleStrategy | None = None,
    allow_evolution: bool | None = None,
) -> Generator:
    """
    Applies one or more Rare Candy to a party Pokémon and will handle
    any evolution or move-learning dialogue, too.

    :param target: The party member that should receive the Candy.
    :param quantity: Amount of candy to give.
    :param battle_strategy: The battle strategy to use for determining
                            whether an evolution should happen, and
                            which moves to replace.
    :param allow_evolution: If used, this serves as an override to the
                            battle strategy's decision on whether to
                            allow the Pokémon to evolve.
    :return:
    """

    rare_candies_in_inventory = get_item_bag().quantity_of(get_item_by_name("Rare Candy"))
    if rare_candies_in_inventory < quantity:
        raise BotModeError(
            f"Cannot use {quantity} Rare Candies because there are only {rare_candies_in_inventory} in the Item Bag."
        )

    if target.is_egg:
        raise BotModeError("Cannot use Rare Candies because the target is an egg.")

    if target.level >= 100:
        raise BotModeError("Cannot use Rare Candies because the target is already at level 100.")

    if battle_strategy is None:
        battle_strategy = DefaultBattleStrategy()

    close_bag_after = False
    if get_game_state() is not GameState.BAG_MENU:
        close_bag_after = True
        yield from StartMenuNavigator("BAG").step()

    for _ in range(quantity):
        yield from scroll_to_item_in_bag(get_item_by_name("Rare Candy"))

        while get_game_state() != GameState.PARTY_MENU:
            context.emulator.press_button("A")
            yield

        # Select the target Pokémon in Party Menu
        while True:
            if context.rom.is_rs:
                current_slot_index = context.emulator.read_bytes(0x0202002F + get_party_size() * 136 + 3, length=1)[0]
            else:
                current_slot_index = read_symbol("gPartyMenu", offset=9, size=1)[0]
            if current_slot_index < target.index:
                context.emulator.press_button("Down")
                yield
            elif current_slot_index > target.index:
                context.emulator.press_button("Up")
                yield
            else:
                break

        while True:
            if task_is_active("Task_HandleReplaceMoveYesNoInput") or task_is_active("sub_806F390"):
                yield from handle_move_replacement_dialogue(battle_strategy)
            if task_is_active("Task_EvolutionScene"):
                yield from handle_evolution_scene(battle_strategy, allow_evolution=allow_evolution)
            if get_game_state() is GameState.BAG_MENU and not is_fade_active():
                break
            context.emulator.press_button("A")
            yield

    if close_bag_after:
        if context.rom.is_rs:
            start_menu_task = "sub_80712B4"
        elif context.rom.is_emerald:
            start_menu_task = "Task_ShowStartMenu"
        else:
            start_menu_task = "Task_StartMenuHandleInput"

        yield from wait_for_task_to_start_and_finish(start_menu_task, "B")
        yield
