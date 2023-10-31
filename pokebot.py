"""Main program entrypoint."""

import argparse
import atexit
import platform

from modules.runtime import is_bundled_app, get_base_path
from modules.version import pokebot_name, pokebot_version

OS_NAME = platform.system()
gui = None


# On Windows, the bot can be started by clicking this Python file. In that case, the terminal
# window is only open for as long as the bot runs, which would make it impossible to see error
# messages during a crash.
# For those cases, we register an `atexit` handler that will wait for user input before closing
# the terminal window.
def on_exit() -> None:
    if OS_NAME == "Windows":
        import psutil
        import os
        parent_process_name = psutil.Process(os.getppid()).name()
        if parent_process_name == "py.exe" or is_bundled_app():
            if gui is not None and gui.window is not None:
                gui.window.withdraw()

            print("")
            input("Press Enter to close...")


atexit.register(on_exit)


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description=f'{pokebot_name} {pokebot_version}')
    parser.add_argument(
        'profile',
        nargs='?',
        help='Profile to initialize. Otherwise, the profile selection menu will appear.',
    )
    parser.add_argument('-d', '--debug', action='store_true', help='Enable extra debug options and a debug menu.')
    return parser.parse_args()


if __name__ == "__main__":
    if not is_bundled_app():
        from requirements import check_requirements
        check_requirements()

    from modules.config import load_config_from_directory
    from modules.console import console
    from modules.gui import PokebotGui, get_emulator
    from modules.main import main_loop
    from modules.profiles import profile_directory_exists, load_profile_by_name

    load_config_from_directory(get_base_path() / "profiles")

    # This catches the signal Windows emits when the underlying console window is closed
    # by the user. We still want to save the emulator state in that case, which would not
    # happen by default!
    if OS_NAME == "Windows":
        import win32api


        def win32_signal_handler(signal_type):
            if signal_type == 2:
                emulator = get_emulator()
                if emulator is not None:
                    emulator.shutdown()


        win32api.SetConsoleCtrlHandler(win32_signal_handler, True)

    parsed_args = parse_arguments()
    preselected_profile = parsed_args.profile
    debug_mode = parsed_args.debug
    if preselected_profile and profile_directory_exists(preselected_profile):
        preselected_profile = load_profile_by_name(preselected_profile)

    console.print(f"Starting [bold cyan]{pokebot_name} {pokebot_version}![/]")
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
