import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import GetTrainer


def ModeSpin():
    try:
        directions = ['Up', 'Right', 'Down', 'Left']
        directions.remove(GetTrainer()['facing'])  # Remove currently facing direction from possible inputs
        PressButton([random.choice(directions)])
        WaitFrames(6)  # Trainer takes 6 frames to fully change direction after an input

    except:
        console.print_exception(show_locals=True)
