from dataclasses import dataclass
from enum import Enum, auto
from typing import Generator

from modules.context import context
from modules.game import decode_string
from modules.memory import get_game_state, get_game_state_symbol, read_symbol, GameState, unpack_uint32
from modules.menuing import get_scroll_direction
from modules.modes import BotModeError
from modules.modes.util import (
    wait_until_task_is_active,
    wait_for_n_frames,
    wait_for_no_script_to_run,
    wait_for_player_avatar_to_be_controllable,
)
from modules.player import get_player_avatar, player_avatar_is_controllable
from modules.pokemon import Pokemon
from modules.pokemon_party import get_party, get_party_size
from modules.pokemon_storage import get_pokemon_storage
from modules.tasks import get_task


class PCStorageSection(Enum):
    WithdrawPokemon = auto()
    DepositPokemon = auto()
    MovePokemon = auto()
    MoveItems = auto()


class PCStorageActionType(Enum):
    Withdraw = auto()
    Deposit = auto()
    ReleaseFromParty = auto()
    ReleaseFromBox = auto()


class PCAction:
    def __init__(
        self, section: PCStorageSection, action: PCStorageActionType, pokemon: Pokemon, target_box: int | None = None
    ):
        self.section = section
        self.action = action
        self.pokemon = pokemon
        self.target_box = target_box

    @classmethod
    def withdraw_pokemon_from_box(cls, pokemon: Pokemon) -> "PCAction":
        return cls(PCStorageSection.WithdrawPokemon, PCStorageActionType.Withdraw, pokemon)

    @classmethod
    def deposit_pokemon_to_box(cls, pokemon: Pokemon, target_box: int | None = None) -> "PCAction":
        return cls(PCStorageSection.DepositPokemon, PCStorageActionType.Deposit, pokemon, target_box)

    @classmethod
    def release_pokemon_from_party(cls, pokemon: Pokemon) -> "PCAction":
        return cls(PCStorageSection.DepositPokemon, PCStorageActionType.ReleaseFromParty, pokemon)

    @classmethod
    def release_pokemon_from_box(cls, pokemon: Pokemon) -> "PCAction":
        return cls(PCStorageSection.MovePokemon, PCStorageActionType.ReleaseFromBox, pokemon)


@dataclass
class MenuCursor:
    cursor_position: int
    cursor_range: tuple[int, int]


def _get_menu_cursor() -> MenuCursor:
    symbol_name = "gMenu" if context.rom.is_rs else "sMenu"
    data = read_symbol(symbol_name)
    return MenuCursor(data[2], (data[3], data[4]))


def _get_storage_menu() -> list[tuple[int, str]]:
    if context.rom.is_rs:
        storage_symbol = "gPokemonStorageSystemPtr"
        offset = 0x1180
    elif context.rom.is_frlg:
        storage_symbol = "gStorage"
        offset = 0xC70
    else:
        storage_symbol = "sStorage"
        offset = 0xC74
    ptr = unpack_uint32(read_symbol(storage_symbol))
    if ptr == 0:
        return []
    data = context.emulator.read_bytes(ptr + offset, length=0x39)
    menu_length = min(7, data[0x38])
    result = []
    for index in range(menu_length):
        text_ptr = unpack_uint32(data[index * 8 : index * 8 + 4])
        if text_ptr >> 24 != 0x08:
            return []
        text_id = unpack_uint32(data[index * 8 + 4 : index * 8 + 8])
        result.append((text_id, decode_string(context.emulator.read_bytes(text_ptr, length=16))))
    return result


@dataclass
class StorageState:
    # 0 = ready for input
    state: int
    active_box: int
    selected_target_box: int
    # 0 = within the box slots area; 2 = box selection widget, 3 = party/close button
    cursor_area: int
    cursor_position: int


