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

import modules.Game
from modules.Config import available_bot_modes, config, LoadConfig, keys_schema, SetBotMode, ToggleManualMode
from modules.Console import console
from modules.LibmgbaEmulator import LibmgbaEmulator, input_map
from modules.Profiles import Profile, ListAvailableProfiles, ProfileDirectoryExists, CreateProfile
from modules.Roms import ROM, ListAvailableRoms
from version import pokebot_name, pokebot_version


gui: 'PokebotGui' = None
emulator: LibmgbaEmulator = None
profile: Profile = None


def SetMessage(message: str) -> None:
    if gui is not None:
        gui.SetMessage(message)


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
        if parent_process_name == 'py.exe' and gui is not None:
            gui.window.withdraw()
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
        self.last_known_bot_mode = config['general']['bot_mode']

    def GetAdditionalWidth(self):
        return 0

    def GetAdditionalHeight(self):
        return 165

    def AddToWindow(self):
        self.frame = tkinter.Frame(self.window, padx=5, pady=5)
        self.frame.grid(row=1, sticky='WE')
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self._AddBotModeControls(row=0, column=0)
        self._AddSpeedControls(row=0, column=1, sticky='N')
        self._AddSettingsControls(row=0, column=2)

        self._AddMessageArea(row=1, column=0, columnspan=3)
        self._AddVersionNotice(row=2, column=0, columnspan=3)

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
            self.last_known_bot_mode = config['general']['bot_mode']

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

    def OnFrameRender(self):
        if config['general']['bot_mode'] != self.last_known_bot_mode:
            self.last_known_bot_mode = config['general']['bot_mode']
            self.Update()

    def _AddBotModeControls(self, row: int, column: int):
        group = tkinter.Frame(self.frame)
        group.grid(row=row, column=column, sticky='W')

        tkinter.Label(group, text='Bot Mode:', justify='left').grid(row=0, sticky='W')
        self.bot_mode_combobox = ttk.Combobox(group, values=available_bot_modes, width=20, state='readonly')
        self.bot_mode_combobox.bind('<<ComboboxSelected>>',
                                    lambda e: self.gui.SetBotMode(self.bot_mode_combobox.get()))
        self.bot_mode_combobox.bind('<FocusIn>', lambda e: self.window.focus())
        self.bot_mode_combobox.grid(row=1, sticky='W')

    def _AddSpeedControls(self, row: int, column: int, sticky: str = 'W'):
        group = tkinter.Frame(self.frame)
        group.grid(row=row, column=column, sticky=sticky)

        tkinter.Label(group, text='Emulation Speed:', justify='left').grid(row=0, columnspan=5, sticky='W',
                                                                           pady=(10, 0))

        self.speed_1x_button = tkinter.Button(group, text='1×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(1))
        self.speed_2x_button = tkinter.Button(group, text='2×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(2))
        self.speed_3x_button = tkinter.Button(group, text='3×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(3))
        self.speed_4x_button = tkinter.Button(group, text='4×', width=3, padx=0,
                                              command=lambda: self.gui.SetEmulationSpeed(4))
        self.unthrottled_button = tkinter.Button(group, text='∞', width=3, padx=0,
                                                 command=lambda: self.gui.SetEmulationSpeed(0))

        self.default_button_background = self.speed_1x_button.cget('background')
        self.default_button_foreground = self.speed_1x_button.cget('foreground')

        self.speed_1x_button.grid(row=1, column=0)
        self.speed_2x_button.grid(row=1, column=1)
        self.speed_3x_button.grid(row=1, column=2)
        self.speed_4x_button.grid(row=1, column=3)
        self.unthrottled_button.grid(row=1, column=4)

    def _AddSettingsControls(self, row: int, column: int):
        group = tkinter.Frame(self.frame)
        group.grid(row=row, column=column, sticky='W')

        tkinter.Label(group, text='Other Settings:').grid(row=0, columnspan=2, sticky='W', pady=(10, 0))

        self.toggle_video_button = tkinter.Button(group, text='Video', width=6, padx=0,
                                                  command=self.gui.ToggleVideo)
        self.toggle_audio_button = tkinter.Button(group, text='Audio', width=6, padx=0,
                                                  command=self.gui.ToggleAudio)

        self.toggle_video_button.grid(row=1, column=0)
        self.toggle_audio_button.grid(row=1, column=1)

    def _AddMessageArea(self, row: int, column: int, columnspan: int = 1):
        group = tkinter.LabelFrame(self.frame, text='Message:', padx=5, pady=0)
        group.grid(row=row, column=column, columnspan=columnspan, sticky='NSWE', pady=10)

        self.bot_message = tkinter.Label(group, wraplength=self.GetAdditionalWidth() - 45, justify='left', height=2)
        self.bot_message.grid(row=0, sticky='NW')

    def _AddVersionNotice(self, row: int, column: int, columnspan: int = 1):
        tkinter.Label(self.frame, text=f'{profile.rom.game_name} - {pokebot_name} {pokebot_version}', foreground='grey',
                      font=tkinter.font.Font(size=9)).grid(row=row, column=column, columnspan=columnspan, sticky='E')

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


class DebugTab:
    def Draw(self, root: ttk.Notebook):
        pass

    def Update(self, emulator: LibmgbaEmulator):
        pass


class DebugEmulatorControls(EmulatorControls):
    debug_frame: Union[tkinter.Frame, None] = None
    debug_notebook: ttk.Notebook
    debug_tabs: list[DebugTab] = []

    def GetAdditionalWidth(self):
        return 480

    def AddToWindow(self):
        self.window.columnconfigure(0, weight=0)
        self.window.columnconfigure(1, weight=1)

        self.debug_frame = tkinter.Frame(self.window, padx=10, pady=5)
        self.debug_frame.rowconfigure(0, weight=1)
        self.debug_frame.columnconfigure(0, weight=1)
        self.debug_frame.grid(row=0, column=1, rowspan=2, sticky='NWES')

        self.debug_notebook = ttk.Notebook(self.debug_frame)
        for tab in self.debug_tabs:
            tab.Draw(self.debug_notebook)
        self.debug_notebook.grid(sticky='NWES')
        self.debug_notebook.bind('<<NotebookTabChanged>>', self.OnTabChange)

        super().AddToWindow()

    def AddTab(self, tab: DebugTab):
        self.debug_tabs.append(tab)
        if self.debug_frame is not None:
            tab.Draw(self.debug_notebook)

    def OnFrameRender(self):
        super().OnFrameRender()
        index = self.debug_notebook.index('current')
        self.debug_tabs[index].Update(emulator)

    def OnTabChange(self, event):
        index = self.debug_notebook.index('current')
        self.debug_tabs[index].Update(emulator)

    def RemoveFromWindow(self):
        super().RemoveFromWindow()

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
    previous_bot_mode: str = ''

    stepping_mode: bool = False
    stepping_button: tkinter.Button
    current_step: int = 0

    _load_save_window: Union[tkinter.Tk, None] = None

    def __init__(self, main_loop: callable):
        global gui
        gui = self

        self.window = tkinter.Tk()
        self.window.title(f'{pokebot_name} {pokebot_version}')
        self.window.geometry('480x320')
        self.window.resizable(False, False)
        self.window.protocol('WM_DELETE_WINDOW', self.CloseWindow)
        self.window.bind('<KeyPress>', self.HandleKeyDownEvent)
        self.window.bind('<KeyRelease>', self.HandleKeyUpEvent)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        key_config = LoadConfig('keys.yml', keys_schema)
        for key in input_map:
            self.gba_keys[key_config['gba'][key].lower()] = input_map[key]
        for action in key_config['emulator']:
            self.emulator_keys[key_config['emulator'][action].lower()] = action

        self.main_loop = main_loop

        if platform.system() == 'Windows':
            atexit.register(PromptBeforeExit)

        self.controls = EmulatorControls(self, self.window)

        # This forces the app icon to be used in the task bar on Windows
        if platform.system() == 'Windows':
            try:
                from win32com.shell import shell
                shell.SetCurrentProcessExplicitAppUserModelID('40cakes.pokebot-gen3')
            except ImportError:
                pass

        self.SetSpriteAsAppIcon(self.ChooseRandomSprite())

    def __del__(self):
        self.window.destroy()

    def Run(self, preselected_profile: Profile = None):
        if preselected_profile is not None:
            self.RunProfile(preselected_profile)
        else:
            self.ShowProfileSelection()

        self.window.mainloop()

    def ChooseRandomSprite(self):
        rand = random.randint(0, 99)
        match rand:
            case _ if rand < 10:
                icon_dir = Path(__file__).parent.parent / 'sprites' / 'pokemon' / 'shiny'
            case _ if rand < 99:
                icon_dir = Path(__file__).parent.parent / 'sprites' / 'pokemon' / 'normal'
            case _:
                icon_dir = Path(__file__).parent.parent / 'sprites' / 'pokemon' / 'anti-shiny'

        files = [x for x in icon_dir.glob('*.png') if x.is_file()]

        return random.choice(files)

    def SetSpriteAsAppIcon(self, path: Path):
        image: PIL.Image = PIL.Image.open(path)
        if image.mode != 'RGBA':
            image = image.convert('RGBA')

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
        if not emulator.GetVideoEnabled():
            # Create a fancy placeholder image.
            placeholder = PIL.Image.new(mode='RGBA', size=(self.width * self.scale, self.height * self.scale))
            draw = PIL.ImageDraw.Draw(placeholder)

            # Black background
            draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill='#000000FF')

            # Paste a random sprite on top
            sprite = PIL.Image.open(self.ChooseRandomSprite())
            if sprite.mode != 'RGBA':
                sprite = sprite.convert('RGBA')
            sprite_position = (placeholder.width // 2 - sprite.width // 2, placeholder.height // 2 - sprite.height // 2)
            placeholder.paste(sprite, sprite_position, sprite)

            self.canvas_current_image = PIL.ImageTk.PhotoImage(placeholder)
            self.canvas.create_image(self.center_of_canvas, image=self.canvas_current_image, state='normal')

    def SetBotMode(self, new_bot_mode: str) -> None:
        SetBotMode(new_bot_mode)
        self.controls.Update()

    def ToggleSteppingMode(self) -> None:
        self.stepping_mode = not self.stepping_mode
        if self.stepping_mode:
            def NextStep():
                self.current_step += 1

            self.stepping_button = tkinter.Button(self.window, text='⮞', padx=8, background='red',
                                                  foreground='white', command=NextStep)
            self.stepping_button.place(x=0, y=0)
            self.current_step = 0
        else:
            self.stepping_button.destroy()

    def HandleKeyDownEvent(self, event) -> str:
        keysym_with_modifier = ('ctrl+' if event.state & 4 else '') + event.keysym.lower()

        # This is checked here so that the key binding also works when the emulator is not running,
        # i.e. during the profile selection/creation screens.
        if keysym_with_modifier in self.emulator_keys and self.emulator_keys[keysym_with_modifier] == 'exit':
            self.CloseWindow()

        # These key bindings will only be applied if the emulation has started.
        if emulator:
            if keysym_with_modifier in self.gba_keys and \
                    (config['general']['bot_mode'] == 'manual'):
                emulator.HoldButton(inputs=self.gba_keys[keysym_with_modifier])
            elif keysym_with_modifier in self.emulator_keys:
                match self.emulator_keys[keysym_with_modifier]:
                    case 'reset':
                        emulator.Reset()
                    case 'save_state':
                        emulator.CreateSaveState('manual')
                    case 'load_state':
                        self._ShowLoadSaveScreen()
                    case 'toggle_stepping_mode':
                        self.ToggleSteppingMode()
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
        keysym_with_modifier = ('ctrl+' if event.state & 4 else '') + event.keysym.lower()
        if emulator:
            if keysym_with_modifier in self.gba_keys and \
                    (config['general']['bot_mode'] == 'manual'):
                emulator.ReleaseButton(inputs=self.gba_keys[keysym_with_modifier])

    def _ShowLoadSaveScreen(self):
        if self._load_save_window is not None:
            self._load_save_window.focus_force()
            return

        state_directory = profile.path / 'states'
        if not state_directory.is_dir():
            return

        state_files: list[Path] = [file for file in state_directory.glob('*.ss1')]
        if len(state_files) < 1:
            return

        def RemoveWindow(event=None):
            self._load_save_window.destroy()
            self._load_save_window = None

        def LoadState(state: Path):
            emulator.LoadSaveState(state.read_bytes())
            self._load_save_window.after(50, RemoveWindow)

        self._load_save_window = tkinter.Tk()
        self._load_save_window.title('Load a Save State')
        self._load_save_window.geometry('520x500')
        self._load_save_window.protocol('WM_DELETE_WINDOW', RemoveWindow)
        self._load_save_window.bind('<Escape>', RemoveWindow)
        self._load_save_window.rowconfigure(0, weight=1)
        self._load_save_window.columnconfigure(0, weight=1)

        # Stole-, uh, I mean heavily inspired from:
        # https://stackoverflow.com/a/71682458/3163142
        scrollable_frame = ttk.Frame(self._load_save_window)
        scrollable_frame.pack(fill=tkinter.BOTH, expand=True)

        canvas = tkinter.Canvas(scrollable_frame)
        canvas.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(scrollable_frame, orient=tkinter.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        frame = ttk.Frame(canvas, width=500)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        canvas.create_window((0, 0), window=frame, anchor='nw')

        def FilterStateFiles(files: list[Path]):
            maximum_number_of_autosave_files = 3

            autosaves_already_included = 0
            autosave_pattern = re.compile('^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}\\.ss1$')
            files.sort(reverse=True, key=lambda file: file.stat().st_mtime)
            for file in files:
                if file.name == 'current_state.ss1' or autosave_pattern.match(file.name):
                    if autosaves_already_included >= maximum_number_of_autosave_files:
                        continue
                    autosaves_already_included += 1
                yield file

        photo_buffer = []
        column = 0
        row = 0
        for state in FilterStateFiles(state_files):
            with open(state, 'rb') as file:
                is_png = file.read(4) == b'\x89PNG'

            photo = None
            if is_png:
                try:
                    photo = tkinter.PhotoImage(master=canvas, file=state)
                except tkinter.TclError:
                    photo = None

            if photo is None:
                placeholder = PIL.Image.new(mode='RGBA', size=(self.width, self.height))
                draw = PIL.ImageDraw.Draw(placeholder)
                draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill='#000000FF')
                possible_sprites = ['TM01.png', 'TM26.png', 'TM44.png', 'TM Dark.png', 'TM Dragon.png',
                                    'TM Electric.png',
                                    'TM Fire.png', 'TM Flying.png', 'TM Ghost.png', 'TM Grass.png', 'TM Ice.png',
                                    'TM Normal.png', 'TM Poison.png', 'TM Rock.png', 'TM Steel.png', 'TM Water.png']
                sprite = PIL.Image.open(
                    Path(__file__).parent.parent / 'sprites' / 'items' / random.choice(possible_sprites))
                if sprite.mode != 'RGBA':
                    sprite = sprite.convert('RGBA')
                sprite = sprite.resize((sprite.width * 3, sprite.height * 3), resample=False)
                sprite_position = (
                    placeholder.width // 2 - sprite.width // 2, placeholder.height // 2 - sprite.height // 2)
                placeholder.paste(sprite, sprite_position, sprite)
                photo_buffer.append(placeholder)
                photo = PIL.ImageTk.PhotoImage(master=canvas, image=placeholder)

            photo_buffer.append(photo)
            button = tkinter.Button(frame, text=state.name, image=photo, compound=tkinter.TOP, padx=0, pady=0,
                                    wraplength=250, command=lambda s=state: LoadState(s))
            button.grid(row=int(row), column=column, sticky='NSWE')
            column = 1 if column == 0 else 0
            row += 0.5

        while self._load_save_window is not None:
            self._load_save_window.update_idletasks()
            self._load_save_window.update()
            time.sleep(1 / 60)

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
        frame.grid()
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
        emulator = LibmgbaEmulator(profile, self.HandleFrame)
        modules.Game.SetROM(profile.rom)

        dimensions = emulator.GetImageDimensions()
        self.width = dimensions[0]
        self.height = dimensions[1]

        self.window.title(profile.rom.game_name)
        self.canvas = tkinter.Canvas(self.window, width=self.window.winfo_width(), height=self.window.winfo_height())
        self.canvas.grid(sticky='NW')
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

    def HandleFrame(self) -> None:
        if emulator._performance_tracker.TimeSinceLastRender() >= (1 / 60) * 1_000_000_000:
            if emulator.GetVideoEnabled():
                self.UpdateImage(emulator.GetCurrentScreenImage())
            else:
                self.UpdateWindow()
            emulator._performance_tracker.TrackRender()

        previous_step = self.current_step
        while self.stepping_mode and previous_step == self.current_step:
            self.window.update_idletasks()
            self.window.update()
            time.sleep(1 / 60)

    def UpdateImage(self, image: PIL.Image) -> None:
        if not self.window:
            return

        self.canvas_current_image = PIL.ImageTk.PhotoImage(
            image=image.resize((self.width * self.scale, self.height * self.scale), resample=False))
        self.canvas.create_image(self.center_of_canvas, image=self.canvas_current_image, state='normal')

        self.UpdateWindow()

    def UpdateWindow(self):
        from modules.Stats import GetEncounterRate
        if self.scale > 1:
            self.controls.OnFrameRender()

        current_fps = emulator.GetCurrentFPS()
        current_load = emulator.GetCurrentTimeSpentInBotFraction()
        if current_fps:
            self.window.title(f'{profile.path.name} | {GetEncounterRate():,}/h | {current_fps:,}fps '
                              f'({current_fps / 60:0.2f}x) | {round(current_load * 100, 1)}% | {profile.rom.game_name}')

        self.window.update_idletasks()
        self.window.update()
