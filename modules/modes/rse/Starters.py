import random
import struct
from typing import NoReturn

from modules.Config import config_general, config_cheats
from modules.Console import console
from modules.Inputs import PressButton, ResetGame, WaitFrames
from modules.Memory import ReadSymbol, GetParty, GetOpponent, GetGameState, GameState, GetTask, mGBA, WriteSymbol
from modules.Stats import GetRNGStateHistory, SaveRNGStateHistory, EncounterPokemon


if mGBA.game == 'Pokémon Emerald':
    t_bag_cursor = 'TASK_HANDLESTARTERCHOOSEINPUT'
    t_confirm = 'TASK_HANDLECONFIRMSTARTERINPUT'
    t_ball_throw = 'TASK_PLAYCRYWHENRELEASEDFROMBALL'
else:
    t_bag_cursor = 'TASK_STARTERCHOOSE2'
    t_confirm = 'TASK_STARTERCHOOSE5'
    t_ball_throw = 'SUB_81414BC'


if not config_cheats['starters_rng']:
    rng_history = GetRNGStateHistory(config_general['starter'])

def Starters() -> NoReturn:
    try:
        while GetGameState() != GameState.CHOOSE_STARTER:
            PressButton(['A'])

        match config_general['starter']:
            case 'treecko':
                while GetTask(t_bag_cursor).get('data', ' ')[0] != 0:
                    PressButton(['Left'])
            case 'mudkip':
                while GetTask(t_bag_cursor).get('data', ' ')[0] != 2:
                    PressButton(['Right'])

        while not GetTask(t_confirm).get('isActive', False):
            PressButton(['A'], 1)

        if config_cheats['starters_rng']:
            WriteSymbol('gRngValue', struct.pack('<I', random.randint(0, 2**32 - 1)))
        else:
            rng = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])
            while rng in rng_history['rng']:
                rng = int(struct.unpack('<I', ReadSymbol('gRngValue', size=4))[0])

        PressButton(['A'])

        if config_cheats['starters']:
            while GetParty() == {}:
                PressButton(['A'])
        else:
            while GetGameState() != GameState.BATTLE:
                PressButton(['A'])

            while GetTask(t_ball_throw) == {}:
                PressButton(['B'])

            WaitFrames(60)
            EncounterPokemon(GetOpponent())

        EncounterPokemon(GetParty()[0])

        if not config_cheats['starters_rng']:
            rng_history['rng'].append(rng)
            SaveRNGStateHistory(config_general['starter'], rng_history)
        ResetGame()
    except:
        console.print_exception(show_locals=True)
