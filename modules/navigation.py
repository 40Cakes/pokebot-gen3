from modules.context import context
from modules.memory import get_game_state, GameState
from modules.pokemon import opponent_changed, get_opponent
from modules.stats import total_stats
from modules.temp import temp_run_from_battle
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
            context.emulator.hold_button("B")

        while True and context.bot_mode != "manual":
            if get_game_state() == GameState.BATTLE:
                if opponent_changed():
                    total_stats.encounter_pokemon(get_opponent())
                context.emulator.release_button("B")
                temp_run_from_battle()

            trainer_coords = trainer.get_coords()
            # Check if map changed to desired map
            if map_data:
                if trainer_coords[0] == map_data[0][0] and trainer_coords[1] == map_data[0][1]:
                    context.emulator.release_button("B")
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
                context.emulator.release_button("B")
                break

            context.emulator.press_button(direction)
            context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)

    return True
