import platform
import sys
from threading import Thread
from modules.Console import console
from modules.Config import config_general, config_discord, config_obs
from modules.Gui import PokebotGui, GetROM
from modules.Inputs import WaitFrames
from modules.Memory import GetGameState, GameState, GameHasStarted
from modules.Temp import temp_RunFromBattle
from modules.Pokemon import OpponentChanged, GetOpponent
from modules.Profiles import ProfileDirectoryExists, LoadProfileByName
from modules.Stats import InitStats, EncounterPokemon
from version import pokebot_name, pokebot_version

def MainLoop():
    InitStats()

    try:
        if config_discord['rich_presence']:
            from modules.Discord import DiscordRichPresence
            Thread(target=DiscordRichPresence).start()

        if config_obs['http_server']['enable']:
            from modules.WebServer import WebServer
            Thread(target=WebServer).start()
    except:
        console.print_exception(show_locals=True)

    verified_that_game_has_started = GameHasStarted()

    while True:
        try:
            if GetGameState() == GameState.BATTLE:
                if OpponentChanged():
                    EncounterPokemon(GetOpponent())
                if config_general['bot_mode'] != 'manual':
                    temp_RunFromBattle()

            if not verified_that_game_has_started:
                WaitFrames(1)
                if GameHasStarted():
                    verified_that_game_has_started = True
                else:
                    continue

            match config_general['bot_mode']:
                case 'manual':
                    WaitFrames(1)

                case 'spin':
                    from modules.modes.General import ModeSpin
                    ModeSpin()

                case 'starters':
                    if GetROM().game_title in ['POKEMON LEAF', 'POKEMON FIRE']:
                        from modules.modes.frlg.Starters import Starters
                    else:
                        from modules.modes.rse.Starters import Starters
                    Starters()

                case 'fishing':
                    from modules.modes.General import ModeFishing
                    ModeFishing()

        except SystemExit:
            raise
        except:
            console.print_exception(show_locals=True)
            sys.exit(1)


if __name__ == "__main__":
    console.print(f'Starting [bold cyan]{pokebot_name} {pokebot_version}![/]')

    # On Windows, the bot can be started by clicking this Python file. In that case, the terminal
    # window is only open for as long as the bot runs, which would make it impossible to see error
    # messages during a crash.
    # For those cases, we register an `atexit` handler that will wait for user input before closing
    # the terminal window.
    if platform.system() == "Windows":
        import atexit
        import os
        import psutil


        def PromptBeforeExit() -> None:
            parent_process_name = psutil.Process(os.getppid()).name()
            if parent_process_name == "py.exe":
                input('Press Enter to continue...')


        atexit.register(PromptBeforeExit)

    # Allow auto-starting a profile by running the bot like `python pokebot.py profile-name`.
    profile = None
    if len(sys.argv) > 1 and ProfileDirectoryExists(sys.argv[1]):
        profile = LoadProfileByName(sys.argv[1])

    PokebotGui(MainLoop, profile)
