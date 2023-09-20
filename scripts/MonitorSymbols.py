# Loops indefinitely while outputting the raw value and decoded text of a specific symbol
# Move this script to the root directory to ensure all imports work correctly
import time

from rich.live import Live
from rich.table import Table

from modules.Game import DecodeString
from modules.Memory import ReadSymbol

symbols = ['sChat', 'gStringVar1', 'gStringVar2', 'gStringVar3', 'gStringVar4']

def symbol_table(data: dict) -> Table:
    table = Table()
    table.add_column('Symbol', justify='left', no_wrap=True)
    table.add_column('Data', justify='left', no_wrap=True)
    for key, value in data.items():
        table.add_row(str(key), DecodeString(value))
    return table

prev_data = {}
with Live(symbol_table(prev_data), refresh_per_second=20) as live:
    while True:
        data = {}
        for symbol in symbols:
            data[symbol] = ReadSymbol(symbol)
        if data and data != prev_data:
            prev_data = data
            live.update(symbol_table(prev_data))
