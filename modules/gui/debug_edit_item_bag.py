import time
from tkinter import ttk, Tk, Toplevel, StringVar, IntVar, Canvas

from modules.context import context
from modules.debug_utilities import debug_write_item_bag
from modules.items import ItemPocket, get_item_bag, _items_by_index, get_item_by_name, ItemSlot


class ItemBagEditMenu:
    def __init__(self, main_window: Tk):
        self._main_window = main_window
        self.window: Toplevel | None = Toplevel(main_window)

        self.window.title("Edit Item Bag")
        self.window.geometry("425x640")
        self.window.protocol("WM_DELETE_WINDOW", self._remove_window)
        self.window.bind("<Escape>", self._remove_window)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.window)
        self.notebook.grid(sticky="NWES", padx=5, pady=5)

        self.save_button = ttk.Button(self.window, text="Save Item Bag", command=self._save, style="Accent.TButton")
        self.save_button.grid(sticky="NE", row=1, column=0, padx=5, pady=5)

        self._frames: dict[ItemPocket, ItemPocketFrame] = {}
        for pocket in ItemPocket:
            frame = ItemPocketFrame(self.window, self.notebook, pocket)
            self._frames[pocket] = frame
            self.notebook.add(frame.frame, text=pocket.name)

    def loop(self) -> None:
        while self.window is not None:
            self.window.update_idletasks()
            self.window.update()
            time.sleep(1 / 60)

    def close_window(self) -> None:
        if self.window is not None:
            self.window.after(50, self._remove_window)

    def _remove_window(self, event=None) -> None:
        self.window.destroy()
        self.window = None

    def _save(self) -> None:
        debug_write_item_bag(
            items=self._frames[ItemPocket.Items].to_list(),
            key_items=self._frames[ItemPocket.KeyItems].to_list(),
            poke_balls=self._frames[ItemPocket.PokeBalls].to_list(),
            tms_hms=self._frames[ItemPocket.TmsAndHms].to_list(),
            berries=self._frames[ItemPocket.Berries].to_list(),
        )
        self.close_window()


class ItemPocketFrame:
    def __init__(self, window: Toplevel, parent: ttk.Widget, pocket: ItemPocket) -> None:
        self._window = window
        self._parent = parent
        self._pocket = pocket

        match pocket:
            case ItemPocket.Items:
                slots = get_item_bag().items
            case ItemPocket.KeyItems:
                slots = get_item_bag().key_items
            case ItemPocket.PokeBalls:
                slots = get_item_bag().poke_balls
            case ItemPocket.TmsAndHms:
                slots = get_item_bag().tms_hms
            case ItemPocket.Berries | _:
                slots = get_item_bag().berries

        self._slot_size = 999 if pocket is ItemPocket.Berries or context.rom.is_frlg else 99
        self._item_vars: list[StringVar] = []
        self._quantity_vars: list[IntVar] = []

        for n in range(pocket.capacity):
            self._item_vars.append(StringVar(value=slots[n].item.name if n < len(slots) else "(Empty)"))
            self._quantity_vars.append(IntVar(value=slots[n].quantity if n < len(slots) else 0))

        self.frame = self._build_frame()

    def to_list(self) -> list[ItemSlot]:
        result = []
        for n in range(self._pocket.capacity):
            item_name = self._item_vars[n].get()
            quantity = self._quantity_vars[n].get()
            if item_name != "(Empty)" and quantity > 0:
                result.append(ItemSlot(get_item_by_name(item_name), quantity))
        return result

    def _build_frame(self) -> ttk.Frame:
        frame = ttk.Frame(self._parent)

        canvas = Canvas(frame)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        inner_frame = ttk.Frame(canvas, width=400)
        inner_frame.columnconfigure(0, weight=1)
        inner_frame.columnconfigure(1, weight=1)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        item_names = [
            "(Empty)",
            *[
                item.name
                for item in _items_by_index
                if item.pocket is self._pocket and item.index > 0 and not item.name.startswith("?")
            ],
        ]
        item_names.sort()
        for n in range(self._pocket.capacity):
            label = ttk.Label(inner_frame, text=f"#{n + 1}")
            label.grid(sticky="e", row=n, column=0, padx=5, pady=5)

            combobox = ttk.Combobox(inner_frame, values=item_names, state="readonly", textvariable=self._item_vars[n])
            combobox.grid(sticky="e", row=n, column=1, padx=5, pady=5)

            spinbox = ttk.Spinbox(
                inner_frame, from_=0, to=self._slot_size, textvariable=self._quantity_vars[n], width=4
            )
            spinbox.grid(sticky="w", row=n, column=2, padx=5, pady=5)

        return frame


def run_edit_item_bag_screen():
    ItemBagEditMenu(context.gui.window).loop()
