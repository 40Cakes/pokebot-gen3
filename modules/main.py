import queue
import sys
from threading import Thread

from modules.console import console
from modules.context import context
from modules.memory import get_game_state, GameState
from modules.pokemon import opponent_changed, get_opponent
from modules.temp import temp_run_from_battle


# Contains a queue of tasks that should be run the next time a frame completes.
# This is currently used by the HTTP server component (which runs in a separate thread) to trigger things
# such as extracting the current party, which need to be done from the main thread.
# Each entry here will be executed exactly once and then removed from the queue.
work_queue: queue.Queue[callable] = queue.Queue()


def main_loop() -> None:
    """
    This function is run after the user has selected a profile and the emulator has been started.
    """
    from modules.encounter import encounter_pokemon  # prevents instantiating TotalStats class before profile selected

    try:
        mode = None

        config = context.config

        if config.discord.rich_presence:
            from modules.discord import discord_rich_presence

            Thread(target=discord_rich_presence).start()

        if config.obs.http_server.enable:
            from modules.http import http_server

            Thread(target=http_server).start()

        while True:
            while not work_queue.empty():
                callback = work_queue.get_nowait()
                callback()

            if not mode and get_game_state() == GameState.BATTLE and context.bot_mode != "Starters":
                if opponent_changed():
                    encounter_pokemon(get_opponent())
                if context.bot_mode != "Manual":
                    temp_run_from_battle()

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

                    case "Ancient Legendaries":
                        from modules.modes.legendaries import ModeAncientLegendaries

                        mode = ModeAncientLegendaries()
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
