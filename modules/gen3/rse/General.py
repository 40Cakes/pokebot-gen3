import struct
import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames
from modules.Files import WriteFile
from modules.Memory import GetTrainer, GetOpponent, OpponentChanged, TrainerState, ReadSymbol, GetParty
from modules.Stats import EncounterPokemon, GetRNGStateHistory, SaveRNGStateHistory



def ModeSpin():
    try:
        while True:
            if OpponentChanged():
                while GetTrainer()['state'] != TrainerState.MISC_MENU:
                    continue
                EncounterPokemon(GetOpponent())
            directions = ['Up', 'Right', 'Down', 'Left']
            CurrentFace = GetTrainer()['facing']
            directions.remove(GetTrainer()['facing'])
            PressButton([random.choice(directions)])
            NewFace = GetTrainer()['facing']
            WaitFrames(6)
            if CurrentFace == NewFace:
                PressButton([random.choice(directions)])
                NewFace = GetTrainer()['facing']
                WaitFrames(6)

    except Exception:
        console.print_exception()

def Starter(choice: str):
    try:
        RNGStateHistory = GetRNGStateHistory(GetTrainer()['tid'], choice)

        while True:
            x = 0
            while ReadSymbol('sStarterLabelWindowId') != b'\x01\x00':
                PressButton(['A'], 10)
            while ReadSymbol('sStarterLabelWindowId') == b'\xFF\x00':
                PressButton(['B'], 10)
            while ReadSymbol('sStarterLabelWindowId') == b'\x01\x00':
                match choice:
                    case 'torchic':
                        None
                    case 'mudkip':
                        PressButton(['Right'], 10)
                    case 'treecko':
                        PressButton(['Left'], 10)
                PressButton(['A'], 10)
            while ReadSymbol('gTasks', size=1) != b'\x01':
                pass
            while True:
                RNG = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
                if RNG not in RNGStateHistory['rng']:
                    PressButton(['A'], 1)
                    RNGStateHistory['rng'].append(RNG)

                    while ReadSymbol('gTasks', size=1) != b'\x0D':
                        PressButton(['A'], 1)
                        break
                    SaveRNGStateHistory(GetTrainer()['tid'], choice, RNGStateHistory)
                    break
            while ReadSymbol('gDisplayedStringBattle', size=4) != b'\xd1\xdc\xd5\xe8':
                PressButton(['B'], 1)
            EncounterPokemon(GetParty()[0])
            EncounterPokemon(GetOpponent())
            while ReadSymbol('sStarterLabelWindowId') != b'\x00\x00':
                PressButton(['A', 'B', 'Start', 'Select'], 1)
    except Exception:
        console.print_exception()

def FRLGStarter(Choice):
    try:
        ListOfRngSeeds = []
        while True:
            Out = 0
            RNG = ReadSymbol('gRngValue', size = 4)
            while RNG in ListOfRngSeeds:
                RNG = ReadSymbol('gRngValue', size = 4)
            ListOfRngSeeds.append(RNG)
            while ReadSymbol('gStringVar4', size = 4) != b'\xbe\xe3\x00\xed':
                PressButton(['A'],10)
            while GetTrainer()['facing'] != 'Down':
                PressButton(['B'],10)
                PressButton(['Down'],10)
            i = 0
            while i < 5:
                PressButton(['Down'],10)
                i = i + 1
            while Out == 0:
                if ReadSymbol('gDisplayedStringBattle', size = 4) == b'\xc9\xbb\xc5\xf0':
                    Out = 1
                PressButton(['Left'],10)
                PressButton(['Down'],10)
                PressButton(['B'],10)


                    #log.info(ReadSymbol('gSpriteCoordOffsetX', size = 1))
            # while ReadSymbol('gDisplayedStringBattle', size = 4) != b'\xd1\xdc\xd5\xe8':
            #     PressButton((['Down'],10))
            #     PressButton((['B'],10))
            EncounterPokemon(GetParty()[0])
            while ReadSymbol('gDisplayedStringBattle', size = 4) != b'\x00\x00\x00\x00':
                PressButton(['A','B','Start','Select'], 1)

    except Exception:
        console.print_exception()
