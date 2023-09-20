import os
import atexit
from typing import NoReturn
from threading import Thread
from modules.Console import console
from modules.Config import config_general, config_discord, config_obs
from modules.Game import game
from modules.Inputs import WriteInputs, WaitFrames
from modules.Memory import GetGameState, GameState
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
            if config_general['bot_mode'] != 'manual':
                temp_RunFromBattle()

        match config_general['bot_mode']:
            case 'manual':
                WaitFrames(5)

            case 'spin':
                from modules.modes.General import ModeSpin
                ModeSpin()

            case 'starters':
                if game.name in ['Pokémon LeafGreen', 'Pokémon FireRed']:
                    from modules.modes.frlg.Starters import Starters
                else:
                    from modules.modes.rse.Starters import Starters
                Starters()

            case 'fishing':
                from modules.modes.General import ModeFishing
                ModeFishing()

    except:
        console.print_exception(show_locals=True)
        input('Press enter to exit...')
        os._exit(1)
