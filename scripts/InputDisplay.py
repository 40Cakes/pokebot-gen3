# Displays inputs on a loop, good for debugging if buttons are stuck down
# Move this script to the root directory to ensure all imports work correctly
from modules.Console import console
from modules.Inputs import input_map, GetInputs

console.print('[bold green]Inputs:')
with console.status('', refresh_per_second=100) as status:
    while True:
        str = '[bold green]'
        inputs = GetInputs()
        for input in input_map:
            if input_map[input] & inputs:
                str += input + ' '
            status.update(status=str)
