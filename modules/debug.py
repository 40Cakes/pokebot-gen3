import time
import tkinter
from enum import Enum
from tkinter import ttk
from typing import TYPE_CHECKING

from modules.daycare import get_daycare_data
from modules.game import decode_string, _reverse_symbols
from modules.gui import DebugTab, get_emulator
from modules.items import get_items
from modules.memory import (
    get_symbol,
    read_symbol,
    parse_tasks,
    get_symbol_name,
    game_has_started,
    unpack_uint16,
    unpack_uint32,
)

from modules.pokemon import get_party, get_species_by_index

if TYPE_CHECKING:
    from modules.libmgba import LibmgbaEmulator


class FancyTreeview:
    def __init__(
        self,
        root: ttk.Widget,
        height=20,
        row=0,
        column=0,
        columnspan=1,
        additional_context_actions: dict[str, callable] = {},
    ):
        treeview_scrollbar_combo = ttk.Frame(root)
        treeview_scrollbar_combo.columnconfigure(0, weight=1)
        treeview_scrollbar_combo.grid(row=row, column=column, columnspan=columnspan)

        self._items = {}
        self._tv = ttk.Treeview(
            treeview_scrollbar_combo, columns="value", show="tree headings", selectmode="browse", height=height
        )

        self._tv.column("value", width=220)

        scrollbar = ttk.Scrollbar(treeview_scrollbar_combo, orient=tkinter.VERTICAL, command=self._tv.yview)
        scrollbar.grid(row=0, column=1, sticky="NWS")
        self._tv.configure(yscrollcommand=scrollbar.set)
        self._tv.grid(row=0, column=0, sticky="E")

        self._context_menu = tkinter.Menu(self._tv, tearoff=0)
        self._context_menu.add_command(label="Copy Value", command=self._handle_copy)
        for action in additional_context_actions:
            self._context_menu.add_command(
                label=action, command=lambda a=action: self._handle_action(additional_context_actions[a])
            )

        self._tv.bind("<Button-3>", self._handle_right_click)

    def update_data(self, data: dict) -> None:
        found_items = self._update_dict(data, "", "")
        missing_items = set(self._items.keys()) - set(found_items)
        for key in missing_items:
            try:
                self._tv.delete(self._items[key])
            except tkinter.TclError:
                pass
            del self._items[key]

    def _update_dict(self, data: any, key_prefix: str, parent: str) -> list[str]:
        found_items = []

        for key in data:
            item_key = f"{key_prefix}{key}"
            if key == "__value":
                pass
            elif type(data[key]) is dict:
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key].get("__value", ""),))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key].get("__value", ""),))
                    self._items[item_key] = item
                found_items.append(item_key)
                found_items.extend(self._update_dict(data[key], f"{key_prefix}{key}.", item))
            elif isinstance(data[key], (list, set, tuple, frozenset)):
                if item_key in self._items:
                    item = self._items[item_key]
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=("",))
                    self._items[item_key] = item
                found_items.append(item_key)

                d = {}
                for i in range(0, len(data[key])):
                    d[str(i)] = data[key][i]

                found_items.extend(self._update_dict(d, f"{key_prefix}{key}.", item))
            elif isinstance(data[key], (bool, int, float, complex, str, bytes, bytearray)):
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key],))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key],))
                    self._items[item_key] = item
                found_items.append(item_key)
            elif isinstance(data[key], Enum):
                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(data[key].name,))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(data[key].name,))
                    self._items[item_key] = item
                found_items.append(item_key)
            else:
                if data[key].__str__ is not object.__str__:
                    value = str(data[key])
                else:
                    value = f"object({data[key].__class__.__name__})"

                if item_key in self._items:
                    item = self._items[item_key]
                    self._tv.item(item, values=(value,))
                else:
                    item = self._tv.insert(parent, tkinter.END, text=key, values=(value,))
                    self._items[item_key] = item
                found_items.append(item_key)

                properties = {}
                try:
                    for k in data[key].__dict__:
                        properties[k] = data[key].__dict__[k]
                except AttributeError:
                    pass
                for k in dir(data[key].__class__):
                    if isinstance(getattr(data[key].__class__, k), property):
                        properties[k] = getattr(data[key], k)

                found_items.extend(self._update_dict(properties, f"{key_prefix}{key}.", item))

        return found_items

    def _handle_right_click(self, event) -> None:
        item = self._tv.identify_row(event.y)
        if item:
            self._tv.selection_set(item)
            self._context_menu.tk_popup(event.x_root, event.y_root)

    def _handle_copy(self) -> None:
        selection = self._tv.selection()
        if len(selection) < 1:
            return

        import pyperclip3

        pyperclip3.copy(str(self._tv.item(selection[0])["values"][0]))

    def _handle_action(self, callback: callable) -> None:
        selection = self._tv.selection()
        if len(selection) < 1:
            return

        callback(self._tv.item(selection[0])["text"])


