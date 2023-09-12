# Track the data of gTasks
# Move this script to the root directory to ensure all imports work correctly

import struct
from rich.table import Table
from rich.live import Live
from modules.Memory import ReadSymbol, GetSymbolName

NUM_TASKS = 16
NUM_TASK_DATA = 16

def ParseTasks():
    gTasks = ReadSymbol('gTasks')
    Tasks = {}
    for x in range(NUM_TASKS):
        name = GetSymbolName(int(struct.unpack('<I', gTasks[(x*40):(x*40+4)])[0]) - 1)
        if name =='':
            name = str(gTasks[(x*40):(x*40+4)])
        Tasks[x] = {
            'func': name,
            'isActive': bool(gTasks[(x*40+4)]),
            'prev': gTasks[(x*40+5)],
            'next': gTasks[(x*40+6)],
            'priority': gTasks[(x*40+7)],
            'data':gTasks[(x*40+8):(x*40+40)]
        }
    return Tasks


def generate_table() -> Table:
    table = Table()
    table.add_column("func", justify="left", no_wrap=True)
    table.add_column("isActive", justify="left", no_wrap=True)
    table.add_column("prev", justify="left", no_wrap=True)
    table.add_column("next", justify="left", no_wrap=True)
    table.add_column("priority", justify="left", width=10)
    for x in range(NUM_TASKS):
        table.add_row(last_data[x]['func'],str(last_data[x]['isActive']),str(last_data[x]['prev']),str(last_data[x]['next']),str(last_data[x]['priority']),)
    return table

last_data = ParseTasks()
with Live(generate_table(), refresh_per_second=4) as live:
    while True:
        data = ParseTasks()
        if data != last_data:
            last_data = data
            live.update(generate_table())
