import logging

from modules.Memory import GetFrameCount, WriteInputs

log = logging.getLogger(__name__)

input_map = {
    "A": 1,
    "B": 2,
    "Select": 4,
    "Start": 8,
    "Right": 16,
    "Left": 32,
    "Up": 64,
    "Down": 128,
    "R": 256,
    "L": 512
}

def PressButton(buttons: tuple):
    inputs = 0
    for button in buttons[0]:
        if button in input_map:
            inputs |= input_map[button]
    WriteInputs(inputs)
    start = GetFrameCount()
    while GetFrameCount() < start + buttons[1]: pass
    WriteInputs(0)
    while GetFrameCount() < start + buttons[1] + 1: pass
