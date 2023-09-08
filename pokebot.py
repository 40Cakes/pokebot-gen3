import os
import struct
import atexit
from typing import NoReturn
from threading import Thread
from modules.Console import console
from modules.Config import config_general, config_discord, config_obs
from modules.Inputs import PressButton, WaitFrames, WriteInputs
from modules.Memory import GetGameState, mGBA, GetTrainer, EncodeString, ReadSymbol, GetOpponent, OpponentChanged, TrainerState
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

    if config_obs['server']['enable']:
        from modules.WebServer import WebServer
        Thread(target=WebServer).start()
except:
    console.print_exception(show_locals=True)

# Main Loop
while True:
    try:
        if config_general['bot_mode'] != 'manual':
            if GetGameState() == TrainerState.BATTLE:
                # Search for the text "What will (Pokémon) do?" in `gDisplayedStringBattle`
                b_What = EncodeString('What')  # TODO English only

                while ReadSymbol('gDisplayedStringBattle', size=4) != b_What:
                    PressButton(['B'])
                while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 1:
                    PressButton(['Right'])
                while struct.unpack('<I', ReadSymbol('gActionSelectionCursor'))[0] != 3:
                    PressButton(['Down'])
                while ReadSymbol('gDisplayedStringBattle', size=4) == b_What:
                    PressButton(['A'])
                while GetTrainer()['state'] != TrainerState.OVERWORLD:
                    PressButton(['B'])

        if OpponentChanged():
            while GetGameState() != TrainerState.BATTLE:
                WaitFrames(1)
                continue
            EncounterPokemon(GetOpponent())

        match config_general['bot_mode']:
            case 'manual':
                WaitFrames(5)

            case 'spin':
                from modules.gen3.General import ModeSpin
                ModeSpin()

            case 'starters':
                if mGBA.game in ['Pokémon Emerald']:
                    from modules.gen3.rse.Starters import Starters
                    Starters(config_general['starter'])
                elif mGBA.game in ['Pokémon LeafGreen', 'Pokémon FireRed']:
                    from modules.gen3.frlg.Starters import Starters
                else:
                    console.print('Ruby/Sapphire starters are currently not supported, coming soon...')
                    input('Press enter to exit...')
                    os._exit(1)
                Starters(config_general['starter'])

    except:
        console.print_exception(show_locals=True)
        input('Press enter to exit...')
        os._exit(1)
