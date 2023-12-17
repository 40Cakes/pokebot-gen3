from datetime import datetime, date
from tkinter import Tk, ttk
from typing import Union

from modules.profiles import Profile, list_available_profiles


class SelectProfileScreen:
    def __init__(self, window: Tk, enable_profile_creation_screen: callable, run_profile: callable):
        self.window = window
        self.enable_profile_creation_screen = enable_profile_creation_screen
        self.run_profile = run_profile
        self.frame: Union[ttk.Frame, None] = None


        self.color_themes = [
            {"name": "Dark Theme", "background": "#333", "foreground": "#fff"},
            {"name": "Light Theme", "background": "#fff", "foreground": "#333"},
            {"name": "Dark Green Theme", "background": "#333", "foreground": "#00ff22"},
            {"name": "Dark Blue Theme", "background": "#333", "foreground": "#00ddff"},
            {"name": "Black Theme", "background": "#000000", "foreground": "#fff"},
            {"name": "Black Green Theme", "background": "#000000", "foreground": "#00ff22"},
            {"name": "Black Blue Theme", "background": "#000000", "foreground": "#00ddff"},
            {"name": "Black Red Theme", "background": "#000000", "foreground": "#f50505"},
            # Add more themes as needed
        ]
        # Add the combo box for selecting color themes
        self.theme_combobox = ttk.Combobox(self.window, values=[theme["name"] for theme in self.color_themes])
        self.theme_combobox.bind("<<ComboboxSelected>>", self._update_color_theme)
        self.theme_combobox.set(self.color_themes[0]["name"])  # Set the default theme name

    def _update_color_theme(self, event=None):
        # Get the selected theme index
        selected_theme_index = self.theme_combobox.current()

        # Update background and foreground colors based on the selected theme
        if selected_theme_index is not None:
            selected_theme = self.color_themes[selected_theme_index]
            background_color = selected_theme["background"]
            foreground_color = selected_theme["foreground"]

            # Update style configurations
            style = ttk.Style()
            style.configure("TFrame", background=background_color, foreground=foreground_color)
            style.configure("TEntry", background=background_color, foreground=foreground_color)
            style.configure("TButton", background=background_color, foreground=foreground_color)
            style.configure("TMessage", background=background_color, foreground=foreground_color)  # Corrected name
            style.configure("Treeview", background=background_color, foreground=foreground_color)  # Corrected name
            style.configure("TSpinbox", background=background_color, foreground=foreground_color)
            style.configure("TScrollbar", background=background_color, foreground=foreground_color)
            style.configure("TBackground", background=background_color, foreground=foreground_color)
            style.configure("TCombobox", background=background_color, foreground=foreground_color)  # Corrected name
            style.configure("TSpinbox", background=background_color, foreground=foreground_color)
            style.configure("TRadiobutton", background=background_color, foreground=foreground_color)
            style.configure("Nested.TFrame", background=background_color, foreground=foreground_color)
            style.configure("TCheckbutton", background=background_color, foreground=foreground_color)
            style.configure("TLabel", background=background_color, foreground=foreground_color)
            style.configure("TText", background=background_color, foreground=foreground_color)
            style.configure("Checkbutton.indicator", background=background_color, foreground=foreground_color)
            style.configure("Radiobutton.indicator", background=background_color, foreground=foreground_color)
            style.configure("Menubutton.indicator", background=background_color, foreground=foreground_color)

            style.theme_use("default")
            style.map(
                "Accent.TButton",
                foreground=[("!active", foreground_color), ("active", "black"), ("pressed", background_color)],
                background=[("!active", "purple"), ("active", "purple"), ("pressed", foreground_color)],
            )

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

        # Place the combo box in the header
        self.theme_combobox.grid(row=1, column=0, padx=0, pady=0, sticky="W")  # Adjust column and padding as needed


    def disable(self) -> None:
        if self.frame:
            self.frame.destroy()

    def _add_header_and_controls(self, row: int = 0) -> None:
        header = ttk.Frame(self.frame)
        header.grid(row=row, sticky="NEW")
        header.columnconfigure(0, weight=1)
        header.columnconfigure(2, weight=1)  # Add a column for the combo box

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
        treeview.heading("profile_name", text="Profile Name")
        treeview.column("game", width=150)
        treeview.heading("game", text="Game")
        treeview.column("last_played", width=170)
        treeview.heading("last_played", text="Last Played")

        scrollbar = ttk.Scrollbar(container, orient="vertical", command=treeview.yview)
        scrollbar.grid(row=0, column=1, sticky="NWS")
        treeview.configure(yscrollcommand=scrollbar.set)
        treeview.grid(row=0, column=0, sticky="NSE")

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
            treeview.insert("", "end", text=profile.path.name, values=data)

        def on_double_click(event):
            item = treeview.identify("item", event.x, event.y)
            selected_name = treeview.item(item, "text")
            for profile in available_profiles:
                if profile.path.name == selected_name:
                    self.run_profile(profile)

        treeview.bind("<Double-1>", on_double_click)
