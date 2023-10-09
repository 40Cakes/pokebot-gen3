import struct
import tkinter
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.Game import DecodeString
from modules.Gui import DebugTab
from modules.Memory import ReadSymbol, ParseTasks, GetSymbolName
from modules.Pokemon import names_list

if TYPE_CHECKING:
    from modules.LibmgbaEmulator import LibmgbaEmulator


class TasksTab(DebugTab):
    _cb1_label: ttk.Label
    _cb2_label: ttk.Label
    _tv: ttk.Treeview
    _items: list = []

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text='Callback 1:').grid(row=0, column=0)
        self._cb1_label = ttk.Label(frame, text='', padding=(10, 0))
        self._cb1_label.grid(row=0, column=1, sticky='W')

        ttk.Label(frame, text='Callback 2:', padding=(0, 10)).grid(row=1, column=0)
        self._cb2_label = ttk.Label(frame, text='', padding=(10, 10))
        self._cb2_label.grid(row=1, column=1, sticky='W')

        treeview_scrollbar_combo = ttk.Frame(frame, padding=(0, 10))
        treeview_scrollbar_combo.columnconfigure(0, weight=1)
        treeview_scrollbar_combo.grid(row=2, columnspan=2)

        self._tv = ttk.Treeview(treeview_scrollbar_combo, columns=('func', 'priority', 'data'),
                                show='headings', selectmode='browse', height=16)

        self._tv.column('func', width=300)
        self._tv.column('priority', width=40)

        self._tv.heading('func', text='Function')
        self._tv.heading('priority', text='Prio')
        self._tv.heading('data', text='Data')

        scrollbar = ttk.Scrollbar(treeview_scrollbar_combo, orient=tkinter.VERTICAL, command=self._tv.yview)
        scrollbar.grid(row=0, column=1, sticky='NWS')
        self._tv.configure(yscrollcommand=scrollbar.set)

        for i in range(0, 16):
            self._items.append(self._tv.insert('', tkinter.END, text=str(i), values=('', '', '')))

        self._tv.grid(row=0, column=0, sticky='E')

        root.add(frame, text='Tasks')

    def Update(self, emulator: 'LibmgbaEmulator'):
        callback1 = ReadSymbol("gMain", 0, 4)
        callback2 = ReadSymbol("gMain", 4, 4)

        cb1_addr = int(struct.unpack("<I", callback1)[0]) - 1
        cb2_addr = int(struct.unpack("<I", callback2)[0]) - 1

        self._cb1_label.config(text=GetSymbolName(cb1_addr, pretty_name=True))
        self._cb2_label.config(text=GetSymbolName(cb2_addr, pretty_name=True))

        index = 0
        for task in ParseTasks(pretty_names=True):
            if task['func'].upper() == 'TASKDUMMY' or not task['isActive'] or task['func'] == b'\x00\x00\x00\x00':
                self._tv.item(self._items[index], values=('', '', '', ''))
                continue

            data = []
            for byte in task['data']:
                data.append(struct.pack('B', byte).hex())
            while len(data) > 0 and data[-1] == '00':
                data.pop()

            self._tv.item(self._items[index],
                          values=(task['func'], task['priority'], data))
            index += 1


