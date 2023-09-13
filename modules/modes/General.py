import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames, ReleaseInputs
from modules.Memory import GetTask, GetTrainer, GetAddress


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


def ModeFishing():
    PressButton(["Select"], 3)
    fishing_task = GetAddress("Task_Fishing")
    active_task_offset = 4
    sub_task_offset = 8
    task = GetTask(fishing_task)
    while task != None and task[active_task_offset] == 1:
        # Check if in `Fishing_WaitForA` or `Fishing_StartEncounter` or `Fishing_EndNoMon`
        if task[sub_task_offset] == 7 or task[sub_task_offset] == 10 or task[sub_task_offset] == 15:
            PressButton(["A"])
        task = GetTask(fishing_task)
