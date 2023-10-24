from modules.config import config
from modules.gui import get_emulator
from modules.memory import get_game_state, GameState
from modules.temp import temp_run_from_battle
from modules.pokemon import opponent_changed, get_opponent
from modules.stats import encounter_pokemon
from modules.trainer import trainer


def follow_path(coords: list, run: bool = True) -> bool:
    """
    Function to walk/run the trianer through a list of coords.
    TODO check if trainer gets stuck, re-attempt previous tuple of coords in the list

    :param coords: coords (tuple) (`posX`, `posY`)
    :param run: Trainer will hold B (run) if True, otherwise trainer will walk
    :return: True if trainer (`posX`, `posY`) = the final coord of the list, otherwise False (bool)
    """
    for x, y, *map_data in coords:
        if run:
            get_emulator().hold_button("B")

        while True and config["general"]["bot_mode"] != "manual":
            if get_game_state() == GameState.BATTLE:
                if opponent_changed():
                    encounter_pokemon(get_opponent())
                get_emulator().release_button("B")
                temp_run_from_battle()

            trainer_coords = trainer.get_coords()
            # Check if map changed to desired map
            if map_data:
                if trainer_coords[0] == map_data[0][0] and trainer_coords[1] == map_data[0][1]:
                    get_emulator().release_button("B")
                    break

            if trainer_coords[0] > x:
                direction = "Left"
            elif trainer_coords[0] < x:
                direction = "Right"
            elif trainer_coords[1] < y:
                direction = "Down"
            elif trainer_coords[1] > y:
                direction = "Up"
            else:
                get_emulator().release_button("B")
                break

            get_emulator().press_button(direction)
            get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
        get_emulator().run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)

    return True
