import re
import sys
import tkinter
from tkinter import ttk

import PIL.Image
import PIL.ImageTk

import modules.Game
from modules.Profiles import Profile, ListAvailableProfiles, ProfileDirectoryExists, CreateProfile
from modules.Roms import ROM, ListAvailableRoms
from modules.LibmgbaEmulator import LibmgbaEmulator
from version import pokebot_name, pokebot_version

input_map = {
    'A': 0x1,
    'B': 0x2,
    'Select': 0x4,
    'Start': 0x8,
    'Right': 0x10,
    'Left': 0x20,
    'Up': 0x40,
    'Down': 0x80,
    'R': 0x100,
    'L': 0x200
}

emulator: LibmgbaEmulator = None
profile: Profile = None


def GetEmulator() -> LibmgbaEmulator:
    return emulator


def GetProfile() -> Profile:
    return profile


def GetROM() -> ROM:
    if not profile:
        return None
    return profile.rom


class PokebotGui:
    window: tkinter.Tk = None
    frame: tkinter.Widget = None
    canvas: tkinter.Canvas = None
    width: int = 240
    height: int = 160
    scale: int = 1
    center_of_canvas: tuple[int, int] = (0, 0)
    is_running = True

    def __init__(self, main_loop: callable, preselected_profile: Profile = None):
        self.window = tkinter.Tk()
        self.window.title(pokebot_name + ' ' + pokebot_version)
        self.window.geometry('480x320')
        self.window.protocol('WM_DELETE_WINDOW', self.CloseWindow)
        self.window.bind('<KeyPress>', self.HandleKeyDownEvent)
        self.window.bind('<KeyRelease>', self.HandleKeyUpEvent)

        self.main_loop = main_loop

        if preselected_profile:
            self.RunProfile(preselected_profile)
        else:
            self.ShowProfileSelection()

        self.window.mainloop()

    def __del__(self):
        self.window.destroy()

    def CloseWindow(self) -> None:
        if emulator:
            setattr(emulator, "RunSingleFrame", lambda: sys.exit())
        sys.exit()

    def HandleKeyDownEvent(self, event) -> None:
        if event.keysym == 'Escape':
            self.CloseWindow()

        if emulator:
            match event.keysym:
                case 'Tab':
                    emulator.SetThrottle(not emulator.GetThrottle())

                case '1':
                    emulator.SetTargetSecondsPerFrame(1 / 60)

                case '2':
                    emulator.SetTargetSecondsPerFrame(1 / 120)

                case '3':
                    emulator.SetTargetSecondsPerFrame(1 / 180)

                case '4':
                    emulator.SetTargetSecondsPerFrame(1 / 240)

                case 'KP_Add':
                    self.SetScale(min(5, self.scale + 1))

                case 'KP_Subtract':
                    self.SetScale(max(1, self.scale - 1))

                case 'Up' | 'Down' | 'Left' | 'Right':
                    self._KeyDown(event.keysym)

                case 'z':
                    self._KeyDown('B')

                case 'x':
                    self._KeyDown('A')

                case 'a':
                    self._KeyDown('L')

                case 's':
                    self._KeyDown('R')

                case 'space':
                    self._KeyDown('Start')

                case 'Control_L':
                    self._KeyDown('Select')

    def HandleKeyUpEvent(self, event) -> None:
        if emulator:
            match event.keysym:
                case 'Up' | 'Down' | 'Left' | 'Right':
                    self._KeyUp(event.keysym)

                case 'z':
                    self._KeyUp('B')

                case 'x':
                    self._KeyUp('A')

                case 'a':
                    self._KeyUp('L')

                case 's':
                    self._KeyUp('R')

                case 'space':
                    self._KeyUp('Start')

                case 'Control_L':
                    self._KeyUp('Select')

    def _KeyDown(self, key: str) -> None:
        emulator.SetInputs(emulator.GetInputs() | input_map[key])

    def _KeyUp(self, key: str) -> None:
        emulator.SetInputs(emulator.GetInputs() & ~input_map[key])

    def ShowProfileSelection(self):
        if self.frame:
            self.frame.destroy()

        frame = ttk.Frame(self.window, padding=10, width=300)
        frame.grid()
        ttk.Label(frame, text="Select a game you would like to run:").grid(column=0, row=0, sticky="W")
        tkinter.Button(frame, text="+ Create new game config", command=self.ShowCreateProfile, fg='white',
                       bg='green', cursor="hand2").grid(column=1, row=0, sticky="E")

        treeview = ttk.Treeview(
            frame,
            columns=("profile_name", "game", "last_played"),
            show="headings",
            height=10,
            selectmode="browse"
        )

        treeview.column('profile_name', width=150)
        treeview.heading("profile_name", text="Profile Name")
        treeview.column('game', width=160)
        treeview.heading("game", text="Game")
        treeview.column('last_played', width=150)
        treeview.heading("last_played", text="Last Played")

        available_profiles = ListAvailableProfiles()
        available_profiles.sort(reverse=True, key=lambda p: p.last_played)
        for profile in available_profiles:
            if profile.last_played:
                last_played = profile.last_played.strftime("%Y-%m-%d, %H:%M:%S")
            else:
                last_played = "never"

            data = (profile.path.name, profile.rom.game_name, last_played)
            treeview.insert('', tkinter.END, text=profile.path.name, values=data)

        def OnDoubleClick(event):
            item = treeview.identify('item', event.x, event.y)
            selected_name = treeview.item(item, 'text')
            for profile in available_profiles:
                if profile.path.name == selected_name:
                    self.RunProfile(profile)
                    break

        treeview.bind('<Double-1>', OnDoubleClick)
        treeview.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Label(frame, text="(Double click a game to run it.)").grid(row=2, column=0, columnspan=2)

        self.frame = frame

    def ShowCreateProfile(self):
        if self.frame:
            self.frame.destroy()

        frame = ttk.Frame(self.window, padding=10)
        frame.grid(sticky="ew")

        available_roms = ListAvailableRoms()
        if len(available_roms) == 0:
            error_message = "There aren't any ROMs in the roms/ directory. Please put some in there."
            ttk.Label(frame, text=error_message, foreground="red", wraplength=300).grid(column=0, row=0, pady=20, padx=20)
            ttk.Button(frame, text="Try again", command=self.ShowCreateProfile).grid(column=0, row=1, pady=20, padx=20)
            self.frame = frame
            return

        tkinter.Button(frame, text="Back", command=self.ShowProfileSelection, cursor="hand2").grid(column=0, row=0, sticky="E")

        group = ttk.LabelFrame(frame, text="Create a new game config", padding=10)
        group.grid(sticky="W")

        ttk.Label(group, text="Name:").grid(column=0, row=0, sticky="W", padx=5)

        button = None
        message_label = None
        sv_name = tkinter.StringVar()
        name_check = re.compile('^[-_a-zA-Z0-9]+$')
        def HandleNameInputChange(name, index, mode, sv=sv_name):
            value = sv.get()
            if value == "":
                button.config(state="disabled")
                message_label.config(text="")
            elif not name_check.match(value):
                button.config(state="disabled")
                message_label.config(text="The profile name may only consist of letters, digits, underscore and hyphen.")
            elif ProfileDirectoryExists(value):
                button.config(state="disabled")
                message_label.config(text="A profile called '"+value+"' already exists.")
            else:
                button.config(state="normal")
                message_label.config(text="")

        sv_name.trace("w", HandleNameInputChange)
        entry = ttk.Entry(group, textvariable=sv_name)
        entry.grid(column=1, row=0, sticky="ew")

        rom_names = []
        for rom in available_roms:
            rom_names.append(rom.game_name)

        ttk.Label(group, text="Game:").grid(column=0, row=1, sticky="W", padx=5)
        rom_input = ttk.Combobox(group, values=sorted(rom_names), width=28, state="readonly")
        rom_input.current(0)
        rom_input.grid(column=1, row=1)

        def HandleButtonPress():
            name = sv_name.get()
            rom_name = rom_input.get()
            for rom in available_roms:
                if rom.game_name == rom_name:
                    self.RunProfile(CreateProfile(name, rom))

        button = ttk.Button(group, text="Create", cursor="hand2", state="disabled", command=HandleButtonPress)
        button.grid(column=1, row=2, sticky="W", pady=10)

        message_label = ttk.Label(frame, text="", wraplength=300, foreground="red")
        message_label.grid(column=0, row=2, pady=10)

        self.frame = frame

    def RunProfile(self, profile_to_run: Profile):
        if self.frame:
            self.frame.destroy()

        global emulator, profile
        profile = profile_to_run
        emulator = LibmgbaEmulator(profile, self)
        modules.Game.SetROM(profile.rom)

        dimensions = emulator.GetImageDimensions()
        self.width = dimensions[0]
        self.height = dimensions[1]

        self.window.title(profile.rom.game_name)
        self.canvas = tkinter.Canvas(self.window, width=self.window.winfo_width(), height=self.window.winfo_height(),
                                     bg='#000000')
        self.canvas.pack()
        self.SetScale(2)

        self.main_loop()

    def SetScale(self, scale: int) -> None:
        self.scale = scale
        self.window.geometry(f"{self.width * self.scale}x{self.height * self.scale}")
        self.canvas.config(width=self.width * self.scale, height=self.height * self.scale)
        self.center_of_canvas = (self.scale * self.width // 2, self.scale * self.height // 2)

    def UpdateImage(self, image: PIL.Image) -> None:
        if not self.window:
            return

        current_fps = emulator.GetCurrentFPS()
        if current_fps:
            self.window.title(f"{profile.rom.game_name} ({current_fps} fps)")

        photo_image = PIL.ImageTk.PhotoImage(
            image=image.resize((self.width * self.scale, self.height * self.scale), resample=False))
        self.canvas.create_image(self.center_of_canvas, image=photo_image, state="normal")

        self.window.update_idletasks()
        self.window.update()
