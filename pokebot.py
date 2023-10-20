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

from modules.Config import config, LoadConfigFromDirectory, ForceManualMode
from modules.Console import console
from modules.Gui import PokebotGui, GetEmulator
from modules.Memory import GetGameState, GameState
from modules.Pokemon import OpponentChanged, GetOpponent
from modules.Profiles import Profile, ProfileDirectoryExists, LoadProfileByName
from modules.Stats import InitStats, EncounterPokemon
from modules.Temp import temp_RunFromBattle
from version import pokebot_name, pokebot_version


def MainLoop(profile: Profile) -> None:
    """
    This function is run after the user has selected a profile and the emulator has been started.
    :param profile: The profile selected by the user
    """
    mode = None
    LoadConfigFromDirectory(profile.path / "config", allow_missing_files=True)
    InitStats(profile)

    try:
        if config["discord"]["rich_presence"]:
            from modules.Discord import DiscordRichPresence

            Thread(target=DiscordRichPresence).start()

        if config["obs"]["http_server"]["enable"]:
            from modules.WebServer import WebServer

            Thread(target=WebServer).start()
    except:
        console.print_exception(show_locals=True)

    while True:
        try:
            if not mode and GetGameState() == GameState.BATTLE and config["general"]["bot_mode"] != "starters":
                if OpponentChanged():
                    EncounterPokemon(GetOpponent())
                if config["general"]["bot_mode"] != "manual":
                    temp_RunFromBattle()

            if config["general"]["bot_mode"] == "manual":
                if mode:
                    mode = None

            elif not mode:
                match config["general"]["bot_mode"]:
                    case "spin":
                        from modules.modes.General import ModeSpin

                        mode = ModeSpin()

                    case "starters":
                        from modules.modes.Starters import ModeStarters

                        mode = ModeStarters()

                    case "fishing":
                        from modules.modes.General import ModeFishing

                        mode = ModeFishing()

            try:
                if mode:
                    next(mode.step())
            except StopIteration:
                mode = None
                continue
            except:
                console.print_exception(show_locals=True)
                mode = None
                ForceManualMode()

            GetEmulator().RunSingleFrame()

        except SystemExit:
            raise
        except:
            console.print_exception(show_locals=True)
            sys.exit(1)


if __name__ == "__main__":
    console.print(f"Starting [bold cyan]{pokebot_name} {pokebot_version}![/]")
    LoadConfigFromDirectory(Path(__file__).parent / "config")

    # This catches the signal Windows emits when the underlying console window is closed
    # by the user. We still want to save the emulator state in that case, which would not
    # happen by default!
    if platform.system() == "Windows":
        import win32api


        def Win32SignalHandler(signal_type):
            if signal_type == 2:
                emulator = GetEmulator()
                if emulator is not None:
                    emulator.Shutdown()


        win32api.SetConsoleCtrlHandler(Win32SignalHandler, True)

    # Allows auto-starting a profile by passing its name as an argument.
    # It also supports the `--debug` flag to enable the debug GUI controls.
    #
    # Examples:
    #     `python pokebot.py my-profile`          starts the 'my-profile' profile
    #     `python pokebot.py my-profile --debug`  starts the 'my-profile' profile in debug mode
    #     `python pokebot.py --debug`             starts the profile selection screen in debug mode
    preselected_profile = None
    debug_mode = False
    for arg in sys.argv[1:]:
        if arg == "--debug":
            debug_mode = True
        elif ProfileDirectoryExists(arg):
            preselected_profile = LoadProfileByName(arg)

    gui = PokebotGui(MainLoop, on_exit)
    if debug_mode:
        from modules.Gui import DebugEmulatorControls
        from modules.GuiDebug import TasksTab, BattleTab, TrainerTab, DaycareTab, SymbolsTab, InputsTab

        controls = DebugEmulatorControls(gui, gui.window)
        controls.AddTab(TasksTab())
        controls.AddTab(BattleTab())
        controls.AddTab(TrainerTab())
        controls.AddTab(DaycareTab())
        controls.AddTab(SymbolsTab())
        controls.AddTab(InputsTab())

        gui.controls = controls

    gui.Run(preselected_profile)
