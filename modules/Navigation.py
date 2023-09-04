from modules.data.MapData import mapRSE  #TODO mapFRLG
from modules.Inputs import PressButton, WaitFrames, ReleaseInputs
from modules.Memory import mGBA, GetTrainer, OpponentChanged

if mGBA.game in ['Pokémon Ruby', 'Pokémon Sapphire', 'Pokémon Emerald']:  # "Ruby", "Sapphire"
    MapDataEnum = mapRSE
#else:
#    MapDataEnum = mapFRLG


def FollowPath(coords: list, run: bool = True):
    for x, y, *map_data in coords:
        if run:
            PressButton(['B'], 0)

        # TODO check if trainer gets stuck, re-attempt previous tuple of coords in the list
        while True:
            trainer = GetTrainer()

            if OpponentChanged():
                return False # TODO

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