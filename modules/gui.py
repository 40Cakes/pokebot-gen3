import os
import platform
import random
import re
import time
import tkinter
import tkinter.font
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Union

import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import PIL.ImageTk

import modules.game
from modules.config import available_bot_modes, config, load_config, keys_schema, set_bot_mode, toggle_manual_mode
from modules.console import console
from modules.libmgba import LibmgbaEmulator, input_map
from modules.profiles import Profile, list_available_profiles, profile_directory_exists, create_profile
from modules.roms import ROM, list_available_roms
from modules.version import pokebot_name, pokebot_version


gui: "PokebotGui" = None
emulator: LibmgbaEmulator = None
profile: Profile = None


def set_message(message: str) -> None:
    if gui is not None:
        gui.set_message(message)


def get_emulator() -> LibmgbaEmulator:
    return emulator


def get_profile() -> Profile:
    return profile


def get_rom() -> ROM:
    if not profile:
        return None
    return profile.rom


class EmulatorControls:
    frame: Union[tkinter.Frame, None] = None
    bot_mode_combobox: ttk.Combobox
    speed_1x_button: tkinter.Button
    speed_2x_button: tkinter.Button
    speed_3x_button: tkinter.Button
    speed_4x_button: tkinter.Button
    unthrottled_button: tkinter.Button
    toggle_video_button: tkinter.Button
    toggle_audio_button: tkinter.Button
    bot_message: tkinter.Label

    default_button_background = None
    default_button_foreground = None

    def __init__(self, gui: "PokebotGui", window: tkinter.Tk):
        self.gui = gui
        self.window = window
        self.last_known_bot_mode = config["general"]["bot_mode"]

    def get_additional_width(self):
        return 0

    def get_additional_height(self):
        return 165

    def add_to_window(self):
        self.frame = tkinter.Frame(self.window, padx=5, pady=5)
        self.frame.grid(row=1, sticky="WE")
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self._add_bot_mode_controls(row=0, column=0)
        self._add_speed_controls(row=0, column=1, sticky="N")
        self._add_settings_controls(row=0, column=2)

        self._add_message_area(row=1, column=0, columnspan=3)
        self._add_version_notice(row=2, column=0, columnspan=3)

        self.update()

    def remove_from_window(self):
        if self.frame:
            self.frame.destroy()

        self.frame = None

    def update(self):
        if self.frame is None:
            return

        # This avoids any other GUI element from having the focus. We don't want that because
        # for example if the bot mode combobox is focussed, pressing Down might open the
        # dropdown menu.
        self.window.focus()

        if self.bot_mode_combobox.get() != config["general"]["bot_mode"]:
            self.bot_mode_combobox.current(available_bot_modes.index(config["general"]["bot_mode"]))
            self.last_known_bot_mode = config["general"]["bot_mode"]

        self._set_button_colour(self.speed_1x_button, emulator.get_throttle() and emulator.get_speed_factor() == 1)
        self._set_button_colour(self.speed_2x_button, emulator.get_throttle() and emulator.get_speed_factor() == 2)
        self._set_button_colour(self.speed_3x_button, emulator.get_throttle() and emulator.get_speed_factor() == 3)
        self._set_button_colour(self.speed_4x_button, emulator.get_throttle() and emulator.get_speed_factor() == 4)
        self._set_button_colour(self.unthrottled_button, not emulator.get_throttle())

        self._set_button_colour(self.toggle_video_button, emulator.get_video_enabled())
        self._set_button_colour(
            self.toggle_audio_button,
            active_condition=emulator.get_audio_enabled(),
            disabled_condition=not emulator.get_throttle(),
        )

    def set_message(self, message: str):
        if self.frame:
            self.bot_message.config(text=message)

    def on_frame_render(self):
        if config["general"]["bot_mode"] != self.last_known_bot_mode:
            self.last_known_bot_mode = config["general"]["bot_mode"]
            self.update()

    def _add_bot_mode_controls(self, row: int, column: int):
        group = tkinter.Frame(self.frame)
        group.grid(row=row, column=column, sticky="W")

        tkinter.Label(group, text="Bot Mode:", justify="left").grid(row=0, sticky="W")
        self.bot_mode_combobox = ttk.Combobox(group, values=available_bot_modes, width=20, state="readonly")
        self.bot_mode_combobox.bind(
            "<<ComboboxSelected>>", lambda e: self.gui.set_bot_mode(self.bot_mode_combobox.get())
        )
        self.bot_mode_combobox.bind("<FocusIn>", lambda e: self.window.focus())
        self.bot_mode_combobox.grid(row=1, sticky="W")

    def _add_speed_controls(self, row: int, column: int, sticky: str = "W"):
        group = tkinter.Frame(self.frame)
        group.grid(row=row, column=column, sticky=sticky)

        tkinter.Label(group, text="Emulation Speed:", justify="left").grid(
            row=0, columnspan=5, sticky="W", pady=(10, 0)
        )

        self.speed_1x_button = tkinter.Button(
            group, text="1×", width=3, padx=0, command=lambda: self.gui.set_emulation_speed(1)
        )
        self.speed_2x_button = tkinter.Button(
            group, text="2×", width=3, padx=0, command=lambda: self.gui.set_emulation_speed(2)
        )
        self.speed_3x_button = tkinter.Button(
            group, text="3×", width=3, padx=0, command=lambda: self.gui.set_emulation_speed(3)
        )
        self.speed_4x_button = tkinter.Button(
            group, text="4×", width=3, padx=0, command=lambda: self.gui.set_emulation_speed(4)
        )
        self.unthrottled_button = tkinter.Button(
            group, text="∞", width=3, padx=0, command=lambda: self.gui.set_emulation_speed(0)
        )

        self.default_button_background = self.speed_1x_button.cget("background")
        self.default_button_foreground = self.speed_1x_button.cget("foreground")

        self.speed_1x_button.grid(row=1, column=0)
        self.speed_2x_button.grid(row=1, column=1)
        self.speed_3x_button.grid(row=1, column=2)
        self.speed_4x_button.grid(row=1, column=3)
        self.unthrottled_button.grid(row=1, column=4)

    def _add_settings_controls(self, row: int, column: int):
        group = tkinter.Frame(self.frame)
        group.grid(row=row, column=column, sticky="W")

        tkinter.Label(group, text="Other Settings:").grid(row=0, columnspan=2, sticky="W", pady=(10, 0))

        self.toggle_video_button = tkinter.Button(group, text="Video", width=6, padx=0, command=self.gui.toggle_video)
        self.toggle_audio_button = tkinter.Button(group, text="Audio", width=6, padx=0, command=self.gui.toggle_audio)

        self.toggle_video_button.grid(row=1, column=0)
        self.toggle_audio_button.grid(row=1, column=1)

    def _add_message_area(self, row: int, column: int, columnspan: int = 1):
        group = tkinter.LabelFrame(self.frame, text="Message:", padx=5, pady=0)
        group.grid(row=row, column=column, columnspan=columnspan, sticky="NSWE", pady=10)

        self.bot_message = tkinter.Label(group, wraplength=self.get_additional_width() - 45, justify="left", height=2)
        self.bot_message.grid(row=0, sticky="NW")

    def _add_version_notice(self, row: int, column: int, columnspan: int = 1):
        tkinter.Label(
            self.frame,
            text=f"{profile.rom.game_name} - {pokebot_name} {pokebot_version}",
            foreground="grey",
            font=tkinter.font.Font(size=9),
        ).grid(row=row, column=column, columnspan=columnspan, sticky="E")

    def _set_button_colour(
        self, button: tkinter.Button, active_condition: bool, disabled_condition: bool = False
    ) -> None:
        if disabled_condition:
            button.config(
                background=self.default_button_background, foreground=self.default_button_foreground, state="disabled"
            )
        elif active_condition:
            button.config(background="green", foreground="white", state="normal")
        else:
            button.config(
                background=self.default_button_background, foreground=self.default_button_foreground, state="normal"
            )


