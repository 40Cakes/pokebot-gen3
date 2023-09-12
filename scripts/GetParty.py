# Prints trainer data if it changes, on a loop (good for finding X,Y coords)
# Move this script to the root directory to ensure all imports work correctly

from modules.Inputs import WaitFrames
from modules.Memory import GetParty

prev_party = {}
while True:
    current_party = GetParty()
    if current_party != prev_party:
        prev_party = current_party
        print(prev_party)
    WaitFrames(1)
