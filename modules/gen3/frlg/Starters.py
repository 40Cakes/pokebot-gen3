import struct
from typing import NoReturn
from modules.Console import console
from modules.Inputs import PressButton
from modules.Memory import GetTrainer, ReadSymbol, GetParty
from modules.Stats import GetRNGStateHistory, SaveRNGStateHistory, EncounterPokemon


def Starters(choice: str) -> NoReturn:
    try:
        RNGStateHistory = GetRNGStateHistory(choice)
        Out = 0
        RNG = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
        while RNG in RNGStateHistory['rng']:
            RNG = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
        RNGStateHistory['rng'].append(RNG)
        SaveRNGStateHistory(choice, RNGStateHistory)
        while ReadSymbol('gStringVar4', size=4) != b'\xbe\xe3\x00\xed':
            PressButton(['A'], 10)
        while GetTrainer()['facing'] != 'Down':
            PressButton(['B'], 10)
            PressButton(['Down'], 10)
        i = 0
        while i < 5:
            PressButton(['Down'],10)
            i = i + 1
        while Out == 0:
            if ReadSymbol('gDisplayedStringBattle', size=4) == b'\xc9\xbb\xc5\xf0':
                Out = 1
            PressButton(['Left'],10)
            PressButton(['Down'],10)
            PressButton(['B'],10)

        EncounterPokemon(GetParty()[0])

        # TODO
        # if config_general['bot_mode'] == 'starters':
        #    if config_general['mem_hacks']['starters']:
        #        pass

        while ReadSymbol('gDisplayedStringBattle', size=4) != b'\x00\x00\x00\x00':
            PressButton(['A', 'B', 'Start', 'Select'], 1)
    except:
        console.print_exception(show_locals=True)
