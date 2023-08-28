# Quick and crude way to test if Python can keep up with high frame rates in mGBA
# Move this script to the root directory to ensure all imports work correctly
from modules.Memory import GetFrameCount

while True:
    start = GetFrameCount()
    while GetFrameCount() == start:
        #print(GetFrameCount())
        pass
    if GetFrameCount() > start + 1: print("Missed a frame!")