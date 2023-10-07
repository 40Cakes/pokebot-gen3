import os
import atexit
from typing import NoReturn
import sys
from pathlib import Path
from threading import Thread
from modules.Console import console
from modules.Config import config_general, config_discord, config_obs, config_battle
from modules.Inputs import WriteInputs, WaitFrames
from modules.Memory import GetGameState, GameState, mGBA
from modules.Temp import temp_RunFromBattle
from modules.Pokemon import OpponentChanged, GetOpponent
from modules.Stats import EncounterPokemon

version = 'v0.0.1a'
console.print('Starting [bold cyan]PokéBot {}![/]'.format(version))


def _exit() -> NoReturn:
    """
    Called when the bot is manually stopped or crashes.
    Clears the inputs register in the emulator so no buttons will be stuck down.
    """
    WriteInputs(0)


atexit.register(_exit)

try:
    if config_discord['rich_presence']:
        from modules.Discord import DiscordRichPresence
        Thread(target=DiscordRichPresence).start()

    if config_obs['http_server']['enable']:
        from modules.WebServer import WebServer
        Thread(target=WebServer).start()
except:
    console.print_exception(show_locals=True)

# Main Loop
while True:
    try:
        if GetGameState() == GameState.BATTLE:
            if OpponentChanged():
                EncounterPokemon(GetOpponent())

        match config_general['bot_mode']:
            case 'manual':
                WaitFrames(5)

            case 'spin':
                from modules.modes.General import ModeSpin
                ModeSpin()

            case 'starters':
                if mGBA.game in ['Pokémon LeafGreen', 'Pokémon FireRed']:
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
