import random
import logging
from modules.Inputs import PressButton
from modules.Memory import GetTrainer, GetOpponent, OpponentChanged, TrainerState
from modules.Stats import EncounterPokemon

log = logging.getLogger(__name__)


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
    except Exception as e:
        log.exception(str(e))