class TasksTab(DebugTab):
    _cb1_label: ttk.Label
    _cb2_label: ttk.Label
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Callback 1:").grid(row=0, column=0)
        self._cb1_label = ttk.Label(frame, text="", padding=(10, 0))
        self._cb1_label.grid(row=0, column=1, sticky="W")

        ttk.Label(frame, text="Callback 2:", padding=(0, 10)).grid(row=1, column=0)
        self._cb2_label = ttk.Label(frame, text="", padding=(10, 10))
        self._cb2_label.grid(row=1, column=1, sticky="W")

        self._tv = FancyTreeview(frame, height=16, row=2, columnspan=2)

        root.add(frame, text="Tasks")

    def update(self, emulator: "LibmgbaEmulator"):
        callback1 = read_symbol("gMain", 0, 4)
        callback2 = read_symbol("gMain", 4, 4)

        cb1_addr = unpack_uint32(callback1) - 1
        cb2_addr = unpack_uint32(callback2) - 1

        self._cb1_label.config(text=get_symbol_name(cb1_addr, pretty_name=True))
        self._cb2_label.config(text=get_symbol_name(cb2_addr, pretty_name=True))

        data = {}
        index = 0
        for task in parse_tasks(pretty_names=True):
            if task["func"].upper() == "TASKDUMMY" or task["func"] == b"\x00\x00\x00\x00" or not task["isActive"]:
                continue

            data[task["func"]] = {
                "__value": task["data"].rstrip(b"\00").hex(" ", 1),
                "function": task["func"],
                "active": task["isActive"],
                "priority": task["priority"],
                "data": task["data"].hex(" ", 1),
            }
            index += 1

        self._tv.update_data(data)


class BattleTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Battle")

    def update(self, emulator: "LibmgbaEmulator"):
        self._tv.update_data(self._get_data())

    def _get_data(self):
        data = read_symbol("gBattleResults")

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
            "Player Mon 1 Species": unpack_uint16(data[6:8]),
            "Player Mon 1 Name": decode_string(data[8:19]),  # SpeciesName(battleResult.playerMon1Species)
            "Battle turn Counter": int(data[19]),
            "Player Mon 2 Species": unpack_uint16(data[38:40]),
            "Player Mon 2 Name": decode_string(data[20:31]),
            "PokeBall Throws": int(data[31]),
            "Last Opponent Species": unpack_uint16(data[32:34]),
            "Last Opponent Name": get_species_by_index(unpack_uint16(data[32:34])).name,
            "Last used Move Player": unpack_uint16(data[34:36]),
            "Last used Move Opponent": unpack_uint16(data[36:38]),
            "Cought Mon Species": unpack_uint16(data[40:42]),
            "Cought Mon Name": decode_string(data[42:53]),
            "Catch Attempts": int(data[54]),
        }


