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
    PressButton(["Select"],3) 
    fishingTask = GetAddress("Task_Fishing")
    activeTaskOffset = 4
    subTaskOffset = 8
    fishingActive = True
    task = GetTask(fishingTask)
    while task != None and task[activeTaskOffset] == 1:
        if task[subTaskOffset] ==  7 or task[subTaskOffset] ==  10 or task[subTaskOffset] ==  15: # means we are in Fishing_WaitForA or 
            PressButton(["A"])                                                                    # Fishing_StartEncounter or Fishing_EndNoMon
        task = GetTask(fishingTask)
         
                