def _get_storage_state() -> StorageState:
    if context.rom.is_rs:
        storage_symbol = "gPokemonStorageSystemPtr"
    elif context.rom.is_frlg:
        storage_symbol = "gStorage"
    else:
        storage_symbol = "sStorage"
    ptr = unpack_uint32(read_symbol(storage_symbol))
    if ptr == 0:
        return StorageState(0, 0, 0, 0, 0)
    else:
        if context.rom.is_rs:
            state = context.emulator.read_bytes(ptr + 4, length=1)[0]
            active_box = read_symbol("gPokemonStorage", size=1)[0]
            selected_target_box = 0
        else:
            state = context.emulator.read_bytes(ptr, length=1)[0]
            active_box = context.emulator.read_bytes(ptr + 0x6FA, length=1)[0]
            if context.rom.is_rs:
                selected_target_box = context.emulator.read_bytes(ptr + 0x25AC, length=1)[0]
            elif context.rom.is_emerald:
                selected_target_box = context.emulator.read_bytes(ptr + 0x20A0, length=1)[0]
            else:
                selected_target_box = context.emulator.read_bytes(ptr + 0x209C, length=1)[0]

        return StorageState(
            state=state,
            active_box=active_box,
            selected_target_box=selected_target_box,
            cursor_area=read_symbol("sCursorArea" if not context.rom.is_rs else "sBoxCursorArea")[0],
            cursor_position=read_symbol("sCursorPosition" if not context.rom.is_rs else "sBoxCursorPosition")[0],
        )


def _get_storage_task_name() -> str:
    return "Task_PokemonStorageSystem" if context.rom.is_rs else "Task_PCMainMenu"


def _open_pc_menu(menu_index: int) -> Generator:
    while get_task(_get_storage_task_name()).data_value(0) != 2:
        yield
    while get_task(_get_storage_task_name()).data_value(1) != menu_index:
        context.emulator.press_button("Down" if get_task(_get_storage_task_name()).data_value(1) < menu_index else "Up")
        yield
    if context.rom.is_rs:
        while get_game_state_symbol() != "SUB_8096B38":
            context.emulator.press_button("A")
            yield
        yield from wait_for_n_frames(15)
    else:
        yield from wait_until_task_is_active("Task_PokeStorageMain", "A")


def _close_pc_menu() -> Generator:
    while get_game_state() is not GameState.OVERWORLD:
        context.emulator.press_button("B")
        yield


def _select_box(box_index: int) -> Generator:
    state = _get_storage_state()
    if state.active_box != box_index:
        # Navigate to the box slider
        direction = "Up" if state.cursor_area != 0 or state.cursor_position < 18 else "Down"
        while _get_storage_state().cursor_area != 2:
            context.emulator.press_button(direction)
            yield

        # Select the correct box
        direction = get_scroll_direction(_get_storage_state().active_box, box_index, total_items=14, horizontal=True)
        while _get_storage_state().active_box != box_index:
            context.emulator.press_button(direction)
            yield

        # Wait for state to be 0 (ready)
        while _get_storage_state().state != 0:
            yield


def _select_box_slot(slot_index: int) -> Generator:
    state = _get_storage_state()
    if state.cursor_area != 0 or state.cursor_position != slot_index:
        row = 2 + slot_index // 6
        column = slot_index % 6

        # Navigate to the correct row
        if state.cursor_area == 0:
            current_row = 2 + state.cursor_position // 6
        elif state.cursor_area == 2:
            current_row = 1
        else:
            current_row = 0

        direction = get_scroll_direction(current_row, row, total_items=7)
        while (state := _get_storage_state()).cursor_area != 0 or 2 + state.cursor_position // 6 != row:
            context.emulator.press_button(direction)
            yield

        # Navigate to the correct column
        current_column = _get_storage_state().cursor_position % 6
        direction = get_scroll_direction(current_column, column, total_items=6, horizontal=True)
        while (state := _get_storage_state()).cursor_area != 0 or state.cursor_position % 6 != column:
            context.emulator.press_button(direction)
            yield

        # Wait for state to be 0 (ready)
        while _get_storage_state().state != 0:
            yield


