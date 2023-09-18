from modules.Inputs import PressButton, WaitFrames, ReleaseInputs
from modules.Memory import GetGameState, GameState
from modules.Temp import temp_RunFromBattle
from modules.Pokemon import OpponentChanged, GetOpponent
from modules.Stats import EncounterPokemon
from modules.Trainer import GetTrainer


def FollowPath(coords: list, run: bool = True) -> bool:
    """
    Function to walk/run the trianer through a list of coords.
    TODO check if trainer gets stuck, re-attempt previous tuple of coords in the list

    :param coords: coords (tuple) (`posX`, `posY`)
    :param run: Trainer will hold B (run) if True, otherwise trainer will walk
    :return: True if trainer (`posX`, `posY`) = the final coord of the list, otherwise False (bool)
    """
    for x, y, *map_data in coords:
        if run:
            PressButton(['B'], 0)

        while True:
            trainer = GetTrainer()

            if GetGameState() == GameState.BATTLE:
                if OpponentChanged():
                    EncounterPokemon(GetOpponent())
                temp_RunFromBattle()

            # Check if map changed to desired map
            if map_data:
                if trainer['mapBank'] == map_data[0][0] and trainer['mapId'] == map_data[0][1]:
                    ReleaseInputs()
                    break

            if trainer['coords'][0] > x:
                direction = 'Left'
            elif trainer['coords'][0] < x:
                direction = 'Right'
            elif trainer['coords'][1] < y:
                direction = 'Down'
            elif trainer['coords'][1] > y:
                direction = 'Up'
            else:
                ReleaseInputs()
                break

            PressButton([direction], 0)
            WaitFrames(1)

    ReleaseInputs()
    return True
