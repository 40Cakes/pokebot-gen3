import struct

from modules.Config import config
from modules.Gui import GetEmulator
from modules.Memory import ReadSymbol, GameState, GetGameState


def temp_RunFromBattle():  # TODO temporary until auto-battle is fleshed out
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1 and \
            config['general']['bot_mode'] != 'manual':
        GetEmulator().PressButton('B')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
        GetEmulator().PressButton('Right')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3 and \
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
