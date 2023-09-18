# Prints trainer data if it changes, on a loop (good for finding X,Y coords)
# Move this script to the root directory to ensure all imports work correctly
from rich.live import Live
from rich.table import Table

from modules.Trainer import GetTrainer


def generic_table(data: dict) -> Table:
    table = Table()
    row = ()
    for key, value in data.items():
        table.add_column(str(key), justify='left', no_wrap=True)
        row = (*row, str(value))
    table.add_row(*row)
    return table


prev_trainer = GetTrainer()
with Live(generic_table(prev_trainer), refresh_per_second=20) as live:
    while True:
        trainer = GetTrainer()
        if trainer and trainer != prev_trainer:
            prev_trainer = trainer
            live.update(generic_table(prev_trainer))