class BattleTab(DebugTab):
    _tv: ttk.Treeview
    _items: dict = {}

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)

        treeview_scrollbar_combo = ttk.Frame(frame)
        treeview_scrollbar_combo.columnconfigure(0, weight=1)
        treeview_scrollbar_combo.grid()

        self._tv = ttk.Treeview(treeview_scrollbar_combo, columns=('name', 'value'), show='headings',
                                selectmode='browse', height=20)

        self._tv.column('name', width=210)
        self._tv.heading('name', text='Name')

        self._tv.column('value', width=210)
        self._tv.heading('value', text='Value')

        scrollbar = ttk.Scrollbar(treeview_scrollbar_combo, orient=tkinter.VERTICAL, command=self._tv.yview)
        scrollbar.grid(row=0, column=1, sticky='NWS')
        self._tv.configure(yscrollcommand=scrollbar.set)

        data = self._GetData()
        for key in data:
            item = self._tv.insert('', tkinter.END, text=key, values=(key, data[key]))
            self._items[key] = item

        self._tv.grid(row=0, column=0, sticky='E')

        root.add(frame, text='Battle')

    def Update(self, emulator: 'LibmgbaEmulator'):
        data = self._GetData()
        for key in data:
            self._tv.item(self._items[key], values=(key, data[key]))

    def _GetData(self):
        data = ReadSymbol('gBattleResults')

        def SpeciesName(value: int) -> str:
            if value > len(names_list):
                return ""
            return names_list[value - 1]

        return {
            "Player Faint Counter": int(data[0]),
            "Opponent Faint Counter": int(data[1]),
            "Player Switch Counter": int(data[2]),
            "Count Healing Items used": int(data[3]),
            "Player Mon Damaged": bool(data[5] & 0x1),  #:1; // 0x5
            "Master Ball used": bool(data[5] & 0x2),  #:1;      // 0x5
            "Caught Mon Ball used": int(data[5] & 0x30),  #:4;       // 0x5
            "Wild Mon was Shiny": bool(data[5] & 0x40),  #:1;       // 0x5
            "Count Revives used": int(data[4]),
            "Player Mon 1 Species": struct.unpack("<H", data[6:8])[0],
            "Player Mon 1 Name": DecodeString(data[8:19]),  # SpeciesName(battleResult.playerMon1Species)
            "Battle turn Counter": int(data[19]),
            "Player Mon 2 Species": struct.unpack("<H", data[38:40])[0],
            "Player Mon 2 Name": DecodeString(data[20:31]),
            "PokeBall Throws": int(data[31]),
            "Last Opponent Species": struct.unpack("<H", data[32:34])[0],
            "Last Opponent Name": SpeciesName(struct.unpack("<H", data[32:34])[0]),
            "Last used Move Player": struct.unpack("<H", data[34:36])[0],
            "Last used Move Opponent": struct.unpack("<H", data[36:38])[0],
            "Cought Mon Species": struct.unpack("<H", data[40:42])[0],
            "Cought Mon Name": DecodeString(data[42:53]),
            "Catch Attempts": int(data[54]),
        }


class StringsTab(DebugTab):
    _tv: ttk.Treeview
    _items: dict = {}

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)

        treeview_scrollbar_combo = ttk.Frame(frame)
        treeview_scrollbar_combo.columnconfigure(0, weight=1)
        treeview_scrollbar_combo.grid()

        self._tv = ttk.Treeview(treeview_scrollbar_combo, columns=('name', 'decoded_value'), show='headings',
                                selectmode='browse', height=20)

        self._tv.column('name', width=120)
        self._tv.heading('name', text='Symbol')

        self._tv.column('decoded_value', width=300)
        self._tv.heading('decoded_value', text='String Data')

        scrollbar = ttk.Scrollbar(treeview_scrollbar_combo, orient=tkinter.VERTICAL, command=self._tv.yview)
        scrollbar.grid(row=0, column=1, sticky='NWS')
        self._tv.configure(yscrollcommand=scrollbar.set)

        data = self._GetData()
        for key in data:
            item = self._tv.insert('', tkinter.END, text=key, values=data[key])
            self._items[key] = item

        self._tv.grid(row=0, column=0, sticky='E')

        root.add(frame, text='Strings')

    def Update(self, emulator: 'LibmgbaEmulator'):
        data = self._GetData()
        for key in data:
            self._tv.item(self._items[key], values=data[key])

    def _GetData(self):
        SYMBOLS_TO_DISPLAY = ['gObjectEvents', 'sChat', 'gStringVar1', 'gStringVar2', 'gStringVar3', 'gStringVar4']
        result = {}

        for symbol in SYMBOLS_TO_DISPLAY:
            value = ReadSymbol(symbol.upper())
            result[symbol] = (symbol, DecodeString(value))

        return result
