import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames, ReleaseInputs
from modules.Memory import GetTrainer


def ModeSpin():
    try:
        # TODO home position, FollowPath() if trainer walks off
        ReleaseInputs()
        directions = ['Up', 'Right', 'Down', 'Left']
        directions.remove(GetTrainer()['facing'])  # Remove currently facing direction from possible inputs
        PressButton([random.choice(directions)])
        WaitFrames(5)

    except:
        console.print_exception(show_locals=True)
