# Quick and crude way to test if Python can keep up with high frame rates in mGBA
# Move this script to the root directory to ensure all imports work correctly
from modules.Memory import emulator

while True:
    start = emulator.GetFrameCount()
    while emulator.GetFrameCount() == start:
        #print(emulator.GetFrameCount())
        pass
    if emulator.GetFrameCount() > start + 1: print('Missed a frame!')
