import json
import logging
import os
from typing import *

from modules.Inputs import PressButton, WaitFrames
from modules.Memory import ReadSymbol, GetTrainer
from modules.data.GameState import GameState

log = logging.getLogger(__name__)
print(os.getcwd())
with open("./modules/data/types.json") as f:
    type_list = json.load(f)
with open("./modules/data/pokemon.json") as f:
    pokemon_list = json.load(f)


def select_battle_option(desired_option: int, cursor_type: str = "gActionSelectionCursor") -> NoReturn:
    """
    Takes a desired battle menu option, navigates to it, and presses it.

    :param desired_option: The desired index for the selection. For the base battle menu, 0 will be FIGHT, 1 will be
    BAG, 2 will be PKMN, and 3 will be RUN.
    :param cursor_type: The symbol to use for the cursor. This is different between selecting moves and selecting battle
     options.
    """
    while ReadSymbol(cursor_type)[0] != desired_option:
        log.info(f"Current cursor position is {ReadSymbol(cursor_type)[0]}, and desired position is {desired_option}")
        presses = []
        match (ReadSymbol(cursor_type)[0] % 2) - (desired_option % 2):
            case - 1:
                PressButton(["Right"])
                presses.append("right")
            case 1:
                PressButton(["Left"])
                presses.append("left")
        match (ReadSymbol(cursor_type)[0] // 2) - (desired_option // 2):
            case - 1:
                PressButton(["Down"])
                presses.append("down")
            case 1:
                PressButton(["Up"])
                presses.append("up")
            case 0:
                pass
            case _:
                log.info(f"Value {desired_option} is out of bounds.")
        log.info(f"Pressed buttons {' and '.join(presses)}.")
    if ReadSymbol(cursor_type)[0] == desired_option:
        # wait a few frames to ensure the press is received
        WaitFrames(10)
        PressButton(['A'])


def FleeBattle() -> NoReturn:
    """
    Readable function to select and execute the Run option from the battle menu.
    """
    select_battle_option(3, cursor_type='gActionSelectionCursor')
    while GetTrainer()['state'] != GameState.OVERWORLD:
        PressButton(["B"])
