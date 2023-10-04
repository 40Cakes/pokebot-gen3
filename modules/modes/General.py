import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames, ReleaseInputs
from modules.Memory import GetTask
from modules.Trainer import GetTrainer


def ModeSpin():
    try:
        directions = ['Up', 'Right', 'Down', 'Left']
        directions.remove(GetTrainer()['facing'])
        PressButton([random.choice(directions)])
        WaitFrames(7)

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def ModeFishing():
    PressButton(['Select'], 3)
    task = GetTask('TASK_FISHING')
    while task != {} and task['isActive']:
        # Check if in `Fishing_WaitForA` or `Fishing_StartEncounter` or `Fishing_EndNoMon`
        if task['data'][0] == 7 or task['data'][0] == 10 or \
                task['data'][0] == 15:
            PressButton(["A"])
        task = GetTask('TASK_FISHING')
