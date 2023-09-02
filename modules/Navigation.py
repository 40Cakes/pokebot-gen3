from modules.data.MapData import mapRSE  #TODO mapFRLG
from modules.Inputs import PressButton, WaitFrames, WriteInputs
from modules.Memory import mGBA, GetOpponent, GetTrainer, OpponentChanged
from modules.Stats import EncounterPokemon

if mGBA.game in ['Pokémon Ruby', 'Pokémon Sapphire', 'Pokémon Emerald']:  # "Ruby", "Sapphire"
    MapDataEnum = mapRSE
#else:
#    MapDataEnum = mapFRLG


def FollowPath(coords: list, run: bool = True, encounter_opponent: bool = True):
    for x, y, *map_data in coords:
        if run:
            PressButton(['B'], 0)

        # TODO check if trainer gets stuck, re-attempt previous tuple of coords in the list
        while True:
            trainer = GetTrainer()

            if encounter_opponent and OpponentChanged():
                EncounterPokemon(GetOpponent())

            # Check if map changed to desired map
            if map_data:
                if trainer['mapBank'] == map_data[0][0] and trainer['mapId'] == map_data[0][1]:
                    WriteInputs(0)
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
                WriteInputs(0)
                break

            PressButton([direction], 0)
            WaitFrames(1)

    WriteInputs(0)
    return True