def _select_menu_option(option_to_select: str) -> Generator:
    menu_option_map = [
        "CANCEL",
        "STORE",
        "WITHDRAW",
        "MOVE",
        "SHIFT",
        "PLACE",
        "SUMMARY",
        "RELEASE",
        "MARK",
        # more in `pokemon_storage_system.c`
    ]
    if option_to_select not in menu_option_map:
        raise BotModeError(f"Value `{option_to_select}` is not a known option.")

    available_options = _get_storage_menu()
    target_index = None
    for option_index, option in enumerate(available_options):
        if option[0] == menu_option_map.index(option_to_select):
            target_index = option_index
    if target_index is None:
        raise BotModeError(f"Option `{option_to_select}` is not available in this menu.")

    current_index = _get_menu_cursor().cursor_position
    if current_index != target_index:
        direction = get_scroll_direction(current_index, target_index, len(available_options))
        while _get_menu_cursor().cursor_position != target_index:
            context.emulator.press_button(direction)
            yield
            yield


def _do_withdraw_actions(actions: list[PCAction]) -> Generator:
    yield from _open_pc_menu(0)
    for action in actions:
        if action.action is PCStorageActionType.Withdraw:
            if get_party_size() == 6:
                raise BotModeError("Cannot withdraw any Pokémon because the party already contains 6 Pokémon.")
            box, slot = get_pokemon_storage().get_slot_for_pokemon(action.pokemon)

            yield from _select_box(box)
            yield from _select_box_slot(slot)
            while _get_storage_state().state != (2 if not context.rom.is_rs else 1):
                context.emulator.press_button("A")
                yield
            yield from _select_menu_option("WITHDRAW")
            while _get_storage_state().state != 4:
                context.emulator.press_button("A")
                yield
            while _get_storage_state().state != 0 or _get_storage_state().cursor_area != 0:
                yield
            yield

    yield from _close_pc_menu()


def _do_deposit_actions(actions: list[PCAction]) -> Generator:
    yield from _open_pc_menu(1)
    for action in actions:
        if action.action is PCStorageActionType.Deposit:
            party = get_party()
            if len(party) == 1:
                raise BotModeError("Cannot deposit that Pokémon because it's the only one in the party.")
            if len(party.non_eggs) == 1:
                raise BotModeError("Cannot deposit that Pokémon because only eggs would remain in the party.")
            if len(party.non_fainted_pokemon) == 1:
                raise BotModeError(
                    "Cannot deposit that Pokémon because only fainted Pokémon would remain in the party."
                )
            target_box = action.target_box
            if target_box is None:
                index = 0
                for box in get_pokemon_storage().boxes:
                    if box.first_empty_slot_index is not None:
                        target_box = index
                        break
                    else:
                        index += 1
            if target_box is None:
                raise BotModeError("Cannot deposit that Pokémon because all boxes are full.")

            target_index = party.get_index_for_pokemon(action.pokemon)
            direction = get_scroll_direction(_get_storage_state().cursor_position, target_index, total_items=7)
            while _get_storage_state().cursor_position != target_index:
                context.emulator.press_button(direction)
                yield
            while _get_storage_state().state != (2 if not context.rom.is_rs else 1):
                context.emulator.press_button("A")
                yield
            yield from _select_menu_option("STORE")
            if context.rom.is_rs:
                context.emulator.press_button("A")
                yield
            while _get_storage_state().state != 1:
                context.emulator.press_button("A")
                yield
            direction = get_scroll_direction(
                _get_storage_state().selected_target_box, target_box, total_items=14, horizontal=True
            )
            while _get_storage_state().selected_target_box != target_box:
                context.emulator.press_button(direction)
                yield
                yield
                if context.rom.is_rs:
                    yield
            while _get_storage_state().state != 3:
                context.emulator.press_button("A")
                yield
            while _get_storage_state().state != 0:
                yield
            yield

        if action.action is PCStorageActionType.ReleaseFromParty:
            party = get_party()
            if len(party) == 1:
                raise BotModeError("Cannot release that Pokémon because it's the only one in the party.")
            if len(party.non_eggs) == 1:
                raise BotModeError("Cannot release that Pokémon because only eggs would remain in the party.")
            if len(party.non_fainted_pokemon) == 1:
                raise BotModeError(
                    "Cannot release that Pokémon because only fainted Pokémon would remain in the party."
                )
            target_index = party.get_index_for_pokemon(action.pokemon)

            if context.rom.is_rs:
                yield from _release_from_party_rs(context, party, target_index)
            else:
                direction = get_scroll_direction(_get_storage_state().cursor_position, target_index, total_items=7)
                while _get_storage_state().cursor_position != target_index:
                    context.emulator.press_button(direction)
                    yield
                while _get_storage_state().state != 2:
                    context.emulator.press_button("A")
                    yield
                yield from _select_menu_option("RELEASE")
                context.emulator.press_button("A")
                yield
                yield
                yield
                if context.rom.is_frlg:
                    yield
                context.emulator.press_button("Up")
                yield
                if context.rom.is_frlg:
                    yield
                while _get_storage_state().state != 7:
                    context.emulator.press_button("A")
                    yield
                while _get_storage_state().state != 0:
                    yield
                yield
    yield from _close_pc_menu()


