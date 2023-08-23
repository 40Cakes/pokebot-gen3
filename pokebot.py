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
            if mGBA.game == 'Pokémon Emerald':
                if config['starter'] == 'mudkip':
                    from modules.gen3.rse.General import Starter
                    Starter(config['starter'])
                elif config['starter'] == 'treecko':
                    from modules.gen3.rse.General import Starter
                    Starter(config['starter'])
                elif config['starter'] == 'torchic':
                    from modules.gen3.rse.General import Starter
                    Starter(config['starter'])
                else:
                    console.print('Incompatible starter')
                    input('Press enter to exit...')
                    os._exit(1)
                from modules.gen3.rse.General import Starter
                Starter(config['starter'])
            elif mGBA.game == 'Pokémon LeafGreen' or mGBA.game == 'Pokémon FireRed':
                if config['starter'] == 'bulbasaur':
                    from modules.gen3.rse.General import FRLGStarter
                    FRLGStarter(config['starter'])
                elif config['starter'] == 'charmander':
                    from modules.gen3.rse.General import FRLGStarter
                    FRLGStarter(config['starter'])
                elif config['starter'] == 'squirtle':
                    from modules.gen3.rse.General import FRLGStarter
                    FRLGStarter(config['starter'])
                else:
                    console.print('Incompatible starter')
                    input('Press enter to exit...')
                    os._exit(1)
                from modules.gen3.rse.General import FRLGStarter
                FRLGStarter(config['starter'])
            else:
                console.print('INCOMPATIBLE ROM')
                input('Press enter to exit...')
                os._exit(0)



except Exception as e:
    print(str(e))
    input('Press enter to exit...')
    os._exit(1)
