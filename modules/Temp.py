import struct

from modules.Inputs import PressButton
from modules.Memory import ReadSymbol, GameState, GetGameState

def temp_RunFromBattle():  # TODO temporary until auto-battle is fleshed out
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1:
        PressButton(['B', 'Right'])
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3:
        PressButton(['Down'])
    while GetGameState() == GameState.BATTLE:
        PressButton(['A'])
    while GetGameState() != GameState.OVERWORLD:
        PressButton(['B'])
