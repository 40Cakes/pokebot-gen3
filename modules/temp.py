from modules.context import context
from modules.memory import read_symbol, GameState, get_game_state, unpack_uint32


def temp_run_from_battle():  # TODO temporary until auto-battle is fleshed out
    while unpack_uint32(read_symbol("gActionSelectionCursor")) != 1 and context.bot_mode != "Manual":
        context.emulator.press_button("B")
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
        context.emulator.press_button("Right")
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while unpack_uint32(read_symbol("gActionSelectionCursor")) != 3 and context.bot_mode != "Manual":
        context.emulator.press_button("Down")
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while get_game_state() == GameState.BATTLE and context.bot_mode != "Manual":
        context.emulator.press_button("A")
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while get_game_state() != GameState.OVERWORLD and context.bot_mode != "Manual":
        context.emulator.press_button("B")
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    for _ in range(10):  # Wait for the battle fade transition # TODO check when trainer becomes controllable instead
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
