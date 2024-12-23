import time
from tkinter import Tk, Toplevel, ttk, StringVar, Canvas

from modules.context import context
from modules.debug_utilities import debug_write_pokedex
from modules.pokedex import get_pokedex
from modules.pokemon import get_species_by_national_dex


class PokedexEditMenu:
    def __init__(self, main_window: Tk):
        self._main_window = main_window
        self.window: Toplevel | None = Toplevel(main_window)

        self.window.title("Edit Pokédex")
        self.window.geometry("480x640")
        self.window.protocol("WM_DELETE_WINDOW", self._remove_window)
        self.window.bind("<Escape>", self._remove_window)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.frame = ttk.Labelframe(self.window, text="Pokédex")
        self.frame.grid(sticky="NWES", padx=5, pady=5)

        canvas = Canvas(self.frame)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        inner_frame = ttk.Frame(canvas, width=400)
        inner_frame.columnconfigure(0, weight=1)
        inner_frame.columnconfigure(1, weight=1)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        self.buttons_row = ttk.Frame(self.window)
        self.buttons_row.columnconfigure(0, weight=1)
        self.buttons_row.grid(sticky="SE", row=1, column=0)

        self.clear_button = ttk.Button(self.buttons_row, text="Clear All", command=self._clear_all)
        self.clear_button.grid(sticky="NE", row=0, column=1, padx=5, pady=5)

        self.set_all_hoenn_button = ttk.Button(self.buttons_row, text="Complete Hoenn", command=self._set_all_hoenn)
        self.set_all_hoenn_button.grid(sticky="NE", row=0, column=2, padx=5, pady=5)

        self.set_all_button = ttk.Button(self.buttons_row, text="Complete All", command=self._set_all)
        self.set_all_button.grid(sticky="NE", row=0, column=3, padx=5, pady=5)

        self.save_button = ttk.Button(self.buttons_row, text="Save", command=self._save, style="Accent.TButton")
        self.save_button.grid(sticky="NE", row=0, column=4, padx=5, pady=5)

        pokedex = get_pokedex()
        self._species_vars: list[StringVar] = []
        for n in range(386):
            species = get_species_by_national_dex(n + 1)

            if species in pokedex.owned_species:
                var = StringVar(value="owned")
            elif species in pokedex.seen_species:
                var = StringVar(value="seen")
            else:
                var = StringVar(value="none")
            self._species_vars.append(var)

            label = ttk.Label(inner_frame, text=f"#{n + 1:03d} {species.name}")
            radio_none = ttk.Radiobutton(inner_frame, text="Not Known", variable=var, value="none")
            radio_seen = ttk.Radiobutton(inner_frame, text="Seen", variable=var, value="seen")
            radio_owned = ttk.Radiobutton(inner_frame, text="Owned", variable=var, value="owned")

            label.grid(sticky="W", row=n, column=0, padx=10, pady=5)
            radio_none.grid(sticky="W", row=n, column=1, padx=10, pady=5)
            radio_seen.grid(sticky="W", row=n, column=2, padx=10, pady=5)
            radio_owned.grid(sticky="W", row=n, column=3, padx=10, pady=5)

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

    def _clear_all(self) -> None:
        for var in self._species_vars:
            var.set("none")

    def _set_all_hoenn(self) -> None:
        for n in range(251, 386):
            self._species_vars[n].set("owned")

    def _set_all(self) -> None:
        for var in self._species_vars:
            var.set("owned")

    def _save(self) -> None:
        seen_species = []
        owned_species = []
        for n, var in enumerate(self._species_vars):
            if var.get() in ("seen", "owned"):
                seen_species.append(get_species_by_national_dex(n + 1))
            if var.get() == "owned":
                owned_species.append(get_species_by_national_dex(n + 1))
        debug_write_pokedex(seen_species, owned_species)
        self.close_window()


def run_edit_pokedex_screen():
    PokedexEditMenu(context.gui.window).loop()
