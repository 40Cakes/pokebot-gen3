import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames, ReleaseInputs
from modules.Memory import GetTrainer, OpponentChanged, GetOpponent
from modules.Stats import EncounterPokemon


def ModeSpin():
    try:
        # TODO home position, FollowPath() if trainer walks off
        while True:
            if OpponentChanged():
                while GetTrainer()['map'] != (0, 0):
                    continue
                EncounterPokemon(GetOpponent())
            ReleaseInputs()
            directions = ['Up', 'Right', 'Down', 'Left']
            directions.remove(GetTrainer()['facing'])
            PressButton([random.choice(directions)])
            WaitFrames(6)

    except:
        console.print_exception(show_locals=True)
