# Prints trainer data if it changes, on a loop (good for finding X,Y coords)
# Move this script to the root directory to ensure all imports work correctly

from modules.Inputs import WaitFrames
from modules.Trainer import GetTrainer

prev_trainer = {}
while True:
    current_trainer = GetTrainer()
    if current_trainer != prev_trainer:
        prev_trainer = current_trainer
        print(prev_trainer)
    WaitFrames(1)
