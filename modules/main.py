import sys
from threading import Thread

from modules.battle import BattleHandler
from modules.config import config, load_config_from_directory
from modules.console import console
from modules.context import context
from modules.memory import get_game_state, GameState
from modules.pokemon import opponent_changed, get_opponent
from modules.temp import temp_run_from_battle


def main_loop() -> None:
    """
    This function is run after the user has selected a profile and the emulator has been started.
    """
    from modules.encounter import encounter_pokemon  # prevents instantiating TotalStats class before profile selected

    try:
        mode = None
        load_config_from_directory(context.profile.path, allow_missing_files=True)

        if config["discord"]["rich_presence"]:
            from modules.discord import discord_rich_presence

            Thread(target=discord_rich_presence).start()

        if config["obs"]["http_server"]["enable"]:
            from modules.http import http_server

            Thread(target=http_server).start()

        while True:
            if not mode and get_game_state() == GameState.BATTLE and context.bot_mode != "Starters":
                if opponent_changed():
                    encounter_pokemon(get_opponent())
                    if context.bot_mode != "Manual" and config["battle"]["battle"]:
                        mode = BattleHandler()

            if context.bot_mode == "Manual":
                if mode:
                    mode = None

            elif not mode:
                match context.bot_mode:
                    case "Spin":
                        from modules.modes.general import ModeSpin

                        mode = ModeSpin()

                    case "Starters":
                        from modules.modes.starters import ModeStarters

                        mode = ModeStarters()

                    case "Fishing":
                        from modules.modes.general import ModeFishing

                        mode = ModeFishing()

                    case "Bunny Hop":
                        from modules.modes.general import ModeBunnyHop

                        mode = ModeBunnyHop()

                    case "Rayquaza":
                        from modules.modes.legendaries import ModeRayquaza

                        mode = ModeRayquaza()

            try:
                if mode:
                    next(mode.step())
            except StopIteration:
                mode = None
                continue
            except:
                mode = None
                context.bot_mode = "Manual"

            context.emulator.run_single_frame()

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        sys.exit(1)
