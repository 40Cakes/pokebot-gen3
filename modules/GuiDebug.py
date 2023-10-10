import struct
import tkinter
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.Daycare import GetDaycareData, PokemonGender
from modules.Game import DecodeString, _reverse_symbols
from modules.Gui import DebugTab, GetROM
from modules.Memory import GetSymbol, ReadSymbol, ParseTasks, GetSymbolName
from modules.Pokemon import names_list, GetParty
from modules.Trainer import GetTrainer

if TYPE_CHECKING:
    from modules.LibmgbaEmulator import LibmgbaEmulator


class FancyTreeview:
    def __init__(self, root: ttk.Widget, height=20, row=0, column=0, columnspan=1,
                 additional_context_actions: dict[str, callable] = {}):
        treeview_scrollbar_combo = ttk.Frame(root)
        treeview_scrollbar_combo.columnconfigure(0, weight=1)
        treeview_scrollbar_combo.grid(row=row, column=column, columnspan=columnspan)

        self._items = {}
        self._tv = ttk.Treeview(treeview_scrollbar_combo, columns=('value'), show='tree headings',
                                selectmode='browse', height=height)

        self._tv.column('value', width=220)

        scrollbar = ttk.Scrollbar(treeview_scrollbar_combo, orient=tkinter.VERTICAL, command=self._tv.yview)
        scrollbar.grid(row=0, column=1, sticky='NWS')
        self._tv.configure(yscrollcommand=scrollbar.set)
        self._tv.grid(row=0, column=0, sticky='E')

        self._context_menu = tkinter.Menu(self._tv, tearoff=0)
        self._context_menu.add_command(label='Copy Value', command=self._HandleCopy)
        for action in additional_context_actions:
            self._context_menu.add_command(label=action,
                                           command=lambda a=action: self._HandleAction(additional_context_actions[a]))

        self._tv.bind('<Button-3>', self._HandleRightClick)

    def UpdateData(self, data: dict) -> None:
        found_items = self._UpdateDict(data, '', '')
        missing_items = set(self._items.keys()) - set(found_items)
        for key in missing_items:
            try:
                self._tv.delete(self._items[key])
            except tkinter.TclError:
                pass
            del self._items[key]

    def _UpdateDict(self, data: any, key_prefix: str, parent: str) -> list[str]:
        found_items = []

        for key in data:
            item_key = f'{key_prefix}{key}'
            if key == '__value':
                pass
            elif type(data[key]) == dict:
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key].get('__value', ''),))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key].get('__value', ''),))
                    self._items[item_key] = item
                found_items.append(item_key)
                found_items.extend(self._UpdateDict(data[key], f'{key_prefix}{key}.', item))
            elif type(data[key]) == list or type(data[key]) == set:
                if item_key in self._items:
                    item = self._items[item_key]
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=('',))
                    self._items[item_key] = item
                found_items.append(item_key)

                d = {}
                for i in range(0, len(data[key])):
                    d[str(i)] = data[key][i]

                found_items.extend(self._UpdateDict(d, f'{key_prefix}{key}.', item))
            else:
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key],))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key],))
                    self._items[item_key] = item
                found_items.append(item_key)

        return found_items

    def _HandleRightClick(self, event) -> None:
        item = self._tv.identify_row(event.y)
        if item:
            self._tv.selection_set(item)
            self._context_menu.tk_popup(event.x_root, event.y_root)

    def _HandleCopy(self) -> None:
        selection = self._tv.selection()
        if len(selection) < 1:
            return

        print(self._tv.item(selection[0])['values'][0])

    def _HandleAction(self, callback: callable) -> None:
        selection = self._tv.selection()
        print(selection, callback)
        if len(selection) < 1:
            return

        callback(self._tv.item(selection[0])['text'])


class TasksTab(DebugTab):
    _cb1_label: ttk.Label
    _cb2_label: ttk.Label
    _tv: FancyTreeview

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text='Callback 1:').grid(row=0, column=0)
        self._cb1_label = ttk.Label(frame, text='', padding=(10, 0))
        self._cb1_label.grid(row=0, column=1, sticky='W')

        ttk.Label(frame, text='Callback 2:', padding=(0, 10)).grid(row=1, column=0)
        self._cb2_label = ttk.Label(frame, text='', padding=(10, 10))
        self._cb2_label.grid(row=1, column=1, sticky='W')

        self._tv = FancyTreeview(frame, height=16, row=2, columnspan=2)

        root.add(frame, text='Tasks')

    def Update(self, emulator: 'LibmgbaEmulator'):
        callback1 = ReadSymbol("gMain", 0, 4)
        callback2 = ReadSymbol("gMain", 4, 4)

        cb1_addr = int(struct.unpack("<I", callback1)[0]) - 1
        cb2_addr = int(struct.unpack("<I", callback2)[0]) - 1

        self._cb1_label.config(text=GetSymbolName(cb1_addr, pretty_name=True))
        self._cb2_label.config(text=GetSymbolName(cb2_addr, pretty_name=True))

        data = {}
        index = 0
        for task in ParseTasks(pretty_names=True):
            if task['func'].upper() == 'TASKDUMMY' or task['func'] == b'\x00\x00\x00\x00' or not task['isActive']:
                continue

            data[task['func']] = {
                '__value': task['data'].rstrip(b'\00').hex(' ', 1),
                'function': task['func'],
                'active': task['isActive'],
                'priority': task['priority'],
                'data': task['data'].hex(' ', 1)
            }
            index += 1

        self._tv.UpdateData(data)


