import os
import platform
from tkinter import Tk, ttk
from typing import TYPE_CHECKING, Union

import PIL.Image
import PIL.ImageTk
import darkdetect

from modules.config import load_config, keys_schema, config
from modules.console import console
from modules.context import context
from modules.game import set_rom
from modules.gui.create_profile_screen import CreateProfileScreen
from modules.gui.emulator_screen import EmulatorScreen
from modules.gui.load_state_window import LoadStateWindow
from modules.gui.select_profile_screen import SelectProfileScreen
from modules.libmgba import LibmgbaEmulator, input_map
from modules.runtime import get_data_path
from modules.sprites import choose_random_sprite, crop_sprite_square
from modules.version import pokebot_name, pokebot_version

if TYPE_CHECKING:
    from modules.profiles import Profile


class PokebotGui:
    def __init__(self, main_loop: callable, on_exit: callable):
        self.window = Tk(className="PokeBot")
        self._current_screen = None
        self._main_loop = main_loop
        self._on_exit = on_exit

        self.window.protocol("WM_DELETE_WINDOW", self._close_window)
        self.window.bind("<KeyPress>", self._handle_key_down_event)
        self.window.bind("<KeyRelease>", self._handle_key_up_event)

        key_config = load_config("keys.yml", keys_schema)
        self._gba_keys: dict[str, int] = {}
        for key in input_map:
            self._gba_keys[key_config["gba"][key].lower()] = input_map[key]
        self._emulator_keys: dict[str, str] = {}
        for action in key_config["emulator"]:
            self._emulator_keys[key_config["emulator"][action].lower()] = action

        self.window.tk.call('source', str(get_data_path().parent / 'ttk-theme' / 'forest-light.tcl'))
        self.window.tk.call('source', str(get_data_path().parent / 'ttk-theme' / 'forest-dark.tcl'))

        theme_setting = config["general"]["colour_scheme"]
        if (darkdetect.isDark() and theme_setting != "light") or theme_setting == "dark":
            ttk.Style().theme_use('forest-dark')
        else:
            ttk.Style().theme_use('forest-light')

        self._create_profile_screen = CreateProfileScreen(self.window, self._enable_select_profile_screen,
                                                          self._run_profile)
        self._select_profile_screen = SelectProfileScreen(self.window, self._enable_create_profile_screen,
                                                          self._run_profile)
        self._emulator_screen = EmulatorScreen(self.window)
        self._set_app_icon()

    def run(self, preselected_profile: Union['Profile', None] = None) -> None:
        if preselected_profile is not None:
            self._run_profile(preselected_profile)
        else:
            self._enable_select_profile_screen()

        self.window.mainloop()

    def on_settings_updated(self) -> None:
        if self._current_screen == self._emulator_screen:
            self._emulator_screen.on_settings_updated()

    def _close_window(self) -> None:
        """
        This is called when the user tries to close the emulator window using the 'X' button,
        or presses the End key.

        This function might be called from a different thread, in which case calling `sys.exit()`
        would not actually terminate the bot and thus the atexit handlers would not be called.

        As a lazy workaround, this function calls the shutdown callbacks directly and then calls
        `os._exit()` which will definitely terminate the process.
        """
        if context.emulator:
            context.emulator.shutdown()
            context.emulator = None

        self._on_exit()

        os._exit(0)

    def _set_app_icon(self):
        # This forces the app icon to be used in the task bar on Windows
        if platform.system() == "Windows":
            try:
                from win32com.shell import shell

                shell.SetCurrentProcessExplicitAppUserModelID("40cakes.pokebot-gen3")
            except ImportError:
                pass

        sprite = crop_sprite_square(choose_random_sprite())
        self.icon = PIL.ImageTk.PhotoImage(sprite)
        self.window.iconphoto(False, self.icon)

    def _reset_screen(self) -> None:
        if self._current_screen is not None:
            self._current_screen.disable()
        self.window.title(f"{pokebot_name} {pokebot_version}")

    def _enable_create_profile_screen(self) -> None:
        self._reset_screen()
        self._create_profile_screen.enable()
        self._current_screen = self._create_profile_screen

    def _enable_select_profile_screen(self) -> None:
        self._reset_screen()
        self._select_profile_screen.enable()
        self._current_screen = self._select_profile_screen

    def _run_profile(self, profile: 'Profile') -> None:
        self._reset_screen()
        context.profile = profile
        set_rom(profile.rom)
        context.emulator = LibmgbaEmulator(profile, self._emulator_screen.update)
        self._emulator_screen.enable()
        self._current_screen = self._emulator_screen

        self._main_loop(profile)

    def _handle_key_down_event(self, event):
        keysym_with_modifier = ("ctrl+" if event.state & 4 else "") + event.keysym.lower()

        # This is checked here so that the key binding also works when the emulator is not running,
        # i.e. during the profile selection/creation screens.
        if keysym_with_modifier in self._emulator_keys and self._emulator_keys[keysym_with_modifier] == "exit":
            self._close_window()

        # These key bindings will only be applied if the emulation has started.
        if context.emulator:
            if keysym_with_modifier in self._gba_keys and context.bot_mode == "manual":
                context.emulator.hold_button(inputs=self._gba_keys[keysym_with_modifier])
            elif keysym_with_modifier in self._emulator_keys:
                match self._emulator_keys[keysym_with_modifier]:
                    case "reset":
                        context.emulator.reset()
                    case "save_state":
                        context.emulator.create_save_state("manual")
                    case "load_state":
                        LoadStateWindow(self.window)
                    case "toggle_stepping_mode":
                        self._emulator_screen.toggle_stepping_mode()
                    case "zoom_in":
                        self._emulator_screen.scale = min(5, self._emulator_screen.scale + 1)
                    case "zoom_out":
                        self._emulator_screen.scale = max(1, self._emulator_screen.scale - 1)
                    case "toggle_manual":
                        context.toggle_manual_mode()
                        console.print(f'Now in [cyan]{context.bot_mode}[/] mode')
                        context.emulator.set_inputs(0)
                    case "toggle_video":
                        context.toggle_video()
                    case "toggle_audio":
                        context.toggle_audio()
                    case "set_speed_1x":
                        context.emulation_speed = 1
                    case "set_speed_2x":
                        context.emulation_speed = 2
                    case "set_speed_3x":
                        context.emulation_speed = 3
                    case "set_speed_4x":
                        context.emulation_speed = 4
                    case "set_speed_unthrottled":
                        context.emulation_speed = 0

        # This prevents the default action for that key to be executed, which is important for
        # the Tab key (which normally moves focus to the next GUI element.)
        return "break"

    def _handle_key_up_event(self, event):
        keysym_with_modifier = ("ctrl+" if event.state & 4 else "") + event.keysym.lower()
        if context.emulator:
            if keysym_with_modifier in self._gba_keys and (context.bot_mode == "manual"):
                context.emulator.release_button(inputs=self._gba_keys[keysym_with_modifier])
