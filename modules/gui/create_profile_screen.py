import re
from tkinter import Tk, ttk, StringVar
from typing import Union

import plyer
from PIL import Image, ImageTk, ImageOps

from modules.profiles import list_available_profiles, profile_directory_exists, create_profile
from modules.roms import ROM, list_available_roms
from modules.runtime import get_sprites_path
from modules.save_import import migrate_save_state, MigrationError
from modules.version import pokebot_name


class CreateProfileScreen:
    def __init__(self, window: Tk, enable_profile_selection_screen: callable, run_profile: callable):
        self.window = window
        self.enable_profile_selection_screen = enable_profile_selection_screen
        self.run_profile = run_profile
        self.frame: ttk.Frame | None = None

    def enable(self) -> None:
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self.window, padding=10)
        self.frame.grid(sticky="NSWE")
        self.frame.rowconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)

        if len(list_available_roms()) == 0:
            self._show_missing_roms_screen()
            return

        if len(list_available_profiles()) == 0:
            self.window.geometry("540x480")
            self._show_welcome_message()
        else:
            self._show_return_button()

        self._add_form()

    def disable(self) -> None:
        if self.frame:
            self.frame.destroy()

    def _show_return_button(self, row: int = 0) -> None:
        button = ttk.Button(self.frame, text="Back to Profile Selection", command=self.enable_profile_selection_screen,
                            cursor="hand2")
        button.grid(sticky="NE", row=row)

    def _show_welcome_message(self, row: int = 0) -> None:
        welcome_text = (
            f"Hey! This seems to be your first launch of {pokebot_name}.\n\n"
            "To get started you first need to create a profile.\n\n"
            "A profile stores your save game, save states, bot config, "
            'bot statistics, screenshots etc. Profiles are stored in the "profiles/" folder.\n'
        )

        container = ttk.Frame(self.frame, padding=(0, 40, 0, 0))
        container.grid(sticky="N", row=row)

        birch_sprite = Image.open(get_sprites_path() / "other" / "Birch.png")
        birch_sprite = ImageOps.scale(birch_sprite, 2, resample=False)
        flipped_birch_sprite = ImageOps.mirror(birch_sprite)
        birch_image = ImageTk.PhotoImage(birch_sprite)
        flipped_birch_image = ImageTk.PhotoImage(flipped_birch_sprite)

        icon = ttk.Label(container, image=flipped_birch_image, padding=(0, 0, 15, 0))
        icon.grid(sticky="N", row=0, column=0)
        icon.img1 = birch_image
        icon.img2 = flipped_birch_image
        # Very important.
        icon.bind("<Button-1>", lambda *_: icon.config(
            image=(flipped_birch_image if icon.cget("image")[0] == str(birch_image) else birch_image)))

        text = ttk.Label(container, text=welcome_text, wraplength=360)
        text.grid(sticky="N", row=0, column=1)

    def _add_form(self, row: int = 1) -> None:
        container = ttk.LabelFrame(self.frame, text="Create a New Profile", padding=(20, 10))
        container.grid(row=row, sticky="N")

        label_padding = (0, 6, 10, 6)

        ttk.Label(container, text="Name:", padding=label_padding).grid(row=0, column=0, sticky="W")

        sv_name = StringVar()
        name_pattern = re.compile("^[-_a-zA-Z0-9 ]+$")

        def select_all(widget: ttk.Entry):
            widget.select_range(0, 'end')
            widget.icursor('end')

        def handle_name_input_change(name, index, mode, sv=sv_name):
            value = sv.get()
            message_label.grid(row=3, column=0, columnspan=2)
            if value == "":
                new_game_button.config(state="disabled")
                load_save_button.config(state="disabled")
                entry.state(["invalid"])
                message_label.config(text="Please enter a profile name.")
            elif not name_pattern.match(value):
                new_game_button.config(state="disabled")
                load_save_button.config(state="disabled")
                entry.state(["invalid"])
                message_label.config(
                    text=(
                        "The profile name can only contain alphanumerical characters (Aa-Zz, 0-9), "
                        "underscores and hyphens."
                    ),
                    foreground="red",
                )
            elif profile_directory_exists(value):
                new_game_button.config(state="disabled")
                load_save_button.config(state="disabled")
                entry.state(["invalid"])
                message_label.config(text=f'A profile named "{value}" already exists.', foreground="red")
            else:
                new_game_button.config(state="normal")
                load_save_button.config(state="normal")
                entry.state(["!invalid"])
                message_label.config(text="")
                message_label.grid_remove()

        sv_name.trace("w", handle_name_input_change)

        entry = ttk.Entry(container, textvariable=sv_name)
        entry.grid(column=1, row=0, sticky="EW")
        entry.bind('<Control-a>', lambda e: self.window.after(50, select_all, e.widget))

        available_roms = list_available_roms()
        rom_names = []
        for rom in available_roms:
            rom_names.append(rom.short_game_name)

        ttk.Label(container, text="Game:", padding=label_padding).grid(row=1, column=0, sticky="W")
        rom_input = ttk.Combobox(container, values=sorted(rom_names), width=28, state="readonly")
        rom_input.current(0)
        rom_input.grid(column=1, row=1)

        def get_selected_rom() -> Union[ROM, None]:
            selected_rom_name = rom_input.get()
            for rom in available_roms:
                if rom.short_game_name == selected_rom_name:
                    return rom
            return None

        def handle_create_new_game_press():
            name = sv_name.get()
            selected_rom = get_selected_rom()
            if selected_rom is None:
                return

            profile = create_profile(name, selected_rom)
            self.run_profile(profile)

        def handle_load_save_press():
            def handle_selected_file(selection: list[str]) -> None:
                if selection is None or len(selection) < 1:
                    return
                selected_rom = get_selected_rom()
                if selected_rom is None:
                    return
                try:
                    with open(selection[0], "rb") as file:
                        profile = migrate_save_state(file, sv_name.get(), selected_rom)
                    self.run_profile(profile)
                except MigrationError as error:
                    message_label.config(text=str(error), foreground="red")
                    message_label.grid(row=3, column=0, columnspan=2)

            plyer.filechooser.open_file(
                filters=[["Save Games", "*.ss0", "*.ss1", "*.ss2", "*.ss3", "*.ss4", "*.ss5", "*.ss6", "*.ss7", "*.ss8",
                          "*.ss9"]],
                title="Load Existing Save",
                on_selection=handle_selected_file)

        button_container = ttk.Frame(container, padding=(0, 15, 0, 5))
        button_container.grid(row=2, column=0, columnspan=2)
        button_container.columnconfigure(0, weight=1)
        button_container.columnconfigure(1, minsize=10)
        button_container.columnconfigure(2, weight=1)

        new_game_button = ttk.Button(button_container, text="Start New Game", cursor="hand2", state="disabled",
                                     command=handle_create_new_game_press, style="Accent.TButton")
        new_game_button.grid(column=0, row=0)

        load_save_button = ttk.Button(button_container, text="Load Existing Save", cursor="hand2", state="disabled",
                                      command=handle_load_save_press)
        load_save_button.grid(column=2, row=0)

        message_label = ttk.Label(container, text="", wraplength=340, padding=(0, 15, 0, 0))

    def _show_missing_roms_screen(self) -> None:
        group = ttk.Frame(self.frame)
        group.grid()

        error_message = ("There don't seem to be any Pokémon ROMs in the 'roms/' folder. "
                         "Please add some and retry.\n\n"
                         "Note that only the original ROMs for Pokémon Ruby, Sapphire, Emerald, FireRed and LeafGreen "
                         "are supported by this bot. Any modified ROM will not be detected.")
        message = ttk.Label(group, text=error_message, wraplength=300, foreground="red", padding=(0, 0, 0, 25))
        message.grid(row=0, column=0, sticky="S")

        def handle_button_click() -> None:
            if len(list_available_roms(force_recheck=True)) > 0:
                self.disable()
                self.enable()

        button = ttk.Button(group, text="Try again", command=handle_button_click, cursor="hand2")
        button.grid(row=1, column=0, sticky="N")
