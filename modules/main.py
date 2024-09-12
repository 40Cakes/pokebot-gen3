import queue
import sys
from collections import deque
from threading import Thread

from modules.console import console
from modules.context import context
from modules.memory import GameState, get_game_state
from modules.modes import BotListener, BotMode, BotModeError, FrameInfo, get_bot_listeners, get_bot_mode_by_name
from modules.plugins import plugin_profile_loaded
from modules.tasks import get_global_script_context, get_tasks

# Contains a queue of tasks that should be run the next time a frame completes.
# This is currently used by the HTTP server component (which runs in a separate thread) to trigger things
# such as extracting the current party, which need to be done from the main thread.
# Each entry here will be executed exactly once and then removed from the queue.
work_queue: queue.Queue[callable] = queue.Queue()


# Keeps a list of inputs that have been pressed for each frame so that the HTTP server
# can fetch and accumulate them for its `Inputs` stream event.
inputs_each_frame: deque[int] = deque(maxlen=128)


def main_loop() -> None:
    """
    This function is run after the user has selected a profile and the emulator has been started.
    """
    try:
        plugin_profile_loaded(context.profile)
        current_mode: BotMode | None = None

        if context.config.discord.rich_presence:
            from modules.discord import discord_rich_presence

            Thread(target=discord_rich_presence).start()

        if context.config.obs.http_server.enable:
            from modules.web.http import http_server

            Thread(target=http_server).start()

        listeners: list[BotListener] = get_bot_listeners(context.rom)
        previous_frame_info: FrameInfo | None = None

        while True:
            # Process work queue, which can be used to get the main thread to access the emulator
            # at a 'safe' time (i.e. not in the middle of emulating a frame.)
            while not work_queue.empty():
                callback = work_queue.get_nowait()
                callback()
                work_queue.task_done()

            context.frame += 1

            if context.bot_mode != "Manual":
                game_state = get_game_state()
                script_context = get_global_script_context()
                script_stack = script_context.stack if script_context is not None and script_context.is_active else []
                task_list = get_tasks()
                if task_list is not None:
                    active_tasks = [task.symbol.lower() for task in task_list]
                else:
                    active_tasks = []
            else:
                game_state = GameState.UNKNOWN
                script_stack = []
                active_tasks = []

            frame_info = FrameInfo(
                frame_count=context.emulator.get_frame_count(),
                game_state=game_state,
                active_tasks=active_tasks,
                script_stack=script_stack,
                previous_frame=previous_frame_info,
            )

            # Reset all bot listeners if the emulator has been reset.
            if previous_frame_info is not None and previous_frame_info.frame_count > frame_info.frame_count:
                listeners = get_bot_listeners(context.rom)

            if context.bot_mode == "Manual":
                context.controller_stack = []
                if current_mode is not None:
                    context.emulator.reset_held_buttons()
                current_mode = None
                listeners = []
            elif len(context.controller_stack) == 0:
                current_mode = get_bot_mode_by_name(context.bot_mode)()
                context.controller_stack.append(current_mode.run())
                listeners = get_bot_listeners(context.rom)

            try:
                if current_mode is not None:
                    for listener in listeners:
                        listener.handle_frame(current_mode, frame_info)
                    if len(context.controller_stack) > 0:
                        next(context.controller_stack[-1])
            except (StopIteration, GeneratorExit):
                context.controller_stack.pop()
            except BotModeError as e:
                context.emulator.reset_held_buttons()
                context.message = str(e)
                context.set_manual_mode()
            except TimeoutError:
                console.print_exception()
                sys.exit(1)
            except Exception as e:
                console.print_exception()
                context.emulator.reset_held_buttons()
                context.message = f"Internal Bot Error: {str(e)}"
                if context.debug:
                    context.debug_stepping_mode()
                    if hasattr(sys, "gettrace") and sys.gettrace() is not None:
                        breakpoint()
                else:
                    context.set_manual_mode()

            inputs_each_frame.append(context.emulator.get_inputs())
            context.emulator.run_single_frame()
            previous_frame_info = frame_info
            previous_frame_info.previous_frame = None

    except SystemExit:
        raise
    except Exception:
        console.print_exception(show_locals=True)
        sys.exit(1)
