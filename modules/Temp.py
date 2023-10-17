from modules.Config import config
from modules.Gui import GetEmulator
from modules.Memory import ReadSymbol, GameState, GetGameState, unpack_uint32


def temp_RunFromBattle():  # TODO temporary until auto-battle is fleshed out
    while unpack_uint32(ReadSymbol('gActionSelectionCursor')) != 1 and \
            config['general']['bot_mode'] != 'manual':
        GetEmulator().PressButton('B')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
        GetEmulator().PressButton('Right')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while unpack_uint32(ReadSymbol('gActionSelectionCursor')) != 3 and \
            config['general']['bot_mode'] != 'manual':
        GetEmulator().PressButton('Down')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while GetGameState() == GameState.BATTLE and \
            config['general']['bot_mode'] != 'manual':
        GetEmulator().PressButton('A')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while GetGameState() != GameState.OVERWORLD and \
            config['general']['bot_mode'] != 'manual':
        GetEmulator().PressButton('B')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    for _ in range(10):  # Wait for the battle fade transition # TODO check when trainer becomes controllable instead
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
