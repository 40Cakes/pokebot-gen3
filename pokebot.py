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
                if config['starter'] != ('mudkip' or 'treecko' or 'torchic'):
                    print('Incompatable starter')
                    input('Press enter to exit...')
                    os._exit(1)
                from modules.gen3.rse.General import Starter
                Starter(config['starter'])
            elif GetGame() == 'Pokémon LeafGreen' or GetGame() == 'Pokémon FireRed':
                if config['starter'] != ('bulbasaur' or 'charmander' or 'squirtle'):

                    print('Incompatable starter')
                    input('Press enter to exit...')
                    os._exit(1)
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