class BattleTab(DebugTab):
    _tv: FancyTreeview

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text='Battle')

    def Update(self, emulator: 'LibmgbaEmulator'):
        self._tv.UpdateData(self._GetData())

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


class SymbolsTab(DebugTab):
    SYMBOLS_TO_DISPLAY = {'gObjectEvents', 'sChat', 'gStringVar1', 'gStringVar2', 'gStringVar3', 'gStringVar4'}
    DISPLAY_AS_STRING = {'sChat', 'gStringVar1', 'gStringVar2', 'gStringVar3', 'gStringVar4'}
    _tv: FancyTreeview

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)

        available_symbols = []
        for key in _reverse_symbols:
            symbol = _reverse_symbols[key]
            if symbol[2] > 0 and \
                    (symbol[1].startswith('s') or symbol[1].startswith('l') or symbol[1].startswith('g')) and \
                    symbol[1][1] == symbol[1][1].upper():
                available_symbols.append(symbol[1])

        self._combobox = ttk.Combobox(frame, values=available_symbols)
        self._combobox.grid(row=0, column=0)
        self._combobox.bind('<<ComboboxSelected>>', self._HandleNewSymbol)

        context_actions = {
            'Remove from List': self._HandleRemoveSymbol,
            'Toggle String Decoding': self._HandleToggleSymbol
        }

        self._tv = FancyTreeview(frame, row=1, height=18, additional_context_actions=context_actions)

        root.add(frame, text='Symbols')

    def Update(self, emulator: 'LibmgbaEmulator'):
        data = {}

        for symbol in self.SYMBOLS_TO_DISPLAY:
            value = ReadSymbol(symbol.upper())
            if symbol in self.DISPLAY_AS_STRING:
                data[symbol] = DecodeString(value)
            else:
                data[symbol] = value.hex(' ', 1)

        self._tv.UpdateData(data)

    def _HandleNewSymbol(self, event):
        new_symbol = self._combobox.get()
        try:
            GetSymbol(new_symbol)
            self.SYMBOLS_TO_DISPLAY.add(new_symbol)
        except RuntimeError:
            pass

    def _HandleRemoveSymbol(self, symbol: str):
        self.SYMBOLS_TO_DISPLAY.remove(symbol)
        self.DISPLAY_AS_STRING.remove(symbol)

    def _HandleToggleSymbol(self, symbol: str):
        if symbol in self.DISPLAY_AS_STRING:
            self.DISPLAY_AS_STRING.remove(symbol)
        else:
            self.DISPLAY_AS_STRING.add(symbol)


class TrainerTab(DebugTab):
    _tv: FancyTreeview

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text='Trainer')

    def Update(self, emulator: 'LibmgbaEmulator'):
        self._tv.UpdateData(self._GetData())

    def _GetData(self):
        data = GetTrainer()
        party = GetParty()

        map_name = ''
        if GetROM().game_title in ['POKEMON EMER', 'POKEMON RUBY', 'POKEMON SAPP']:
            from modules.data.MapData import mapRSE
            try:
                map_name = mapRSE(data['map']).name
            except ValueError:
                pass

        result = {
            'Name': data['name'],
            'Gender': data['gender'],
            'Trainer ID': data['tid'],
            'Secret ID': data['sid'],
            'Map': data['map'],
            'Map Name': map_name,
            'Local Coordinates': data['coords'],
            'Facing Direction': data['facing'],
            'On Bike': data['on_bike'],
        }

        for i in range(0, 6):
            key = f'Party Pokémon #{i + 1}'
            if len(party) <= i:
                result[key] = {'__value': 'n/a'}
                continue

            result[key] = party[i]

            if party[i]['isEgg']:
                result[key]['__value'] = 'Egg'
            else:
                result[key]['__value'] = f"{party[i]['name']} (lvl. {party[i]['level']})"

        return result


class DaycareTab(DebugTab):
    _tv: FancyTreeview

    def Draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text='Daycare')

    def Update(self, emulator: 'LibmgbaEmulator'):
        self._tv.UpdateData(self._GetData())

    def _GetData(self):
        data = GetDaycareData()

        pokemon1 = 'n/a'
        if data.pokemon1 is not None:
            gender = f'({PokemonGender.GetFromPokemonData(data.pokemon1).name})'
            if gender == PokemonGender.Genderless:
                gender = ''

            pokemon1 = {
                '__value': f"{data.pokemon2['name']}{gender}; {data.pokemon1_steps:,} steps",
                'pokemon': data.pokemon1,
                'steps': data.pokemon1_steps,
                'egg_groups': ', '.join(set(data.pokemon1_egg_groups))
            }

        pokemon2 = 'n/a'
        if data.pokemon2 is not None:
            gender = f'({PokemonGender.GetFromPokemonData(data.pokemon2).name})'
            if gender == PokemonGender.Genderless:
                gender = ''

            pokemon2 = {
                '__value': f"{data.pokemon2['name']}{gender}; {data.pokemon1_steps:,} steps",
                'pokemon': data.pokemon2,
                'steps': data.pokemon2_steps,
                'egg_groups': ', '.join(set(data.pokemon2_egg_groups))
            }

        return {
            'Patient #1': pokemon1,
            'Patient #2': pokemon2,
            'Offspring Personality': data.offspring_personality,
            'Step Counter': data.step_counter,
            'Compatibility': data.compatibility[0].name,
            'Compatibility Reason': data.compatibility[1],
        }