def _do_move_pokemon_actions(actions: list[PCAction]) -> Generator:
    yield from _open_pc_menu(2)
    for action in actions:
        if action.action is PCStorageActionType.ReleaseFromBox:
            box, slot = get_pokemon_storage().get_slot_for_pokemon(action.pokemon)

            yield from _select_box(box)
            yield from _select_box_slot(slot)
            while _get_storage_state().state != (2 if not context.rom.is_rs else 1):
                context.emulator.press_button("A")
                yield
            yield from _select_menu_option("RELEASE")
            context.emulator.press_button("A")
            yield
            yield
            yield
            if context.rom.is_frlg:
                yield
            context.emulator.press_button("Up")
            yield
            if context.rom.is_frlg:
                yield
            while _get_storage_state().state != 7:
                context.emulator.press_button("A")
                yield
            while _get_storage_state().state != 0:
                yield
            yield
    yield from _close_pc_menu()


def interact_with_pc(actions: list[PCAction]) -> Generator:
    targeted_tile = get_player_avatar().map_location_in_front
    if targeted_tile.tile_type != "PC":
        raise BotModeError("Player is not facing a PC.")

    if not player_avatar_is_controllable():
        raise BotModeError("Player is not controllable. Cannot interact with PC.")

    yield from wait_until_task_is_active(_get_storage_task_name(), "A")

    # Run the actions
    actions_for_withdraw_menu = [action for action in actions if action.section is PCStorageSection.WithdrawPokemon]
    if len(actions_for_withdraw_menu) > 0:
        yield from _do_withdraw_actions(actions_for_withdraw_menu)

    actions_for_deposit_menu = [action for action in actions if action.section is PCStorageSection.DepositPokemon]
    if len(actions_for_deposit_menu) > 0:
        yield from _do_deposit_actions(actions_for_deposit_menu)

    actions_for_move_pokemon_menu = [action for action in actions if action.section is PCStorageSection.MovePokemon]
    if len(actions_for_move_pokemon_menu) > 0:
        yield from _do_move_pokemon_actions(actions_for_move_pokemon_menu)

    yield from wait_for_no_script_to_run("B")
    yield from wait_for_player_avatar_to_be_controllable("B")


def _release_from_party_rs(context, party, target_index):
    """
    Handles the special release sequence for Ruby/Sapphire,
    since their storage behavior differs from other gens.
    """

    def press_and_wait(button: str, frames: int = 10):
        context.emulator.press_button(button)
        return wait_for_n_frames(frames)

    direction = get_scroll_direction(_get_storage_state().cursor_position, target_index, total_items=7)

    while _get_storage_state().cursor_position != target_index:
        context.emulator.press_button(direction)
        yield

    yield from wait_for_n_frames(10)

    yield from press_and_wait("A", 10)
    yield from press_and_wait("Up", 10)
    yield from press_and_wait("Up", 10)
    yield from press_and_wait("A", 10)
    yield from press_and_wait("Up", 10)
    yield from press_and_wait("A", 20)

    old_party_len = len(party)
    while len(get_party()) >= old_party_len:
        yield

    yield from press_and_wait("A", 10)
    yield from press_and_wait("A", 10)
    yield
