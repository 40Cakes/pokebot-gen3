import struct
from typing import NoReturn

from modules.Config import config
from modules.Gui import GetEmulator
from modules.Memory import GetGameState, GameState


press = 0
held = 0
input_map = {
    'A': 0x1,
    'B': 0x2,
    'Select': 0x4,
    'Start': 0x8,
    'Right': 0x10,
    'Left': 0x20,
    'Up': 0x40,
    'Down': 0x80,
    'R': 0x100,
    'L': 0x200
}


def GetInputs() -> int:
    return GetEmulator().GetInputs()


def WriteInputs(value: int) -> None:
    """
    Writes inputs to mGBA input memory, 2 bytes, each bit controls a different button (see input_map).

    Examples:
    0000 0000 0000 0001 = A press
    0000 0000 0000 0010 = B press
    0000 0000 0000 0011 = A+B press
    0000 0001 0000 0000 = R press
    0000 0010 0000 0000 = L press
    0000 0011 0000 0011 = A+B+R+L press
    etc.

    :param value: inputs to write to mGBA memory
    """
    if config['general']['bot_mode'] != 'manual':
        GetEmulator().SetInputs(value)


def WaitFrames(frames: int) -> None:
    """
    Waits for n frames to pass before continuing.

    :param frames: number of frames to wait
    """
    for i in range(frames):
        GetEmulator().RunSingleFrame()


def ReleaseInputs() -> None:
    global press
    global held
    press, held = 0, 0
    WriteInputs(0)
    WaitFrames(1)


def PressButton(buttons: list, hold_frames: int = 1) -> None:
    """
    Press a button or multiple buttons for 1 frame unless specified.
    If `hold_frames` is set to 0, the function will return and the buttons will be held down indefinitely.
    Inputs are cumulative, any buttons being held down from previous calls will be preserved.

    Example:
    > Frame n
    > Write inputs
    > Wait until frame n+1 to allow the game to register the inputs
    > Clear inputs
    > Wait until frame n+2 to allow the game to register release of inputs

    :param buttons: list of buttons to press
    :param hold_frames: hold the buttons for n frames
    """
    global press
    global held
    for button in buttons:
        if button in input_map:
            press |= input_map[button]
    press |= held
    WriteInputs(press)

    if hold_frames > 0:
        press = 0
        WaitFrames(hold_frames)
        WriteInputs(held)
        WaitFrames(1)


def ResetGame() -> None:
    while GetGameState() != GameState.TITLE_SCREEN:
        PressButton(['A', 'B', 'Start', 'Select'], 5)
