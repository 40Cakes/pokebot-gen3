import struct
from typing import NoReturn

from modules.Config import config_cheats, config_general
from modules.Console import console
from modules.Inputs import PressButton, ResetGame
from modules.Memory import GetTrainer, ReadSymbol, GetParty, GameState, GetGameState, GetTask
from modules.Navigation import FollowPath
from modules.Stats import GetRNGStateHistory, SaveRNGStateHistory, EncounterPokemon


rng_history = GetRNGStateHistory(config_general['starter'])
def Starters() -> NoReturn:
    try:
        while GetGameState() != GameState.OVERWORLD:
            PressButton(['A'])

        rng = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
        while rng in rng_history['rng']:
            rng = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])

        while GetTask('TASK_SCRIPTSHOWMONPIC') == {}:
            PressButton(['A'])

        while GetTask('TASK_SCRIPTSHOWMONPIC') != {}:
            PressButton(['A'])

        while GetTask('TASK_FANFARE') == {}:
            PressButton(['B'])

        if config_cheats['starters']:
            while GetParty() == {}:
                PressButton(['B'])
        else:
            while GetTrainer()['facing'] != 'Down':
                PressButton(['B', 'Down'])

            FollowPath([
                (GetTrainer()['coords'][0], 7),
                (7, 7),
                (7, 8)
            ])

            while GetTask('TASK_PLAYERCONTROLLER_RESTOREBGMAFTERCRY') == {}:
                PressButton(['B'])

        EncounterPokemon(GetParty()[0])
        rng_history['rng'].append(rng)
        SaveRNGStateHistory(config_general['starter'], rng_history)
        ResetGame()
    except:
        console.print_exception(show_locals=True)
