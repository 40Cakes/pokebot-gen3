import os
from modules.Console import console
from modules.Config import config


console.print('Starting [cyan]PokéBot![/cyan]')

try:
    match config['bot_mode']:
        case 'spin':
            from modules.gen3.rse.General import ModeSpin
            ModeSpin()
        case 'Starter':
            from modules.gen3.rse.General import RSEstarters
            RSEstarters(config['starter'])

except Exception as e:
    print(str(e))
    input('Press enter to exit...')
    os._exit(1)
