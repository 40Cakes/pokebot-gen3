from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.memory import read_symbol


def _select_in_menu(cursor_symbol: str, target_index: int, use_third_byte: bool = False) -> Generator:
    if target_index < 0 or target_index > 3:
        raise ValueError(f"Menu index must be a number between 0 and 3. '{target_index}' given.")

    first_iteration = True
    while True:
        current_index = read_symbol(cursor_symbol, size=4)

        # In double battles, for the right-side Pokémon the 3rd byte of the index is used,
        # otherwise it's the 1st byte.
        if use_third_byte:
            current_index = current_index[2]
        else:
            current_index = current_index[0]

        if current_index == target_index:
            # If this function is called when the cursor is already pointing at the target,
            # in some edge cases we need to wait another frame until the UI becomes responsive.
            # This is _usually_ not necessary, but waiting that extra frame fixes the edge
            # case so here we go.
            if first_iteration:
                yield
            break
        else:
            if current_index > 1 and target_index <= 1:
                context.emulator.press_button("Up")
            elif current_index <= 1 and target_index > 1:
                context.emulator.press_button("Down")
            elif current_index in (1, 3):
                context.emulator.press_button("Left")
            else:
                context.emulator.press_button("Right")
        yield
        yield
        first_iteration = False


@debug.track
def scroll_to_battle_action(action_index: int) -> Generator:
    yield from _select_in_menu("gActionSelectionCursor", action_index)


@debug.track
def scroll_to_move(move_index: int, is_right_side_pokemon: bool = False) -> Generator:
    yield from _select_in_menu("gMoveSelectionCursor", move_index, is_right_side_pokemon)
