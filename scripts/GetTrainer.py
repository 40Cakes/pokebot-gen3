# Prints trainer data on a loop, good for finding X,Y coords
# Move this script to the root directory to ensure all imports work correctly
import time
from modules.Memory import mGBA, GetTrainer

while True:
    print(GetTrainer())
    time.sleep(0.5)