class SymbolsTab(DebugTab):
    SYMBOLS_TO_DISPLAY = {
        "gObjectEvents",
        "sChat",
        "gStringVar1",
        "gStringVar2",
        "gStringVar3",
        "gStringVar4",
        "gDisplayedStringBattle",
    }
    DISPLAY_AS_STRING = {"sChat", "gStringVar1", "gStringVar2", "gStringVar3", "gStringVar4", "gDisplayedStringBattle"}
    _tv: FancyTreeview
    _mini_window: tkinter.Tk = None

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)

        button = ttk.Button(frame, text="Add Symbol to Watch", command=self._add_new_symbol)
        button.grid(row=0, column=0, sticky="NE")

        context_actions = {
            "Remove from List": self._handle_remove_symbol,
            "Toggle String Decoding": self._handle_toggle_symbol,
        }

        self._tv = FancyTreeview(frame, row=1, height=18, additional_context_actions=context_actions)

        root.add(frame, text="Symbols")

    def _add_new_symbol(self):
        if self._mini_window is not None:
            return

        self._mini_window = tkinter.Tk()
        self._mini_window.title("Add a symbol to list")
        self._mini_window.geometry("480x480")

        def remove_window(event=None):
            self._mini_window.destroy()
            self._mini_window = None

        self._mini_window.protocol("WM_DELETE_WINDOW", remove_window)
        self._mini_window.rowconfigure(1, weight=1)
        self._mini_window.columnconfigure(0, weight=1)

        search_input = ttk.Entry(self._mini_window)
        search_input.grid(row=0, column=0, sticky="NWE")
        search_input.focus_force()

        tv_frame = ttk.Frame(self._mini_window)
        tv_frame.columnconfigure(0, weight=1)
        tv_frame.grid(row=1, column=0, sticky="NWSE")

        tv = ttk.Treeview(
            tv_frame, columns=("name", "address", "length"), show="headings", selectmode="browse", height=22
        )

        tv.column("name", width=300)
        tv.heading("name", text="Symbol Name")

        tv.column("address", width=90)
        tv.heading("address", text="Address")

        tv.column("length", width=90)
        tv.heading("length", text="Length")

        items: dict[str, str] = {}
        detached_items = set()
        for address in _reverse_symbols:
            _, symbol, length = _reverse_symbols[address]
            if length == 0:
                continue
            if not (symbol.startswith("s") or symbol.startswith("l") or symbol.startswith("g")):
                continue
            if symbol[1] != symbol[1].upper():
                continue
            if symbol in self.SYMBOLS_TO_DISPLAY:
                continue

            if symbol not in items:
                items[symbol] = tv.insert("", tkinter.END, text=symbol, values=(symbol, hex(address), hex(length)))

        def handle_input(event=None):
            search_term = search_input.get().strip().lower()
            for key in items:
                if search_term in key.lower() and key in detached_items:
                    tv.reattach(items[key], "", 0)
                    detached_items.remove(key)
                elif search_term not in key.lower() and key not in detached_items:
                    tv.detach(items[key])
                    detached_items.add(key)

        search_input.bind("<KeyRelease>", handle_input)

        def handle_double_click(event):
            if self._mini_window is not None:
                item = tv.identify_row(event.y)
                if item:
                    self.SYMBOLS_TO_DISPLAY.add(tv.item(item)["text"])
                    self.update(get_emulator())

        tv.bind("<Double-Button-1>", handle_double_click)

        scrollbar = ttk.Scrollbar(tv_frame, orient=tkinter.VERTICAL, command=tv.yview)
        scrollbar.grid(row=0, column=1, sticky="NWS")
        tv.configure(yscrollcommand=scrollbar.set)
        tv.grid(row=0, column=0, sticky="E")

        def handle_focus_out(event=None):
            if self._mini_window.focus_get() is None:
                remove_window()

        self._mini_window.bind("<FocusOut>", handle_focus_out)
        self._mini_window.bind("<Escape>", remove_window)
        self._mini_window.bind("<Control-q>", remove_window)

        while self._mini_window is not None and self._mini_window.state() != "destroyed":
            self._mini_window.update_idletasks()
            self._mini_window.update()
            time.sleep(1 / 60)

    def update(self, emulator: "LibmgbaEmulator"):
        data = {}

        for symbol in self.SYMBOLS_TO_DISPLAY:
            try:
                address, length = get_symbol(symbol.upper())
            except RuntimeError:
                self.SYMBOLS_TO_DISPLAY.remove(symbol)
                self.DISPLAY_AS_STRING.remove(symbol)
                break

            value = emulator.read_bytes(address, length)
            if symbol in self.DISPLAY_AS_STRING:
                data[symbol] = decode_string(value)
            elif length == 4 or length == 2:
                n = int.from_bytes(value, byteorder="little")
                data[symbol] = f"{value.hex(' ', 1)} ({n})"
            else:
                data[symbol] = value.hex(" ", 1)

        self._tv.update_data(data)

    def _handle_new_symbol(self, event):
        new_symbol = self._combobox.get()
        try:
            get_symbol(new_symbol)
            self.SYMBOLS_TO_DISPLAY.add(new_symbol)
        except RuntimeError:
            pass

    def _handle_remove_symbol(self, symbol: str):
        self.SYMBOLS_TO_DISPLAY.remove(symbol)
        self.DISPLAY_AS_STRING.remove(symbol)

    def _handle_toggle_symbol(self, symbol: str):
        if symbol in self.DISPLAY_AS_STRING:
            self.DISPLAY_AS_STRING.remove(symbol)
        else:
            self.DISPLAY_AS_STRING.add(symbol)


class TrainerTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Trainer")

    def update(self, emulator: "LibmgbaEmulator"):
        if game_has_started():
            self._tv.update_data(self._get_data())
        else:
            self._tv.update_data({})

    def _get_data(self):
        from modules.trainer import trainer, AcroBikeStates, RunningStates, TileTransitionStates

        party = get_party()

        result = {
            "Name": trainer.get_name(),
            "Gender": trainer.get_gender(),
            "Trainer ID": trainer.get_tid(),
            "Secret ID": trainer.get_sid(),
            "Map": trainer.get_map(),
            "Map Name": trainer.get_map_name(),
            "Local Coordinates": trainer.get_coords(),
            "On Bike": trainer.get_on_bike(),
            "Running State": RunningStates(trainer.get_running_state()).name,
            "Acro Bike State": AcroBikeStates(trainer.get_acro_bike_state()).name,
            "Tile Transition State": TileTransitionStates(trainer.get_tile_transition_state()).name,
            "Facing Direction": trainer.get_facing_direction(),
        }

        for i in range(0, 6):
            key = f"Party Pokémon #{i + 1}"
            if len(party) <= i or party[i].is_empty:
                result[key] = {"__value": "n/a"}
                continue

            result[key] = party[i]

        result["Items"] = get_items()

        return result


class DaycareTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Daycare")

    def update(self, emulator: "LibmgbaEmulator"):
        self._tv.update_data(self._get_data())

    def _get_data(self):
        data = get_daycare_data()
        if data is None:
            return {}

        pokemon1 = "n/a"
        if data.pokemon1 is not None and not data.pokemon1.is_empty:
            gender = ""
            if data.pokemon1.gender is not None:
                gender = f" ({data.pokemon1.gender})"

            pokemon1 = {
                "__value": f"{data.pokemon1.species.name}{gender}; {data.pokemon1_steps:,} steps",
                "pokemon": data.pokemon1,
                "steps": data.pokemon1_steps,
                "egg_groups": ", ".join(set(data.pokemon1_egg_groups)),
            }

        pokemon2 = "n/a"
        if data.pokemon2 is not None and not data.pokemon2.is_empty:
            gender = ""
            if data.pokemon2.gender is not None:
                gender = f" ({data.pokemon2.gender})"

            pokemon2 = {
                "__value": f"{data.pokemon2.species.name}{gender}; {data.pokemon1_steps:,} steps",
                "pokemon": data.pokemon2,
                "steps": data.pokemon2_steps,
                "egg_groups": ", ".join(set(data.pokemon2_egg_groups)),
            }

        return {
            "Pokémon #1": pokemon1,
            "Pokémon #2": pokemon2,
            "Offspring Personality": data.offspring_personality,
            "Step Counter": data.step_counter,
            "Compatibility": data.compatibility[0].name,
            "Compatibility Reason": data.compatibility[1],
        }


class EventFlagsTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Event Flags")

    def update(self, emulator: "LibmgbaEmulator"):
        self._tv.update_data(self._get_data())

    def _get_data(self):
        from modules.game import _event_flags
        from modules.memory import get_event_flag

        result = {}

        for flag in _event_flags:
            result[flag] = get_event_flag(flag)

        return result


class InputsTab(DebugTab):
    _tv: FancyTreeview

    def draw(self, root: ttk.Notebook):
        frame = ttk.Frame(root, padding=10)
        self._tv = FancyTreeview(frame)
        root.add(frame, text="Inputs")

    def update(self, emulator: "LibmgbaEmulator"):
        self._tv.update_data(self._get_data())

    def _get_data(self):
        from modules.libmgba import input_map

        result = {}
        inputs = get_emulator().get_inputs()

        for input in input_map:
            result[input] = True if input_map[input] & inputs else False

        return result
