# Prints trainer data dict as it changes

from rich.live import Live
from rich.table import Table

from modules.Gui import emulator
from modules.Trainer import GetTrainer


def generic_table(data: dict) -> Table:
    table = Table()
    row = ()
    for key, value in data.items():
        table.add_column(str(key), justify="left", no_wrap=True)
        row = (*row, str(value))
    table.add_row(*row)
    return table


prev_trainer = GetTrainer()


def ModeDebugTrainer():
    global prev_trainer
    with Live(generic_table(prev_trainer), refresh_per_second=60) as live:
        while True:
            trainer = GetTrainer()
            if trainer and trainer != prev_trainer:
                prev_trainer = trainer
                live.update(generic_table(prev_trainer))
            emulator.RunSingleFrame()
