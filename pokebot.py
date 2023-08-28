import os
from modules.Console import console
from modules.Config import config
from modules.Memory import mGBA


console.print('Starting [cyan]PokéBot![/cyan]')

try:
    match config['bot_mode']:
        case 'spin':
            from modules.gen3.rse.General import ModeSpin
            ModeSpin()

        case 'starters':
            if mGBA.game is 'Pokémon Emerald':
                from modules.gen3.rse.General import Starters
                Starters(config['starter'])
            elif mGBA.game in ['Pokémon LeafGreen', 'Pokémon FireRed']:
                from modules.gen3.rse.General import Starters
            else:
                console.print('Ruby/Sapphire starters are currently not supported, coming soon...')
                input('Press enter to exit...')
                os._exit(1)
            Starters(config['starter'])


except Exception as e:
    print(str(e))
    input('Press enter to exit...')
    os._exit(1)
