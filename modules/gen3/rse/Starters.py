import struct
from typing import NoReturn
from modules.Console import console
from modules.Inputs import PressButton
from modules.Memory import GetTrainer, ReadSymbol, GetParty, GetOpponent
from modules.Stats import GetRNGStateHistory, SaveRNGStateHistory, EncounterPokemon


def Starters(choice: str) -> NoReturn:
    try:
        rng_state_history = GetRNGStateHistory(GetTrainer()['tid'], choice)

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
            if RNG not in rng_state_history['rng']:
                PressButton(['A'], 1)
                rng_state_history['rng'].append(RNG)

                while ReadSymbol('gTasks', size=1) != b'\x0D':
                    PressButton(['A'], 1)
                    break
                SaveRNGStateHistory(GetTrainer()['tid'], choice, rng_state_history)
                break
        while ReadSymbol('gDisplayedStringBattle', size=4) != b'\xd1\xdc\xd5\xe8':
            PressButton(['B'], 1)

        EncounterPokemon(GetParty()[0])
        EncounterPokemon(GetOpponent())

        # TODO
        # if config_general['bot_mode'] == 'starters':
        #    if config_general['mem_hacks']['starters']:
        #        pass

        while ReadSymbol('sStarterLabelWindowId') != b'\x00\x00':
            PressButton(['A', 'B', 'Start', 'Select'], 1)
    except:
        console.print_exception(show_locals=True)