class DebugTab:
    def draw(self, root: ttk.Notebook):
        pass

    def update(self, emulator: LibmgbaEmulator):
        pass


class DebugEmulatorControls(EmulatorControls):
    debug_frame: Union[tkinter.Frame, None] = None
    debug_notebook: ttk.Notebook
    debug_tabs: list[DebugTab] = []

    def get_additional_width(self):
        return 480

    def add_to_window(self):
        self.window.columnconfigure(0, weight=0)
        self.window.columnconfigure(1, weight=1)

        self.debug_frame = tkinter.Frame(self.window, padx=10, pady=5)
        self.debug_frame.rowconfigure(0, weight=1)
        self.debug_frame.columnconfigure(0, weight=1)
        self.debug_frame.grid(row=0, column=1, rowspan=2, sticky="NWES")

        self.debug_notebook = ttk.Notebook(self.debug_frame)
        for tab in self.debug_tabs:
            tab.draw(self.debug_notebook)
        self.debug_notebook.grid(sticky="NWES")
        self.debug_notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        super().add_to_window()

    def add_tab(self, tab: DebugTab):
        self.debug_tabs.append(tab)
        if self.debug_frame is not None:
            tab.draw(self.debug_notebook)

    def on_frame_render(self):
        super().on_frame_render()
        index = self.debug_notebook.index("current")
        self.debug_tabs[index].update(emulator)

    def on_tab_change(self, event):
        index = self.debug_notebook.index("current")
        self.debug_tabs[index].update(emulator)

    def remove_from_window(self):
        super().remove_from_window()

        if self.debug_frame:
            self.debug_frame.destroy()
        self.debug_frame = None


