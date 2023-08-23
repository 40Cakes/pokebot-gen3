from typing import NoReturn

from modules.Inputs import PressButton, WaitFrames
from modules.Memory import ReadSymbol, GetTrainer, pokemon_list, type_list
from modules.data.GameState import GameState


def SelectBattleOption(desired_option: int, cursor_type: str = "gActionSelectionCursor") -> NoReturn:
    """
    Takes a desired battle menu option, navigates to it, and presses it.

    :param desired_option: The desired index for the selection. For the base battle menu, 0 will be FIGHT, 1 will be
    BAG, 2 will be PKMN, and 3 will be RUN.
    :param cursor_type: The symbol to use for the cursor. This is different between selecting moves and selecting battle
     options.
    """
    while ReadSymbol(cursor_type)[0] != desired_option:
        match (ReadSymbol(cursor_type)[0] % 2) - (desired_option % 2):
            case - 1:
                PressButton(["Right"])
            case 1:
                PressButton(["Left"])
        match (ReadSymbol(cursor_type)[0] // 2) - (desired_option // 2):
            case - 1:
                PressButton(["Down"])
            case 1:
                PressButton(["Up"])
            case 0:
                pass
    if ReadSymbol(cursor_type)[0] == desired_option:
        # wait a few frames to ensure the press is received
        WaitFrames(10)
        PressButton(['A'])


def FleeBattle() -> NoReturn:
    """
    Readable function to select and execute the Run option from the battle menu.
    """
    SelectBattleOption(3, cursor_type='gActionSelectionCursor')
    while GetTrainer()['state'] != GameState.OVERWORLD:
        PressButton(["B"])
