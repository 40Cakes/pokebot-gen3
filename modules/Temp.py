import struct

from modules.Inputs import PressButton
from modules.Memory import GetTask, ReadSymbol, GameState, GetGameState, EncodeString

b_What = EncodeString('What')  # TODO temporary fix (English only) for fishing in Safari Zone
def temp_RunFromBattle():  # TODO temporary until auto-battle is fleshed out
    while GetTask('TASK_PLAYCRYWHENRELEASEDFROMBALL') == {} and GetTask('SUB_8046AD0') == {} and \
        ReadSymbol('gDisplayedStringBattle', size=4) != b_What:  # TODO temporary fix (English only) for fishing in Safari Zone
        PressButton(['B'])
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1:
        PressButton(['Right'])
    while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3:
        PressButton(['Down'])
    while GetGameState() == GameState.BATTLE:
        PressButton(['A'])
    while GetGameState() != GameState.OVERWORLD:
        PressButton(['B'])