class PokebotGui:
    window: tkinter.Tk = None
    frame: tkinter.Widget = None
    canvas: tkinter.Canvas = None
    canvas_current_image: tkinter.PhotoImage
    gba_keys: dict[str, int] = {}
    emulator_keys: dict[str, str] = {}
    width: int = 240
    height: int = 160
    scale: int = 1
    center_of_canvas: tuple[int, int] = (0, 0)
    previous_bot_mode: str = ""

    stepping_mode: bool = False
    stepping_button: tkinter.Button
    current_step: int = 0

    _load_save_window: Union[tkinter.Tk, None] = None

    def __init__(self, main_loop: callable, on_exit: callable):
        global gui
        gui = self

        self.window = tkinter.Tk()
        self.window.title(f"{pokebot_name} {pokebot_version}")
        self.window.geometry("480x320")
        self.window.resizable(False, False)
        self.window.protocol("WM_DELETE_WINDOW", self.close_window)
        self.window.bind("<KeyPress>", self.handle_key_down_event)
        self.window.bind("<KeyRelease>", self.handle_key_up_event)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        key_config = load_config("keys.yml", keys_schema)
        for key in input_map:
            self.gba_keys[key_config["gba"][key].lower()] = input_map[key]
        for action in key_config["emulator"]:
            self.emulator_keys[key_config["emulator"][action].lower()] = action

        self.main_loop = main_loop
        self.on_exit = on_exit

        self.controls = EmulatorControls(self, self.window)

        # This forces the app icon to be used in the task bar on Windows
        if platform.system() == "Windows":
            try:
                from win32com.shell import shell

                shell.SetCurrentProcessExplicitAppUserModelID("40cakes.pokebot-gen3")
            except ImportError:
                pass

        self.set_sprite_as_app_icon(self.choose_random_sprite())

    def __del__(self):
        self.window.destroy()

    def run(self, preselected_profile: Profile = None):
        if preselected_profile is not None:
            self.run_profile(preselected_profile)
        else:
            self.show_profile_selection()

        self.window.mainloop()

    def choose_random_sprite(self):
        rand = random.randint(0, 99)
        match rand:
            case _ if rand < 10:
                icon_dir = Path(__file__).parent.parent / "sprites" / "pokemon" / "shiny"
            case _ if rand < 99:
                icon_dir = Path(__file__).parent.parent / "sprites" / "pokemon" / "normal"
            case _:
                icon_dir = Path(__file__).parent.parent / "sprites" / "pokemon" / "anti-shiny"

        files = [x for x in icon_dir.glob("*.png") if x.is_file()]

        return random.choice(files)

    def set_sprite_as_app_icon(self, path: Path):
        image: PIL.Image = PIL.Image.open(path)
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        bbox = list(image.getbbox())
        bbox_width = bbox[2] - bbox[0]
        bbox_height = bbox[3] - bbox[1]

        # Make sure the image is sqare (width == height)
        if bbox_width - bbox_height:
            # Wider than high
            missing_height = bbox_width - bbox_height
            bbox[1] -= missing_height // 2
            bbox[3] += missing_height // 2 + (missing_height % 2)
        else:
            # Higher than wide (or equal sizes)
            missing_width = bbox_height - bbox_width
            bbox[0] -= missing_width // 2
            bbox[2] += missing_width // 2 + (missing_width % 2)

        # Make sure we didn't move the bounding box out of scope
        if bbox[0] < 0:
            bbox[2] -= bbox[0]
            bbox[0] = 0
        if bbox[1] < 0:
            bbox[3] -= bbox[1]
            bbox[1] = 0
        if bbox[2] > image.width:
            bbox[0] -= bbox[2] - image.width
            bbox[2] = image.width
        if bbox[3] > image.height:
            bbox[1] -= bbox[3] - image.height
            bbox[3] = image.height

        cropped_image = image.crop(bbox)
        icon = PIL.ImageTk.PhotoImage(cropped_image)
        self.window.iconphoto(False, icon)

    def close_window(self) -> None:
        """
        This is called when the user tries to close the emulator window using the 'X' button,
        or presses the End key.

        This function might be called from a different thread, in which case calling `sys.exit()`
        would not actually terminate the bot and thus the atexit handlers would not be called.

        As a lazy workaround, this function calls the shutdown callbacks directly and then calls
        `os._exit()` which will definitely terminate the process.
        """
        if emulator:
            emulator.shutdown()

        self.on_exit()

        os._exit(0)

    def set_message(self, message) -> None:
        self.controls.set_message(message)

    def set_emulation_speed(self, new_speed: float) -> None:
        if new_speed == 0:
            emulator.set_throttle(False)
        else:
            emulator.set_throttle(True)
            emulator.set_speed_factor(new_speed)

        self.controls.update()

    def toggle_audio(self) -> None:
        emulator.set_audio_enabled(not emulator.get_audio_enabled())
        self.controls.update()

    def toggle_video(self) -> None:
        emulator.set_video_enabled(not emulator.get_video_enabled())
        self.controls.update()
        if not emulator.get_video_enabled():
            self.set_placeholder_image()

    def set_placeholder_image(self) -> None:
        # Create a fancy placeholder image.
        placeholder = PIL.Image.new(mode="RGBA", size=(self.width * self.scale, self.height * self.scale))
        draw = PIL.ImageDraw.Draw(placeholder)

        # Black background
        draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill="#000000FF")

        # Paste a random sprite on top
        sprite = PIL.Image.open(self.choose_random_sprite())
        if sprite.mode != "RGBA":
            sprite = sprite.convert("RGBA")
        sprite_position = (placeholder.width // 2 - sprite.width // 2, placeholder.height // 2 - sprite.height // 2)
        placeholder.paste(sprite, sprite_position, sprite)

        self.canvas_current_image = PIL.ImageTk.PhotoImage(placeholder)
        self.canvas.create_image(self.center_of_canvas, image=self.canvas_current_image, state="normal")

    def set_bot_mode(self, new_bot_mode: str) -> None:
        set_bot_mode(new_bot_mode)
        self.controls.update()

    def toggle_stepping_mode(self) -> None:
        self.stepping_mode = not self.stepping_mode
        if self.stepping_mode:

            def next_step():
                self.current_step += 1

            self.stepping_button = tkinter.Button(
                self.window, text="⮞", padx=8, background="red", foreground="white", command=next_step
            )
            self.stepping_button.place(x=0, y=0)
            self.current_step = 0
        else:
            self.stepping_button.destroy()

    def handle_key_down_event(self, event) -> str:
        keysym_with_modifier = ("ctrl+" if event.state & 4 else "") + event.keysym.lower()

        # This is checked here so that the key binding also works when the emulator is not running,
        # i.e. during the profile selection/creation screens.
        if keysym_with_modifier in self.emulator_keys and self.emulator_keys[keysym_with_modifier] == "exit":
            self.close_window()

        # These key bindings will only be applied if the emulation has started.
        if emulator:
            if keysym_with_modifier in self.gba_keys and (config["general"]["bot_mode"] == "manual"):
                emulator.hold_button(inputs=self.gba_keys[keysym_with_modifier])
            elif keysym_with_modifier in self.emulator_keys:
                match self.emulator_keys[keysym_with_modifier]:
                    case "reset":
                        emulator.reset()
                    case "save_state":
                        emulator.create_save_state("manual")
                    case "load_state":
                        self._show_load_save_screen()
                    case "toggle_stepping_mode":
                        self.toggle_stepping_mode()
                    case "zoom_in":
                        self.set_scale(min(5, self.scale + 1))
                        self.set_placeholder_image()
                    case "zoom_out":
                        self.set_scale(max(1, self.scale - 1))
                        self.set_placeholder_image()
                    case "toggle_manual":
                        toggle_manual_mode()
                        console.print(f'Now in [cyan]{config["general"]["bot_mode"]}[/] mode')
                        emulator.set_inputs(0)
                        self.controls.update()
                    case "toggle_video":
                        self.toggle_video()
                    case "toggle_audio":
                        self.toggle_audio()
                    case "set_speed_1x":
                        self.set_emulation_speed(1)
                    case "set_speed_2x":
                        self.set_emulation_speed(2)
                    case "set_speed_3x":
                        self.set_emulation_speed(3)
                    case "set_speed_4x":
                        self.set_emulation_speed(4)
                    case "set_speed_unthrottled":
                        self.set_emulation_speed(0)

        # This prevents the default action for that key to be executed, which is important for
        # the Tab key (which normally moves focus to the next GUI element.)
        return "break"

    def handle_key_up_event(self, event) -> None:
        keysym_with_modifier = ("ctrl+" if event.state & 4 else "") + event.keysym.lower()
        if emulator:
            if keysym_with_modifier in self.gba_keys and (config["general"]["bot_mode"] == "manual"):
                emulator.release_button(inputs=self.gba_keys[keysym_with_modifier])

    def _show_load_save_screen(self):
        if self._load_save_window is not None:
            self._load_save_window.focus_force()
            return

        state_directory = profile.path / "states"
        if not state_directory.is_dir():
            return

        state_files: list[Path] = [file for file in state_directory.glob("*.ss1")]
        if len(state_files) < 1:
            return

        def remove_window(event=None):
            self._load_save_window.destroy()
            self._load_save_window = None

        def load_state(state: Path):
            emulator.load_save_state(state.read_bytes())
            self._load_save_window.after(50, remove_window)

        self._load_save_window = tkinter.Tk()
        self._load_save_window.title("Load a Save State")
        self._load_save_window.geometry("520x500")
        self._load_save_window.protocol("WM_DELETE_WINDOW", remove_window)
        self._load_save_window.bind("<Escape>", remove_window)
        self._load_save_window.rowconfigure(0, weight=1)
        self._load_save_window.columnconfigure(0, weight=1)

        scrollable_frame = ttk.Frame(self._load_save_window)
        scrollable_frame.pack(fill=tkinter.BOTH, expand=True)

        canvas = tkinter.Canvas(scrollable_frame)
        canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(scrollable_frame, orient=tkinter.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        frame = ttk.Frame(canvas, width=500)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        canvas.create_window((0, 0), window=frame, anchor="nw")

        def filter_state_files(files: list[Path]):
            maximum_number_of_autosave_files = 3

            autosaves_already_included = 0
            autosave_pattern = re.compile("^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}\\.ss1$")
            files.sort(reverse=True, key=lambda file: file.stat().st_mtime)
            for file in files:
                if file.name == "current_state.ss1" or autosave_pattern.match(file.name):
                    if autosaves_already_included >= maximum_number_of_autosave_files:
                        continue
                    autosaves_already_included += 1
                yield file

        photo_buffer = []
        column = 0
        row = 0
        for state in filter_state_files(state_files):
            with open(state, "rb") as file:
                is_png = file.read(4) == b"\x89PNG"

            photo = None
            if is_png:
                try:
                    photo = tkinter.PhotoImage(master=canvas, file=state)
                except tkinter.TclError:
                    photo = None

            if photo is None:
                placeholder = PIL.Image.new(mode="RGBA", size=(self.width, self.height))
                draw = PIL.ImageDraw.Draw(placeholder)
                draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill="#000000FF")
                possible_sprites = [
                    "TM01.png",
                    "TM26.png",
                    "TM44.png",
                    "TM Dark.png",
                    "TM Dragon.png",
                    "TM Electric.png",
                    "TM Fire.png",
                    "TM Flying.png",
                    "TM Ghost.png",
                    "TM Grass.png",
                    "TM Ice.png",
                    "TM Normal.png",
                    "TM Poison.png",
                    "TM Rock.png",
                    "TM Steel.png",
                    "TM Water.png",
                ]
                sprite = PIL.Image.open(
                    Path(__file__).parent.parent / "sprites" / "items" / random.choice(possible_sprites)
                )
                if sprite.mode != "RGBA":
                    sprite = sprite.convert("RGBA")
                sprite = sprite.resize((sprite.width * 3, sprite.height * 3), resample=False)
                sprite_position = (
                    placeholder.width // 2 - sprite.width // 2,
                    placeholder.height // 2 - sprite.height // 2,
                )
                placeholder.paste(sprite, sprite_position, sprite)
                photo_buffer.append(placeholder)
                photo = PIL.ImageTk.PhotoImage(master=canvas, image=placeholder)

            photo_buffer.append(photo)
            button = tkinter.Button(
                frame,
                text=state.name,
                image=photo,
                compound=tkinter.TOP,
                padx=0,
                pady=0,
                wraplength=250,
                command=lambda s=state: load_state(s),
            )
            button.grid(row=int(row), column=column, sticky="NSWE")
            column = 1 if column == 0 else 0
            row += 0.5

        while self._load_save_window is not None:
            self._load_save_window.update_idletasks()
            self._load_save_window.update()
            time.sleep(1 / 60)

    def show_profile_selection(self):
        if self.frame:
            self.frame.destroy()

        available_profiles = list_available_profiles()
        if len(available_profiles) == 0:
            self.show_create_profile()
            return

        frame = ttk.Frame(self.window, padding=10, width=300)
        frame.grid()
        ttk.Label(frame, text="Select profile to run:").grid(column=0, row=0, sticky="W")
        tkinter.Button(
            frame, text="+ New profile", command=self.show_create_profile, fg="white", bg="green", cursor="hand2"
        ).grid(column=1, row=0, sticky="E")

        treeview = ttk.Treeview(
            frame, columns=("profile_name", "game", "last_played"), show="headings", height=10, selectmode="browse"
        )

        treeview.column("profile_name", width=150)
        treeview.heading("profile_name", text="Profile Name")
        treeview.column("game", width=160)
        treeview.heading("game", text="Game")
        treeview.column("last_played", width=150)
        treeview.heading("last_played", text="Last Played")

        available_profiles.sort(reverse=True, key=lambda p: p.last_played or datetime(1, 1, 1, 0, 0, 0))
        for profile in available_profiles:
            if profile.last_played:
                last_played = profile.last_played.strftime("%Y-%m-%d, %H:%M:%S")
            else:
                last_played = "never"

            data = (profile.path.name, profile.rom.game_name, last_played)
            treeview.insert("", tkinter.END, text=profile.path.name, values=data)

        def on_double_click(event):
            item = treeview.identify("item", event.x, event.y)
            selected_name = treeview.item(item, "text")
            for profile in available_profiles:
                if profile.path.name == selected_name:
                    self.run_profile(profile)
                    break

        treeview.bind("<Double-1>", on_double_click)
        treeview.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Label(frame, text="Double click a profile to launch it.").grid(row=2, column=0, columnspan=2)

        self.frame = frame

    def show_create_profile(self):
        if self.frame:
            self.frame.destroy()

        frame = ttk.Frame(self.window, padding=10, width=320)
        frame.grid()
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        available_roms = list_available_roms()
        if len(available_roms) == 0:
            error_message = 'No valid .gba ROMs detected in the "roms/" folder. Please add some and retry.'
            ttk.Label(frame, text=error_message, foreground="red", wraplength=300).grid(
                column=0, row=0, pady=20, padx=20, sticky="S"
            )
            ttk.Button(frame, text="Try again", command=self.show_create_profile, cursor="hand2").grid(
                column=0, row=1, pady=20, padx=20, sticky="N"
            )
            frame.grid_rowconfigure(1, weight=1)
            self.frame = frame
            return

        if len(list_available_profiles()) > 0:
            tkinter.Button(frame, text="Back", command=self.show_profile_selection, cursor="hand2").grid(
                column=0, row=0, sticky="E"
            )
        else:
            welcome_message = (
                f"Hey! This seems to be your first launch of {pokebot_name}, "
                "to get started you first need to create a profile.\n\n"
                "A profile stores your save game, save states, bot config, "
                'bot statistics, screenshots etc. Profiles are stored in the "profiles/" folder.\n'
            )
            ttk.Label(frame, text=welcome_message, wraplength=450, justify="left").grid(column=0, row=0, columnspan=2)

        group = ttk.LabelFrame(frame, text="Create a new profile", padding=10)
        group.grid()

        ttk.Label(group, text="Name:").grid(column=0, row=0, sticky="W", padx=5)

        button = None
        message_label = None
        sv_name = tkinter.StringVar()
        name_check = re.compile("^[-_a-zA-Z0-9 ]+$")

        def handle_name_input_change(name, index, mode, sv=sv_name):
            value = sv.get()
            if value == "":
                button.config(state="disabled")
                message_label.config(text="")
            elif not name_check.match(value):
                button.config(state="disabled")
                message_label.config(
                    text=(
                        "The profile name can only contain alphanumerical characters (Aa-Zz, 0-9), "
                        "underscores and hyphens."
                    ),
                    foreground="red",
                )
            elif profile_directory_exists(value):
                button.config(state="disabled")
                message_label.config(text=f'A profile named "{value}" already exists.', foreground="red")
            else:
                button.config(state="normal")
                message_label.config(text="")

        sv_name.trace("w", handle_name_input_change)
        entry = ttk.Entry(group, textvariable=sv_name)
        entry.grid(column=1, row=0, sticky="ew")

        rom_names = []
        for rom in available_roms:
            rom_names.append(rom.game_name)

        ttk.Label(group, text="Game:").grid(column=0, row=1, sticky="W", padx=5)
        rom_input = ttk.Combobox(group, values=sorted(rom_names), width=28, state="readonly")
        rom_input.current(0)
        rom_input.grid(column=1, row=1, pady=5)

        def handle_button_press():
            name = sv_name.get()
            rom_name = rom_input.get()
            for rom in available_roms:
                if rom.game_name == rom_name:
                    self.run_profile(create_profile(name, rom))

        button = ttk.Button(group, text="Create", cursor="hand2", state="disabled", command=handle_button_press)
        button.grid(column=0, columnspan=2, row=2, pady=10)

        message_label = ttk.Label(frame, text="", wraplength=480)
        message_label.grid(column=0, row=2, pady=10)

        self.frame = frame

    def run_profile(self, profile_to_run: Profile):
        if self.frame:
            self.frame.destroy()

        global emulator, profile
        profile = profile_to_run
        emulator = LibmgbaEmulator(profile, self.handle_frame)
        modules.game.set_rom(profile.rom)

        dimensions = emulator.get_image_dimensions()
        self.width = dimensions[0]
        self.height = dimensions[1]

        self.window.title(profile.rom.game_name)
        self.canvas = tkinter.Canvas(self.window, width=self.window.winfo_width(), height=self.window.winfo_height())
        self.canvas.grid(sticky="NW")
        self.set_scale(2)

        self.main_loop(profile)

    def set_scale(self, scale: int) -> None:
        self.scale = scale
        if scale > 1:
            self.window.geometry(
                "%dx%d"
                % (
                    self.width * self.scale + self.controls.get_additional_width(),
                    self.height * self.scale + self.controls.get_additional_height(),
                )
            )
        else:
            self.window.geometry(f"{self.width}x{self.height}")
        self.canvas.config(width=self.width * self.scale, height=self.height * self.scale)
        self.center_of_canvas = (self.scale * self.width // 2, self.scale * self.height // 2)

        self.controls.remove_from_window()
        if scale > 1:
            self.controls.add_to_window()

    def handle_frame(self) -> None:
        if emulator._performance_tracker.time_since_last_render() >= (1 / 60) * 1_000_000_000:
            if emulator.get_video_enabled():
                self.update_image(emulator.get_current_screen_image())
            else:
                self.update_window()
            emulator._performance_tracker.track_render()

        previous_step = self.current_step
        while self.stepping_mode and previous_step == self.current_step:
            self.window.update_idletasks()
            self.window.update()
            time.sleep(1 / 60)

    def update_image(self, image: PIL.Image) -> None:
        if not self.window:
            return

        self.canvas_current_image = PIL.ImageTk.PhotoImage(
            image=image.resize((self.width * self.scale, self.height * self.scale), resample=False)
        )
        self.canvas.create_image(self.center_of_canvas, image=self.canvas_current_image, state="normal")

        self.update_window()

    def update_window(self):
        from modules.stats import get_encounter_rate

        if self.scale > 1:
            self.controls.on_frame_render()

        current_fps = emulator.get_current_fps()
        current_load = emulator.get_current_time_spent_in_bot_fraction()
        if current_fps:
            self.window.title(
                f"{profile.path.name} | {get_encounter_rate():,}/h | {current_fps:,}fps "
                f"({current_fps / 60:0.2f}x) | {round(current_load * 100, 1)}% | {profile.rom.game_name}"
            )

        self.window.update_idletasks()
        self.window.update()
