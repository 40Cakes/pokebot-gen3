import struct
import atexit
from modules.Memory import mGBA, GetFrameCount

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


def WaitFrames(frames: int):
    """
    Waits for n frames to pass before continuing.

    :param frames: number of frames to wait
    :return: None
    """
    start = GetFrameCount()
    while GetFrameCount() < start + frames:
        pass


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
    WaitFrames(hold_frames)
    WriteInputs(0)
    WaitFrames(1)


def _exit():
    """
    Called when the bot is manually stopped or crashes.
    Clears the inputs register in the emulator so no buttons will be stuck down.

    :return: None
    """
    WriteInputs(0)


atexit.register(_exit)
