from datetime import date, datetime
from tkinter import Tk, ttk, StringVar
from typing import Union

from modules.profiles import Profile, list_available_profiles


class SelectProfileScreen:
    def __init__(self, window: Tk, enable_profile_creation_screen: callable, run_profile: callable):
        self.window = window
        self.enable_profile_creation_screen = enable_profile_creation_screen
        self.run_profile = run_profile
        self.frame: Union[ttk.Frame, None] = None

        self._filter_term = ""
        self._order_by = "last_played"
        self._order_descending = True

    def enable(self) -> None:
        available_profiles = list_available_profiles()
        if len(available_profiles) == 0:
            self.enable_profile_creation_screen()
            return

        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self.window, padding=10)
        self.frame.grid(sticky="NSWE")
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self._add_header_and_controls()
        self._add_profile_list(available_profiles)

    def disable(self) -> None:
        if self.frame:
            self.frame.destroy()

    def _add_header_and_controls(self, row: int = 0) -> None:
        header = ttk.Frame(self.frame)
        style = ttk.Style()
        style.map(
            "Accent.TButton",
            foreground=[("!active", "white"), ("active", "white"), ("pressed", "white")],
            background=[("!active", "green"), ("active", "darkgreen"), ("pressed", "green")],
        )
        header.grid(row=row, sticky="NEW")
        header.columnconfigure(0, weight=1)

        label = ttk.Label(header, text="Select a profile to run:")
        label.grid(column=0, row=0, sticky="W")

        new_profile_button = ttk.Button(
            header,
            text="+ New profile",
            command=self.enable_profile_creation_screen,
            style="Accent.TButton",
            cursor="hand2",
        )
        new_profile_button.grid(column=1, row=0, sticky="E")

    def _add_profile_list(self, available_profiles: list[Profile], row: int = 1) -> None:
        container = ttk.Frame(self.frame, padding=(0, 10, 0, 0))
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)
        container.grid(row=row, sticky="NSEW")

        treeview = ttk.Treeview(
            container, columns=("profile_name", "game", "last_played"), show="headings", selectmode="browse"
        )
        treeview.column("profile_name", width=200)
        treeview.heading("profile_name", text="Profile Name", command=lambda: sort_by("profile_name"))
        treeview.column("game", width=150)
        treeview.heading("game", text="Game", command=lambda: sort_by("game"))
        treeview.column("last_played", width=170)
        treeview.heading("last_played", text="Last Played ↑", command=lambda: sort_by("last_played"))

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=treeview.yview)
        scrollbar.grid(row=0, column=1, sticky="NWS")
        treeview.configure(yscrollcommand=scrollbar.set)
        treeview.grid(row=0, column=0, sticky="NSE")

        entry_map: dict[str, str] = {}
        detached_entries: dict[str, str] = {}

        available_profiles.sort(reverse=True, key=lambda p: p.last_played or datetime(1, 1, 1, 0, 0, 0))
        for profile in available_profiles:
            if profile.last_played:
                if profile.last_played.date() == date.today():
                    last_played = f"Today, {profile.last_played.strftime('%H:%M:%S')}"
                else:
                    last_played = profile.last_played.strftime("%Y-%m-%d, %H:%M:%S")
            else:
                last_played = "never"

            data = (profile.path.name, profile.rom.short_game_name, last_played)
            entry_map[profile.path.name] = treeview.insert("", "end", text=profile.path.name, values=data)

        def on_double_click(event):
            item = treeview.identify("item", event.x, event.y)
            selected_name = treeview.item(item, "text")
            for profile in available_profiles:
                if profile.path.name == selected_name:
                    self.run_profile(profile)

        search_field: ttk.Entry | None = None

        def on_ctrl_f(event):
            nonlocal search_field
            if search_field is None:
                search_term = StringVar()
                search_field = ttk.Entry(self.frame, textvariable=search_term)
                search_field.place(x=0, y=0)
                search_field.focus_set()

                def select_all():
                    search_field.select_range(0, "end")
                    search_field.icursor("end")

                def on_change(event):
                    new_filter_term = search_term.get().lower()
                    if self._filter_term != new_filter_term:
                        self._filter_term = new_filter_term
                        update_list()

                def remove_field():
                    nonlocal search_field
                    search_field.destroy()
                    search_field = None
                    if self._filter_term != "":
                        self._filter_term = ""
                        update_list()

                search_field.bind("<Control-a>", lambda _: self.window.after(50, select_all))
                search_field.bind("<KeyRelease>", on_change)
                search_field.bind("<Escape>", lambda _: self.window.after(50, remove_field))
            else:
                search_field.destroy()

        self.window.bind("<Control-f>", on_ctrl_f)

        def sort_by(column_name: str):
            if column_name == self._order_by:
                self._order_descending = not self._order_descending
            else:
                self._order_by = column_name
                self._order_descending = column_name == "last_played"
            update_list()

        def update_list():
            arrow = "↑" if self._order_descending else "↓"
            treeview.heading("profile_name", text="Profile Name")
            treeview.heading("game", text="Game")
            treeview.heading("last_played", text="Last Played")

            if self._order_by == "profile_name":
                available_profiles.sort(reverse=self._order_descending, key=lambda p: p.path.name)
                treeview.heading("profile_name", text=f"Profile Name {arrow}")
            elif self._order_by == "game":
                available_profiles.sort(reverse=self._order_descending, key=lambda p: p.rom.short_game_name)
                treeview.heading("game", text=f"Game {arrow}")
            else:
                available_profiles.sort(
                    reverse=self._order_descending, key=lambda p: p.last_played or datetime(1, 1, 1, 0, 0, 0)
                )
                treeview.heading("last_played", text=f"Last Played {arrow}")

            index = 1
            for profile in available_profiles:
                if self._filter_term == "" or self._filter_term in profile.path.name.lower():
                    if profile.path.name in detached_entries:
                        treeview.reattach(entry_map[profile.path.name], "", index)
                        del detached_entries[profile.path.name]
                    else:
                        treeview.move(entry_map[profile.path.name], "", index)
                    index += 1
                elif profile.path.name not in detached_entries:
                    detached_entries[profile.path.name] = entry_map[profile.path.name]
                    treeview.detach(entry_map[profile.path.name])

        treeview.bind("<Double-1>", on_double_click)
