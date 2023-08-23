import os
from modules.Console import console
from modules.Config import config
from modules.Memory import GetGame


console.print('Starting [cyan]PokéBot![/cyan]')

try:
    match config['bot_mode']:
        case 'spin':
            from modules.gen3.rse.General import ModeSpin
            ModeSpin()
        case 'starter':
            print(GetGame())
            if GetGame() == 'Pokémon Emerald':
                from modules.gen3.rse.General import Starter
                Starter(config['starter'])
            elif GetGame() == 'Pokémon LeafGreen' or GetGame() == 'Pokémon FireRed':
                from modules.gen3.rse.General import FRLGStarter
                FRLGStarter(config['starter'])
            else:
                print('INCOMPATTABLE ROM')
                input('Press enter to exit...')
                os._exit(0)



except Exception as e:
    print(str(e))
    input('Press enter to exit...')
    os._exit(1)
