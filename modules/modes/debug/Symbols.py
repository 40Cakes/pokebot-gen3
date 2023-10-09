# Loops indefinitely while outputting the raw value and decoded text of a specific symbol

from rich.live import Live
from rich.table import Table

from modules.Game import DecodeString
from modules.Gui import emulator
from modules.Memory import ReadSymbol

symbols = ["gObjectEvents", "sChat", "gStringVar1", "gStringVar2", "gStringVar3", "gStringVar4"]


def symbol_table(data: dict) -> Table:
    table = Table()
    table.add_column("Symbol", justify="left", no_wrap=False)
    table.add_column("Data", justify="left", no_wrap=False)
    table.add_column("DecodedString", justify="left", no_wrap=False)
    for key, value in data.items():
        table.add_row(str(key), str(value), DecodeString(value))
    return table


def ModeDebugSymbols():
    prev_data = {}
    with Live(symbol_table(prev_data), refresh_per_second=60) as live:
        while True:
            data = {}
            for symbol in symbols:
                data[symbol] = ReadSymbol(symbol)
            if data and data != prev_data:
                prev_data = data
                live.update(symbol_table(prev_data))
            emulator.RunSingleFrame()
