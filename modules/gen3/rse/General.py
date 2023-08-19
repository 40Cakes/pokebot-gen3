import os
import struct
import random
import logging
from modules.Inputs import PressButton
from modules.Memory import EncodeString, GetTrainer, GetOpponent, OpponentChanged, ReadSymbol
from modules.Stats import LogEncounter

log = logging.getLogger(__name__)


def ModeSpin():
    try:
        # Search for the text "What will (Pokémon) do?" in `gDisplayedStringBattle`
        b_What = EncodeString("What")

        while True:
            #if OpponentChanged(): EncounterPokemon()
            if OpponentChanged():
                while ReadSymbol('gDisplayedStringBattle', size=4) != b_What:
                    PressButton(['B'])
                LogEncounter(GetOpponent())
                if(GetOpponent()['shiny']):
                    log.info('Shiny found!')
                    input('Press enter to continue...')
                    os._exit(0)
                while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1:
                    PressButton(['Right'])
                while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3:
                    PressButton(['Down'])
                while ReadSymbol('gDisplayedStringBattle', size=4) == b_What:
                    PressButton(['A'])
                while GetTrainer()['state'] != 80:
                    PressButton(['B'])
            directions = ['Up', 'Right', 'Down', 'Left']
            directions.remove(GetTrainer()['facing'])
            PressButton([random.choice(directions)])
    except Exception as e:
        log.exception(str(e))
