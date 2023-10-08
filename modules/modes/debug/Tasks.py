# Track the data of gTasks

from rich.table import Table
from rich.live import Live

from modules.Gui import emulator
from modules.Memory import ParseTasks


def generate_table(data: list) -> Table:
    table = Table()
    table.add_column("func", justify="left", no_wrap=True)
    table.add_column("isActive", justify="left", no_wrap=True)
    table.add_column("prev", justify="left", no_wrap=True)
    table.add_column("next", justify="left", no_wrap=True)
    table.add_column("priority", justify="left", width=10)
    table.add_column("data", justify="left")
    for x in range(16):
        table.add_row(
            data[x]["func"],
            str(data[x]["isActive"]),
            str(data[x]["prev"]),
            str(data[x]["next"]),
            str(data[x]["priority"]),
            str(data[x]["data"]),
        )
    return table


def ModeDebugTasks():
    last_data = ParseTasks()
    with Live(generate_table(last_data), refresh_per_second=60) as live:
        while True:
            data = ParseTasks()
            if data != last_data:
                last_data = data
                live.update(generate_table(last_data))
            emulator.RunSingleFrame()
