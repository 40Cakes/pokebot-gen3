import random
from modules.Console import console
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import GetTrainer, GetOpponent, OpponentChanged, TrainerState, ReadSymbol, GetParty
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

def Starter(Choice):
    try:
        ListOfRngSeeds = []
        while True:
            x = 0
            # i = i + 1
            while ReadSymbol('sStarterLabelWindowId') != b'\x01\x00':
                PressButton(['A'],10)
            while ReadSymbol('sStarterLabelWindowId') == b'\xFF\x00':
                PressButton(['B'],10)
            while ReadSymbol('sStarterLabelWindowId') == b'\x01\x00':
                match Choice:
                    case 'torchic':
                        None
                    case 'mudkip':
                        PressButton(['Right'],10)
                    case 'treecko':
                        PressButton(['Left'],10)
                PressButton(['A'],10)
            while ReadSymbol('gTasks', size = 1) != b'\x01':
                None
            while x != 1:
                RNG = ReadSymbol('gRngValue', size = 4)
                if RNG not in ListOfRngSeeds:
                    PressButton(['A'], 1)
                    ListOfRngSeeds.append(RNG)
                    #log.info(ReadSymbol('gRngValue', size = 4))

                    while ReadSymbol('gTasks', size = 1) != b'\x0D':
                        PressButton(['A'],1)
                        x = 1
            while ReadSymbol('gDisplayedStringBattle', size=4) != b'\xd1\xdc\xd5\xe8':
                PressButton(['B'], 1)
            EncounterPokemon(GetParty()[0])
            # if(GetParty()[0]['shiny']):
            #     #log.info('Shiny found!')
            #     input('Press enter to continue...')
            #     os._exit(0)
            EncounterPokemon(GetOpponent())
            while ReadSymbol('sStarterLabelWindowId') != b'\x00\x00':
                PressButton(['A', 'B', 'Start', 'Select'], 1)
    except Exception:
        console.print_exception()
