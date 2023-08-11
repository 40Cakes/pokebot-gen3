from modules.Memory import GetFrameCount

while True:
    start = GetFrameCount()
    while GetFrameCount() == start:
        #print(GetFrameCount())
        pass
    if GetFrameCount() > start + 1: print("Missed a frame!")