import atexit
import platform
import sys
from pathlib import Path
from threading import Thread

gui = None


# On Windows, the bot can be started by clicking this Python file. In that case, the terminal
# window is only open for as long as the bot runs, which would make it impossible to see error
# messages during a crash.
# For those cases, we register an `atexit` handler that will wait for user input before closing
# the terminal window.
def on_exit() -> None:
    if platform.system() == 'Windows':
        import psutil
        import os
        parent_process_name = psutil.Process(os.getppid()).name()
        if parent_process_name == 'py.exe':
            if gui is not None and gui.window is not None:
                gui.window.withdraw()

            print('')
            input('Press Enter to close...')


atexit.register(on_exit)

from modules.config import config, load_config_from_directory, force_manual_mode
from modules.console import console
from modules.gui import PokebotGui, get_emulator
from modules.memory import get_game_state, GameState
from modules.pokemon import opponent_changed, get_opponent
from modules.profiles import Profile, profile_directory_exists, load_profile_by_name
from modules.stats import init_stats, encounter_pokemon
from modules.temp import temp_run_from_battle
from version import pokebot_name, pokebot_version


def main_loop(profile: Profile) -> None:
    """
    This function is run after the user has selected a profile and the emulator has been started.
    :param profile: The profile selected by the user
    """
    mode = None
    load_config_from_directory(profile.path, allow_missing_files=True)
    init_stats(profile)

    try:
        if config["discord"]["rich_presence"]:
            from modules.discord import discord_rich_presence

            Thread(target=discord_rich_presence).start()

        if config["obs"]["http_server"]["enable"]:
            from modules.http import http_server

            Thread(target=http_server).start()
    except:
        console.print_exception(show_locals=True)

    while True:
        try:
            if not mode and get_game_state() == GameState.BATTLE and config["general"]["bot_mode"] != "starters":
                if opponent_changed():
                    encounter_pokemon(get_opponent())
                if config["general"]["bot_mode"] != "manual":
                    temp_run_from_battle()

            if config["general"]["bot_mode"] == "manual":
                if mode:
                    mode = None

            elif not mode:
                match config["general"]["bot_mode"]:
                    case "spin":
                        from modules.modes.general import ModeSpin

                        mode = ModeSpin()

                    case "starters":
                        from modules.modes.starters import ModeStarters

                        mode = ModeStarters()

                    case "fishing":
                        from modules.modes.general import ModeFishing

                        mode = ModeFishing()

                    case "bunny_hop":
                        from modules.modes.general import ModeBunnyHop

                        mode = ModeBunnyHop()

            try:
                if mode:
                    next(mode.step())
            except StopIteration:
                mode = None
                continue
            except:
                console.print_exception(show_locals=True)
                mode = None
                force_manual_mode()

            get_emulator().run_single_frame()

        except SystemExit:
            raise
        except:
            console.print_exception(show_locals=True)
            sys.exit(1)


if __name__ == "__main__":
    console.print(f"Starting [bold cyan]{pokebot_name} {pokebot_version}![/]")
    load_config_from_directory(Path(__file__).parent / "profiles")

    # This catches the signal Windows emits when the underlying console window is closed
    # by the user. We still want to save the emulator state in that case, which would not
    # happen by default!
    if platform.system() == "Windows":
        import win32api


        def win32_signal_handler(signal_type):
            if signal_type == 2:
                emulator = get_emulator()
                if emulator is not None:
                    emulator.shutdown()


        win32api.SetConsoleCtrlHandler(win32_signal_handler, True)

    preselected_profile = None
    debug_mode = False
    for arg in sys.argv[1:]:
        if arg == "--debug":
            debug_mode = True
        elif profile_directory_exists(arg):
            preselected_profile = load_profile_by_name(arg)

    gui = PokebotGui(main_loop, on_exit)
    if debug_mode:
        from modules.gui import DebugEmulatorControls
        from modules.debug import TasksTab, BattleTab, TrainerTab, DaycareTab, SymbolsTab, InputsTab, EventFlagsTab

        controls = DebugEmulatorControls(gui, gui.window)
        controls.add_tab(TasksTab())
        controls.add_tab(BattleTab())
        controls.add_tab(TrainerTab())
        controls.add_tab(DaycareTab())
        controls.add_tab(SymbolsTab())
        controls.add_tab(EventFlagsTab())
        controls.add_tab(InputsTab())

        gui.controls = controls

    gui.run(preselected_profile)
