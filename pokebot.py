"""Main program entrypoint."""

import argparse
import atexit
import platform
from dataclasses import dataclass

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


@dataclass
class StartupSettings:
    profile: "Profile | None"
    debug: bool
    bot_mode: str
    no_video: bool
    no_audio: bool
    emulation_speed: int
    always_on_top: bool


def parse_arguments() -> StartupSettings:
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description=f"{pokebot_name} {pokebot_version}")
    parser.add_argument(
        "profile",
        nargs="?",
        help="Profile to initialize. Otherwise, the profile selection menu will appear.",
    )
    parser.add_argument("-m", "--bot-mode", choices=available_bot_modes, help="Initial bot mode (default: manual.)")
    parser.add_argument(
        "-s",
        "--emulation-speed",
        choices=["0", "1", "2", "3", "4"],
        help="Initial emulation speed (0 for unthrottled; default: 1.)",
    )
    parser.add_argument("-nv", "--no-video", action="store_true", help="Turn off video output by default.")
    parser.add_argument("-na", "--no-audio", action="store_true", help="Turn off audio output by default.")
    parser.add_argument(
        "-t", "--always-on-top", action="store_true", help="Keep the bot window always on top of other windows."
    )
    parser.add_argument("-d", "--debug", action="store_true", help="Enable extra debug options and a debug menu.")
    args = parser.parse_args()

    preselected_profile: Profile | None = None
    if args.profile and profile_directory_exists(args.profile):
        preselected_profile = load_profile_by_name(args.profile)

    return StartupSettings(
        profile=preselected_profile,
        debug=bool(args.debug),
        bot_mode=args.bot_mode or "manual",
        no_video=bool(args.no_video),
        no_audio=bool(args.no_audio),
        emulation_speed=int(args.emulation_speed or "1"),
        always_on_top=bool(args.always_on_top),
    )


if __name__ == "__main__":
    try:
        if not is_bundled_app():
            from requirements import check_requirements

            check_requirements()

        from modules.config import load_config_from_directory, available_bot_modes
        from modules.context import context
        from modules.console import console
        from modules.gui import PokebotGui
        from modules.main import main_loop
        from modules.profiles import Profile, profile_directory_exists, load_profile_by_name

        load_config_from_directory(get_base_path() / "profiles")

        # This catches the signal Windows emits when the underlying console window is closed
        # by the user. We still want to save the emulator state in that case, which would not
        # happen by default!
        if OS_NAME == "Windows":
            import win32api

            def win32_signal_handler(signal_type):
                if signal_type == 2:
                    if context.emulator is not None:
                        context.emulator.shutdown()

            win32api.SetConsoleCtrlHandler(win32_signal_handler, True)

        startup_settings = parse_arguments()
        console.print(f"Starting [bold cyan]{pokebot_name} {pokebot_version}![/]")
        gui = PokebotGui(main_loop, on_exit)
        context.gui = gui
        gui.run(startup_settings)
    except:
        console.print_exception(show_locals=True)
