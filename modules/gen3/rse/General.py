import os
import json
import time
import struct
import random
import logging

from modules.Inputs import PressButton
from modules.Memory import GetParty, GetTrainer, GetOpponent, OpponentChanged, ReadSymbol, ParseString

log = logging.getLogger(__name__)


def ModeSpin():
    try:
        #print(json.dumps(GetTrainer(), indent=2))
        #print(json.dumps(GetParty(), indent=2))
        #print(json.dumps(GetOpponent(), indent=2))

        while True:
            #if OpponentChanged(): EncounterPokemon()
            if OpponentChanged():
                while b'\xd1\xdc\xd5\xe8\x00\xeb\xdd\xe0\xe0' != ReadSymbol('gDisplayedStringBattle', size=9):
                    PressButton((['B'], 1))
                if(GetOpponent()['shiny']):
                    log.info('Shiny found!')
                    input('Press enter to continue...')
                    os._exit(0)
                while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1:
                    PressButton((['Right'], 1))
                while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3:
                    PressButton((['Down'], 1))
                while b'\xd1\xdc\xd5\xe8\x00\xeb\xdd\xe0\xe0' == ReadSymbol('gDisplayedStringBattle', size=9):
                    PressButton((['A'], 1))
                while GetTrainer()['state'] != 80:
                    PressButton((['B'], 1))
            directions = ['Up', 'Right', 'Down', 'Left']
            directions.remove(GetTrainer()['facing'])
            PressButton(([random.choice(directions)], 1))
    except Exception as e:
        log.exception(str(e))
