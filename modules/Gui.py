import re
import sys
import tkinter
from datetime import datetime
from tkinter import ttk

import PIL.Image
import PIL.ImageTk

import modules.Game
from modules.Config import config, LoadConfig, keys_schema, ToggleManualMode
from modules.Console import console
from modules.LibmgbaEmulator import LibmgbaEmulator
from modules.Profiles import Profile, ListAvailableProfiles, ProfileDirectoryExists, CreateProfile
from modules.Roms import ROM, ListAvailableRoms
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
    gba_keys: dict[str, int] = {}
    emulator_keys: dict[str, str] = {}
    width: int = 240
    height: int = 160
    scale: int = 1
    center_of_canvas: tuple[int, int] = (0, 0)
    previous_bot_mode: str = ''

    def __init__(self, main_loop: callable, preselected_profile: Profile = None):
        self.window = tkinter.Tk()
        self.window.title(f'{pokebot_name} {pokebot_version}')
        self.window.geometry('480x320')
        self.window.protocol('WM_DELETE_WINDOW', self.CloseWindow)
        self.window.bind('<KeyPress>', self.HandleKeyDownEvent)
        self.window.bind('<KeyRelease>', self.HandleKeyUpEvent)

        key_config = LoadConfig('keys.yml', keys_schema)
        for key in input_map:
            self.gba_keys[key_config['gba'][key]] = input_map[key]
        for action in key_config['emulator']:
            self.emulator_keys[key_config['emulator'][action]] = action

        self.main_loop = main_loop

        if preselected_profile:
            self.RunProfile(preselected_profile)
        else:
            self.ShowProfileSelection()

        self.window.mainloop()

    def __del__(self):
        self.window.destroy()

    def CloseWindow(self) -> None:
        """
        This is called when the user tries to close the emulator window using the 'X' button,
        or presses the End key.
        """
        if emulator:
            # This function might be called from a different thread, in which case calling `sys.exit()` does
            # not actually quit the bot.
            #
            # While calling `os._exit()` would work, that would prevent Python's exit handlers to be called --
            # one of which is responsible for storing the current emulator state to disk. Which we reaaally
            # want to happen.
            #
            # As a lazy workaround for this (until someone comes up with a better solution) we override the
            # emulator's per-frame method. So the next time it tries to emulate, it triggers the exit from the
            # main thread.
            setattr(emulator, 'RunSingleFrame', lambda: sys.exit())

        # Close/hide the window
        self.window.withdraw()

        sys.exit()

    def HandleKeyDownEvent(self, event) -> None:
        if emulator:
            if event.keysym in self.gba_keys and config['general']['bot_mode'] == 'manual':
                emulator.SetInputs(emulator.GetInputs() | self.gba_keys[event.keysym])
            elif event.keysym in self.emulator_keys:
                match self.emulator_keys[event.keysym]:
                    case 'reset':
                        emulator.Reset()
                    case 'exit':
                        self.CloseWindow()
                    case 'zoom_in':
                        self.SetScale(min(5, self.scale + 1))
                    case 'zoom_out':
                        self.SetScale(max(1, self.scale - 1))
                    case 'toggle_manual':
                        ToggleManualMode()
                        console.print(f'Now in [cyan]{config["general"]["bot_mode"]}[/] mode')
                        emulator.SetInputs(0)
                    case 'toggle_video':
                        emulator.SetVideoEnabled(not emulator.GetVideoEnabled())
                    case 'toggle_audio':
                        emulator.SetAudioEnabled(not emulator.GetAudioEnabled())
                    case 'set_speed_1x':
                        emulator.SetThrottle(True)
                        emulator.SetSpeedFactor(1)
                    case 'set_speed_2x':
                        emulator.SetThrottle(True)
                        emulator.SetSpeedFactor(2)
                    case 'set_speed_3x':
                        emulator.SetThrottle(True)
                        emulator.SetSpeedFactor(3)
                    case 'set_speed_4x':
                        emulator.SetThrottle(True)
                        emulator.SetSpeedFactor(4)
                    case 'set_speed_unthrottled':
                        emulator.SetThrottle(False)

    def HandleKeyUpEvent(self, event) -> None:
        if emulator:
            if event.keysym in self.gba_keys and config['general']['bot_mode'] == 'manual':
                emulator.SetInputs(emulator.GetInputs() & ~self.gba_keys[event.keysym])

    def ShowProfileSelection(self):
        if self.frame:
            self.frame.destroy()

        available_profiles = ListAvailableProfiles()
        if len(available_profiles) == 0:
            self.ShowCreateProfile()
            return

        frame = ttk.Frame(self.window, padding=10, width=300)
        frame.grid()
        ttk.Label(frame, text='Select profile to run:').grid(column=0, row=0, sticky='W')
        tkinter.Button(frame, text='+ New profile', command=self.ShowCreateProfile, fg='white',
                       bg='green', cursor='hand2').grid(column=1, row=0, sticky='E')

        treeview = ttk.Treeview(
            frame,
            columns=('profile_name', 'game', 'last_played'),
            show='headings',
            height=10,
            selectmode='browse'
        )

        treeview.column('profile_name', width=150)
        treeview.heading('profile_name', text='Profile Name')
        treeview.column('game', width=160)
        treeview.heading('game', text='Game')
        treeview.column('last_played', width=150)
        treeview.heading('last_played', text='Last Played')

        available_profiles.sort(reverse=True, key=lambda p: p.last_played or datetime(1, 1, 1, 0, 0, 0))
        for profile in available_profiles:
            if profile.last_played:
                last_played = profile.last_played.strftime('%Y-%m-%d, %H:%M:%S')
            else:
                last_played = 'never'

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

        ttk.Label(frame, text='Double click a profile to launch it.').grid(row=2, column=0, columnspan=2)

        self.frame = frame

    def ShowCreateProfile(self):
        if self.frame:
            self.frame.destroy()

        frame = ttk.Frame(self.window, padding=10, width=320)
        frame.pack(fill='both', expand=True)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        available_roms = ListAvailableRoms()
        if len(available_roms) == 0:
            error_message = 'No valid .gba ROMs detected in the "roms/" folder. Please add some and retry.'
            ttk.Label(frame, text=error_message, foreground='red', wraplength=300).grid(column=0, row=0, pady=20,
                                                                                        padx=20, sticky='S')
            ttk.Button(frame, text='Try again', command=self.ShowCreateProfile, cursor='hand2').grid(column=0, row=1,
                                                                                                     pady=20, padx=20,
                                                                                                     sticky='N')
            frame.grid_rowconfigure(1, weight=1)
            self.frame = frame
            return

        if len(ListAvailableProfiles()) > 0:
            tkinter.Button(frame, text='Back', command=self.ShowProfileSelection, cursor='hand2').grid(column=0, row=0,
                                                                                                       sticky='E')
        else:
            welcome_message = f'Hey! This seems to be your first launch of {pokebot_name}, ' \
                              'to get started you first need to create a profile.\n\n' \
                              'A profile stores your save game, save states, bot config, ' \
                              'bot statistics, screenshots etc. Profiles are stored in the "config/" folder.\n\n' \
                              'You can create and run as many profiles as your PC can handle, ' \
                              'simply launch another instance of the bot with a different profile.\n'
            ttk.Label(frame, text=welcome_message, wraplength=450, justify='left').grid(column=0, row=0, columnspan=2)

        group = ttk.LabelFrame(frame, text='Create a new profile', padding=10)
        group.grid()

        ttk.Label(group, text='Name:').grid(column=0, row=0, sticky='W', padx=5)

        button = None
        message_label = None
        sv_name = tkinter.StringVar()
        name_check = re.compile('^[-_a-zA-Z0-9 ]+$')

        def HandleNameInputChange(name, index, mode, sv=sv_name):
            value = sv.get()
            if value == '':
                button.config(state='disabled')
                message_label.config(text='')
            elif not name_check.match(value):
                button.config(state='disabled')
                message_label.config(text='The profile name can only contain alphanumerical characters (Aa-Zz, 0-9), '
                                          'underscores and hyphens.',
                                     foreground='red')
            elif ProfileDirectoryExists(value):
                button.config(state='disabled')
                message_label.config(text=f'A profile named "{value}" already exists.', foreground='red')
            else:
                button.config(state='normal')
                message_label.config(text='')

        sv_name.trace('w', HandleNameInputChange)
        entry = ttk.Entry(group, textvariable=sv_name)
        entry.grid(column=1, row=0, sticky='ew')

        rom_names = []
        for rom in available_roms:
            rom_names.append(rom.game_name)

        ttk.Label(group, text='Game:').grid(column=0, row=1, sticky='W', padx=5)
        rom_input = ttk.Combobox(group, values=sorted(rom_names), width=28, state='readonly')
        rom_input.current(0)
        rom_input.grid(column=1, row=1, pady=5)

        def HandleButtonPress():
            name = sv_name.get()
            rom_name = rom_input.get()
            for rom in available_roms:
                if rom.game_name == rom_name:
                    self.RunProfile(CreateProfile(name, rom))

        button = ttk.Button(group, text='Create', cursor='hand2', state='disabled', command=HandleButtonPress)
        button.grid(column=0, columnspan=2, row=2, pady=10)

        message_label = ttk.Label(frame, text='', wraplength=480)
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

        self.main_loop(profile)

    def SetScale(self, scale: int) -> None:
        self.scale = scale
        self.window.geometry(f'{self.width * self.scale}x{self.height * self.scale}')
        self.canvas.config(width=self.width * self.scale, height=self.height * self.scale)
        self.center_of_canvas = (self.scale * self.width // 2, self.scale * self.height // 2)

    def UpdateImage(self, image: PIL.Image) -> None:
        if not self.window:
            return

        photo_image = PIL.ImageTk.PhotoImage(
            image=image.resize((self.width * self.scale, self.height * self.scale), resample=False))
        self.canvas.create_image(self.center_of_canvas, image=photo_image, state='normal')

        self.UpdateWindow()

    def UpdateWindow(self):
        current_fps = emulator.GetCurrentFPS()
        current_load = emulator.GetCurrentTimeSpentInBotFraction()
        if current_fps:
            self.window.title(f'{pokebot_name} {pokebot_version} ({current_fps} fps / bot: '
                              f'{round(current_load * 100, 1)}%) | {profile.path.name} - {profile.rom.game_name}')

        self.window.update_idletasks()
        self.window.update()
