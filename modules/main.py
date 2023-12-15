import queue
import sys
from threading import Thread

from modules.battle import BattleHandler, check_lead_can_battle, RotatePokemon
from modules.console import console
from modules.context import context
from modules.memory import get_game_state, GameState
from modules.menuing import MenuWrapper, CheckForPickup, should_check_for_pickup
from modules.pokemon import opponent_changed, get_opponent


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

    encounter_counter = 0
    pickup_checked = False
    lead_rotated = False

    try:
        mode = None

        config = context.config

        if config.discord.rich_presence:
            from modules.discord import discord_rich_presence

            Thread(target=discord_rich_presence).start()

        if config.obs.http_server.enable:
            from modules.web.http import http_server

            Thread(target=http_server).start()

        while True:
            while not work_queue.empty():
                callback = work_queue.get_nowait()
                callback()

            if (
                not mode
                and get_game_state() == GameState.BATTLE
                and context.bot_mode not in ["Starters", "Static Soft Resets"]
            ):
                if opponent_changed():
                    pickup_checked = False
                    lead_rotated = False
                    encounter_pokemon(get_opponent())
                    encounter_counter += 1
                if context.bot_mode != "Manual":
                    mode = BattleHandler()

            if context.bot_mode == "Manual":
                if mode:
                    mode = None

            elif (
                not mode and config.battle.pickup and should_check_for_pickup(encounter_counter) and not pickup_checked
            ):
                mode = MenuWrapper(CheckForPickup(encounter_counter))
                pickup_checked = True
                encounter_counter = 0

            elif not mode and config.battle.replace_lead_battler and not check_lead_can_battle() and not lead_rotated:
                mode = MenuWrapper(RotatePokemon())
                lead_rotated = True

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

                    case "Static Soft Resets":
                        from modules.modes.soft_resets import ModeStaticSoftResets

                        mode = ModeStaticSoftResets()

                    case "Tower Duo":
                        from modules.modes.tower_duo import ModeTowerDuo

                        mode = ModeTowerDuo()

                    case "Ancient Legendaries":
                        from modules.modes.ancient_legendaries import ModeAncientLegendaries

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
