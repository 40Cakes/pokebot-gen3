import time
import struct
from modules.Memory import mGBA
from modules.Memory import ReadSymbol

while True:
    print("gActionSelectionCursor:")
    print(struct.unpack('<I', ReadSymbol("gActionSelectionCursor"))[0])
    time.sleep(0.1)