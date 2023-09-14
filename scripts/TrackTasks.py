# Track the data of gTasks
# Move this script to the root directory to ensure all imports work correctly

from rich.table import Table
from rich.live import Live
from modules.Memory import ParseTasks


def generate_table() -> Table:
    table = Table()
    table.add_column("func", justify="left", no_wrap=True)
    table.add_column("isActive", justify="left", no_wrap=True)
    table.add_column("prev", justify="left", no_wrap=True)
    table.add_column("next", justify="left", no_wrap=True)
    table.add_column("priority", justify="left", width=10)
    table.add_column("data", justify="left")
    for x in range(16):
        table.add_row(
            last_data[x]['func'],
            str(last_data[x]['isActive']),
            str(last_data[x]['prev']),
            str(last_data[x]['next']),
            str(last_data[x]['priority']),
            str(last_data[x]['data'][0]))
    return table

last_data = ParseTasks()
with Live(generate_table(), refresh_per_second=4) as live:
    while True:
        data = ParseTasks()
        if data != last_data:
            last_data = data
            live.update(generate_table())
