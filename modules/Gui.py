import os
import platform
import re
import tkinter
import tkinter.font
from datetime import datetime
from pathlib import Path
from tkinter import ttk
from typing import Union

import PIL.Image
import PIL.ImageTk

import modules.Game
from modules.Config import available_bot_modes, config, LoadConfig, keys_schema, SetBotMode, ToggleManualMode, \
    on_bot_mode_change_callbacks
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

gui: 'PokebotGui' = None
emulator: LibmgbaEmulator = None
profile: Profile = None


def GetGUI() -> 'PokebotGui':
    return gui


def GetEmulator() -> LibmgbaEmulator:
    return emulator


def GetProfile() -> Profile:
    return profile


def GetROM() -> ROM:
    if not profile:
        return None
    return profile.rom


# On Windows, the bot can be started by clicking this Python file. In that case, the terminal
# window is only open for as long as the bot runs, which would make it impossible to see error
# messages during a crash.
# For those cases, we register an `atexit` handler that will wait for user input before closing
# the terminal window.
if platform.system() == 'Windows':
    import atexit
    import psutil


    def PromptBeforeExit() -> None:
        parent_process_name = psutil.Process(os.getppid()).name()
        if parent_process_name == 'py.exe':
            input('Press Enter to close...')


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

    def __init__(self, gui: 'PokebotGui', window: tkinter.Tk):
        self.gui = gui
        self.window = window
        on_bot_mode_change_callbacks.append(lambda n: self.Update())

    def GetAdditionalWidth(self):
        return 200

    def GetAdditionalHeight(self):
        return 0

    def AddToWindow(self):
        self.frame = tkinter.Frame(self.window, padx=10, pady=5)
        self.frame.pack(side='right', fill='both', expand=True)
        self.frame.columnconfigure(0, weight=1)

        self._AddBotModeControls(0)
        self._AddSpeedControls(2)
        self._AddSettingsControls(4)
        self._AddMessageArea(6)
        self._AddVersionNotice(8)

        self.Update()

    def RemoveFromWindow(self):
        if self.frame:
            self.frame.destroy()

        self.frame = None

    def Update(self):
        if self.frame is None:
            return

        # This avoids any other GUI element from having the focus. We don't want that because
        # for example if the bot mode combobox is focussed, pressing Down might open the
        # dropdown menu.
        self.window.focus()

        if self.bot_mode_combobox.get() != config['general']['bot_mode']:
            self.bot_mode_combobox.current(available_bot_modes.index(config['general']['bot_mode']))

        self._SetButtonColour(self.speed_1x_button, emulator.GetThrottle() and emulator.GetSpeedFactor() == 1)
        self._SetButtonColour(self.speed_2x_button, emulator.GetThrottle() and emulator.GetSpeedFactor() == 2)
        self._SetButtonColour(self.speed_3x_button, emulator.GetThrottle() and emulator.GetSpeedFactor() == 3)
        self._SetButtonColour(self.speed_4x_button, emulator.GetThrottle() and emulator.GetSpeedFactor() == 4)
        self._SetButtonColour(self.unthrottled_button, not emulator.GetThrottle())

        self._SetButtonColour(self.toggle_video_button, emulator.GetVideoEnabled())
        self._SetButtonColour(self.toggle_audio_button,
                              active_condition=emulator.GetAudioEnabled(),
                              disabled_condition=not emulator.GetThrottle())

    def SetMessage(self, message: str):
        if self.frame:
            self.bot_message.config(text=message)

    def _AddBotModeControls(self, row: int):
        ttk.Label(self.frame, text='Bot Mode:', justify='left').grid(row=row, sticky='W')
        self.bot_mode_combobox = ttk.Combobox(self.frame, values=available_bot_modes, width=20, state='readonly')
        self.bot_mode_combobox.bind('<<ComboboxSelected>>',
                                    lambda e: self.gui.SetBotMode(self.bot_mode_combobox.get()))
        self.bot_mode_combobox.grid(row=row + 1, sticky='W')

    def _AddSpeedControls(self, row: int):
        ttk.Label(self.frame, text='Emulation Speed:', justify='left').grid(row=row, sticky='W', pady=(15, 0))
        speed_button_group = ttk.Frame(self.frame)
        speed_button_group.grid(row=row + 1, sticky='W')

        self.speed_1x_button = tkinter.Button(speed_button_group, text='1×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(1))
        self.speed_2x_button = tkinter.Button(speed_button_group, text='2×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(2))
        self.speed_3x_button = tkinter.Button(speed_button_group, text='3×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(3))
        self.speed_4x_button = tkinter.Button(speed_button_group, text='4×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(4))
        self.unthrottled_button = tkinter.Button(speed_button_group, text='∞', width=3, padx=0,
                                                 command=lambda: self.gui.SetEmulationSpeed(0))

        self.default_button_background = self.speed_1x_button.cget('background')
        self.default_button_foreground = self.speed_1x_button.cget('foreground')

        self.speed_1x_button.grid(row=0, column=0)
        self.speed_2x_button.grid(row=0, column=1)
        self.speed_3x_button.grid(row=0, column=2)
        self.speed_4x_button.grid(row=0, column=3)
        self.unthrottled_button.grid(row=0, column=4)

    def _AddSettingsControls(self, row: int):
        tkinter.Label(self.frame, text='Other Settings:').grid(row=row, sticky='W', pady=(15, 0))
        settings_group = tkinter.Frame(self.frame)
        settings_group.grid(row=row + 1, sticky='W')

        self.toggle_video_button = tkinter.Button(settings_group, text='Video', width=6, padx=0,
                                                  command=self.gui.ToggleVideo)
        self.toggle_audio_button = tkinter.Button(settings_group, text='Audio', width=6, padx=0,
                                                  command=self.gui.ToggleAudio)

        self.toggle_video_button.grid(row=0, column=0)
        self.toggle_audio_button.grid(row=0, column=1)

    def _AddMessageArea(self, row: int):
        self.frame.rowconfigure(row, weight=1)

        group = tkinter.LabelFrame(self.frame, text='Message:', padx=5, pady=0)
        group.grid(row=row, sticky='NSWE', pady=10)

        self.bot_message = tkinter.Label(group, wraplength=self.GetAdditionalWidth() - 45, justify='left')
        self.bot_message.grid(row=0, sticky='W')

    def _AddVersionNotice(self, row: int):
        tkinter.Label(self.frame, text=f'{pokebot_name} {pokebot_version}', foreground='grey',
                      font=tkinter.font.Font(size=9)).grid(row=row, sticky='E')

    def _SetButtonColour(self, button: tkinter.Button, active_condition: bool,
                         disabled_condition: bool = False) -> None:
        if disabled_condition:
            button.config(background=self.default_button_background, foreground=self.default_button_foreground,
                          state='disabled')
        elif active_condition:
            button.config(background='green', foreground='white', state='normal')
        else:
            button.config(background=self.default_button_background, foreground=self.default_button_foreground,
                          state='normal')


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
        global gui
        gui = self

        self.window = tkinter.Tk()
        self.window.title(f'{pokebot_name} {pokebot_version}')
        self.window.geometry('480x320')
        self.window.resizable(False, False)
        self.window.protocol('WM_DELETE_WINDOW', self.CloseWindow)
        self.window.bind('<KeyPress>', self.HandleKeyDownEvent)
        self.window.bind('<KeyRelease>', self.HandleKeyUpEvent)

        key_config = LoadConfig('keys.yml', keys_schema)
        for key in input_map:
            self.gba_keys[key_config['gba'][key]] = input_map[key]
        for action in key_config['emulator']:
            self.emulator_keys[key_config['emulator'][action].lower()] = action

        self.main_loop = main_loop

        if platform.system() == 'Windows':
            atexit.register(PromptBeforeExit)

        self.controls = EmulatorControls(self, self.window)

        if preselected_profile:
            self.RunProfile(preselected_profile)
        else:
            self.ShowProfileSelection()

        self.window.iconphoto(False,
                              tkinter.PhotoImage(file=str(Path(__file__).parent.parent / 'sprites' / 'app_icon.png')))

        self.window.mainloop()

    def __del__(self):
        self.window.destroy()

    def CloseWindow(self) -> None:
        """
        This is called when the user tries to close the emulator window using the 'X' button,
        or presses the End key.

        This function might be called from a different thread, in which case calling `sys.exit()`
        would not actually terminate the bot and thus the atexit handlers would not be called.

        As a lazy workaround, this function calls the shutdown callbacks directly and then calls
        `os._exit()` which will definitely terminate the process.
        """
        if emulator:
            emulator.Shutdown()

        if platform.system() == 'Windows':
            self.window.withdraw()
            PromptBeforeExit()

        os._exit(0)

    def SetMessage(self, message) -> None:
        self.controls.SetMessage(message)

    def SetEmulationSpeed(self, new_speed: float) -> None:
        if new_speed == 0:
            emulator.SetThrottle(False)
        else:
            emulator.SetThrottle(True)
            emulator.SetSpeedFactor(new_speed)

        self.controls.Update()

    def ToggleAudio(self) -> None:
        emulator.SetAudioEnabled(not emulator.GetAudioEnabled())
        self.controls.Update()

    def ToggleVideo(self) -> None:
        emulator.SetVideoEnabled(not emulator.GetVideoEnabled())
        self.controls.Update()

    def SetBotMode(self, new_bot_mode: str) -> None:
        SetBotMode(new_bot_mode)
        self.controls.Update()

    def HandleKeyDownEvent(self, event) -> str:
        keysym_with_modifier = ('ctrl+' if event.state & 4 else '') + event.keysym.lower()

        # This is checked here so that the key binding also works when the emulator is not running,
        # i.e. during the profile selection/creation screens.
        if keysym_with_modifier in self.emulator_keys and self.emulator_keys[keysym_with_modifier] == 'exit':
            self.CloseWindow()

        # These key bindings will only be applied if the emulation has started.
        if emulator:
            if event.keysym in self.gba_keys and \
                    (config['general']['bot_mode'] == 'manual' or 'debug_' in config['general']['bot_mode']):
                emulator.SetInputs(emulator.GetInputs() | self.gba_keys[event.keysym])
            elif keysym_with_modifier in self.emulator_keys:
                match self.emulator_keys[keysym_with_modifier]:
                    case 'reset':
                        emulator.Reset()
                    case 'zoom_in':
                        self.SetScale(min(5, self.scale + 1))
                    case 'zoom_out':
                        self.SetScale(max(1, self.scale - 1))
                    case 'toggle_manual':
                        ToggleManualMode()
                        console.print(f'Now in [cyan]{config["general"]["bot_mode"]}[/] mode')
                        emulator.SetInputs(0)
                        self.controls.Update()
                    case 'toggle_video':
                        self.ToggleVideo()
                    case 'toggle_audio':
                        self.ToggleAudio()
                    case 'set_speed_1x':
                        self.SetEmulationSpeed(1)
                    case 'set_speed_2x':
                        self.SetEmulationSpeed(2)
                    case 'set_speed_3x':
                        self.SetEmulationSpeed(3)
                    case 'set_speed_4x':
                        self.SetEmulationSpeed(4)
                    case 'set_speed_unthrottled':
                        self.SetEmulationSpeed(0)

        # This prevents the default action for that key to be executed, which is important for
        # the Tab key (which normally moves focus to the next GUI element.)
        return 'break'

    def HandleKeyUpEvent(self, event) -> None:
        if emulator:
            if event.keysym in self.gba_keys and \
                    (config['general']['bot_mode'] == 'manual' or 'debug_' in config['general']['bot_mode']):
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
        self.canvas.pack(side='left')
        self.SetScale(2)

        self.main_loop(profile)

    def SetScale(self, scale: int) -> None:
        self.scale = scale
        if scale > 1:
            self.window.geometry('%dx%d' % (
                self.width * self.scale + self.controls.GetAdditionalWidth(),
                self.height * self.scale + self.controls.GetAdditionalHeight()))
        else:
            self.window.geometry(f'{self.width}x{self.height}')
        self.canvas.config(width=self.width * self.scale, height=self.height * self.scale)
        self.center_of_canvas = (self.scale * self.width // 2, self.scale * self.height // 2)

        self.controls.RemoveFromWindow()
        if scale > 1:
            self.controls.AddToWindow()

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
            self.window.title(f'{profile.path.name} - {profile.rom.game_name} ({current_fps} fps / bot: '
                              f'{round(current_load * 100, 1)}%)')

        self.window.update_idletasks()
        self.window.update()
