import struct

from modules.Gui import GetEmulator
from modules.Memory import ReadSymbol, GameState, GetGameState


def temp_RunFromBattle():  # TODO temporary until auto-battle is fleshed out
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1:
        GetEmulator().PressButton('B')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
        GetEmulator().PressButton('Right')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3:
        GetEmulator().PressButton('Down')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while GetGameState() == GameState.BATTLE:
        GetEmulator().PressButton('A')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
    while GetGameState() != GameState.OVERWORLD:
        GetEmulator().PressButton('B')
        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
