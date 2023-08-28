import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import GetTrainer, GetOpponent, OpponentChanged, TrainerState
from modules.Stats import EncounterPokemon


def ModeSpin():
    try:
        while True:
            if OpponentChanged():
                while GetTrainer()['state'] != TrainerState.MISC_MENU:
                    continue
                EncounterPokemon(GetOpponent())
            directions = ['Up', 'Right', 'Down', 'Left']
            directions.remove(GetTrainer()['facing'])
            PressButton([random.choice(directions)])
            WaitFrames(6)

    except Exception:
        console.print_exception()
