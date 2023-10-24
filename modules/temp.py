from modules.config import config
from modules.gui import get_emulator
from modules.memory import read_symbol, GameState, get_game_state, unpack_uint32


def temp_run_from_battle():  # TODO temporary until auto-battle is fleshed out
    while unpack_uint32(read_symbol("gActionSelectionCursor")) != 1 and config["general"]["bot_mode"] != "manual":
        get_emulator().press_button("B")
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
        get_emulator().press_button("Right")
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while unpack_uint32(read_symbol("gActionSelectionCursor")) != 3 and config["general"]["bot_mode"] != "manual":
        get_emulator().press_button("Down")
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while get_game_state() == GameState.BATTLE and config["general"]["bot_mode"] != "manual":
        get_emulator().press_button("A")
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    while get_game_state() != GameState.OVERWORLD and config["general"]["bot_mode"] != "manual":
        get_emulator().press_button("B")
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
    for _ in range(10):  # Wait for the battle fade transition # TODO check when trainer becomes controllable instead
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
