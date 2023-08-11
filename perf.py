from modules.Memory import GetFrameCount

while True:
    start = GetFrameCount()
    while GetFrameCount() == start:
        pass
    if GetFrameCount() > start + 1: print("Missed a frame!")