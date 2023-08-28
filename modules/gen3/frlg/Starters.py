import struct
from modules.Console import console
from modules.Inputs import PressButton
from modules.Memory import GetTrainer, ReadSymbol, GetParty
from modules.Navigation import FollowPath
from modules.Stats import GetRNGStateHistory, SaveRNGStateHistory, EncounterPokemon


def Starters(choice: str):
    try:
        RNGStateHistory = GetRNGStateHistory(GetTrainer()['tid'], choice)
        while True:
            RNG = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
            while RNG in RNGStateHistory['rng']:
                RNG = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
            RNGStateHistory['rng'].append(RNG)
            SaveRNGStateHistory(GetTrainer()['tid'], choice, RNGStateHistory)

            while ReadSymbol('gStringVar4', size=4) != b'\xbe\xe3\x00\xed':
                PressButton(['A'])

            while GetTrainer()['facing'] != 'Down':
                PressButton(['B', 'Down'])

            FollowPath([
                (8, 7),
                (7, 7),
                (7, 8)
            ])

            while GetTrainer()['state'] != 3:
                PressButton(['B'])

            EncounterPokemon(GetParty()[0])
            while ReadSymbol('gDisplayedStringBattle', size=4) != b'\x00\x00\x00\x00':
                PressButton(['A', 'B', 'Start', 'Select'], 1)

    except Exception:
        console.print_exception()
