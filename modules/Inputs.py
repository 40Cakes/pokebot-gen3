import struct
import atexit
import logging
from modules.Memory import mGBA, GetFrameCount

log = logging.getLogger(__name__)

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


def WriteInputs(value: int):
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
    mGBA.proc.write_bytes(mGBA.p_Input, struct.pack('<H', value), 2)


def PressButton(buttons: list, hold_frames: int = 1):
    """
    Press a button or multiple buttons for 1 frame unless specified.
    This function requires at least 2 frames to run.
    TODO: add functionality to allow a sequence of inputs without clearing inputs and wasting 1 frame.

    Example:
    > Frame n
    > Write inputs
    > Wait until frame n+1 to allow the game to register the inputs
    > Clear inputs
    > Wait until frame n+2 to allow the game to register release of inputs

    :param buttons: list of buttons to press
    :param hold_frames: hold the buttons for n frames
    :return:
    """
    inputs = 0
    for button in buttons:
        if button in input_map:
            inputs |= input_map[button]
    WriteInputs(inputs)
    start = GetFrameCount()
    while GetFrameCount() < start + hold_frames:
        pass
    WriteInputs(0)
    while GetFrameCount() < start + hold_frames + 1:
        pass


def _exit():
    WriteInputs(0)  # Clear inputs if bot is stopped


atexit.register(_exit)
