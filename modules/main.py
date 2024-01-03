import queue
import sys
from threading import Thread
from typing import Generator

from modules.battle import BattleHandler, check_lead_can_battle, RotatePokemon
from modules.console import console
from modules.context import context
from modules.memory import get_game_state, GameState
from modules.menuing import MenuWrapper, CheckForPickup, should_check_for_pickup
from modules.modes import get_bot_mode_by_name, BotMode, BotModeError
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

    pickup_checked = False
    lead_rotated = False

    try:
        current_mode: BotMode | None = None
        battle_controller: Generator | None = None
        in_battle: bool = False

        if context.config.discord.rich_presence:
            from modules.discord import discord_rich_presence

            Thread(target=discord_rich_presence).start()

        if context.config.obs.http_server.enable:
            from modules.web.http import http_server

            Thread(target=http_server).start()

        while True:
            # Process work queue, which can be used to get the main thread to access the emulator
            # at a 'safe' time (i.e. not in the middle of emulating a frame.)
            while not work_queue.empty():
                callback = work_queue.get_nowait()
                callback()

            # Handle active battle, unless the mode wants to handle it itself.
            if get_game_state() == GameState.BATTLE:
                in_battle = True
                # Log encounter if a new battle starts or a new opponent Pokemon is switched in.
                if opponent_changed():
                    pickup_checked = False
                    lead_rotated = False
                    encounter_pokemon(get_opponent())

                if battle_controller is None and context.bot_mode != "Manual":
                    battle_controller = BattleHandler().step()
            elif in_battle:
                # 'Clean-up tasks' at the end of a battle.
                in_battle = False
                if context.config.battle.pickup and should_check_for_pickup() and not pickup_checked:
                    pickup_checked = True
                    battle_controller = MenuWrapper(CheckForPickup()).step()
                elif context.config.battle.replace_lead_battler and not check_lead_can_battle() and not lead_rotated:
                    lead_rotated = True
                    battle_controller = MenuWrapper(RotatePokemon()).step()
                else:
                    battle_controller = None

            if current_mode is not None and current_mode.disable_default_battle_handler():
                battle_controller = None
                in_battle = False

            if context.bot_mode == "Manual":
                current_mode = None
                battle_controller = None
            elif current_mode is None and battle_controller is None:
                current_mode = get_bot_mode_by_name(context.bot_mode)()

            try:
                if battle_controller is not None:
                    next(battle_controller)
                elif current_mode is not None:
                    next(current_mode)
            except (StopIteration, GeneratorExit):
                if battle_controller is not None:
                    battle_controller = None
                else:
                    current_mode = None
            except BotModeError as e:
                current_mode = None
                battle_controller = None
                context.message = str(e)
                context.set_manual_mode()
            except Exception as e:
                console.print_exception()
                current_mode = None
                battle_controller = None
                context.message = "Internal Bot Error: " + str(e)
                context.set_manual_mode()

            context.emulator.run_single_frame()

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        sys.exit(1)
