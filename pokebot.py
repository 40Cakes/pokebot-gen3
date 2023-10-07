import sys
from pathlib import Path
from threading import Thread

from modules.Config import config, LoadConfigFromDirectory
from modules.Console import console
from modules.Gui import PokebotGui, GetROM
from modules.Inputs import WaitFrames
from modules.Memory import GetGameState, GameState, GameHasStarted
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
    LoadConfigFromDirectory(profile.path / 'config', allow_missing_files=True)
    InitStats(profile)

    try:
        if config['discord']['rich_presence']:
            from modules.Discord import DiscordRichPresence
            Thread(target=DiscordRichPresence).start()

        if config['obs']['http_server']['enable']:
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
                if config['general']['bot_mode'] != 'manual':
                    temp_RunFromBattle()

            # If the game is still somewhere within the title screen (including the 'New Game' content
            # with Prof. Birch) there is nothing the bot can do, so in that case we force the bot into
            # manual mode until a game has been loaded.
            if not verified_that_game_has_started:
                WaitFrames(1)
                if GameHasStarted():
                    verified_that_game_has_started = True
                else:
                    continue

            match config['general']['bot_mode']:
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


if __name__ == '__main__':
    console.print(f'Starting [bold cyan]{pokebot_name} {pokebot_version}![/]')
    LoadConfigFromDirectory(Path(__file__).parent / 'config')

    # Allow auto-starting a profile by running the bot like `python pokebot.py profile-name`.
    preselected_profile = None
    if len(sys.argv) > 1 and ProfileDirectoryExists(sys.argv[1]):
        preselected_profile = LoadProfileByName(sys.argv[1])

    PokebotGui(MainLoop, preselected_profile)
