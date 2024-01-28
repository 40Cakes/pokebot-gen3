import tkinter.font
from tkinter import ttk
from ttkthemes import ThemedTk
from typing import Union

from modules.console import console
from modules.context import context
from modules.libmgba import LibmgbaEmulator
from modules.modes import get_bot_modes
from modules.memory import get_game_state, GameState
from modules.version import pokebot_name, pokebot_version


class EmulatorControls:
    def __init__(self, window: ThemedTk):
        self.window = window
        self.last_known_bot_mode = context.bot_mode

        self.frame: Union[ttk.Frame, None] = None
        self.bot_mode_button: ttk.Button
        self.bot_mode_menu: tkinter.Menu | None
        self.speed_1x_button: ttk.Button
        self.speed_2x_button: ttk.Button
        self.speed_3x_button: ttk.Button
        self.speed_4x_button: ttk.Button
        self.unthrottled_button: ttk.Button
        self.toggle_video_button: ttk.Button
        self.toggle_audio_button: ttk.Button
        self.bot_message: ttk.Label
        self.stats_label: ttk.Label

    def get_additional_width(self) -> int:
        return 0

    def get_additional_height(self) -> int:
        return 200

    def add_to_window(self) -> None:
        self.frame = ttk.Frame(self.window, padding=5)
        self.frame.grid(row=1, sticky="NSWE")
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self._add_bot_mode_controls(row=0, column=0)
        self._add_speed_controls(row=0, column=1, sticky="N")
        self._add_settings_controls(row=0, column=2)

        self._add_message_area(row=1, column=0, columnspan=3)
        self._add_stats_and_version_notice(row=2, column=0, columnspan=3)

        self.update()

    def remove_from_window(self) -> None:
        if self.frame:
            self.frame.destroy()

        self.frame = None

    def update(self) -> None:
        if self.frame is None:
            return

        self.bot_mode_button.config(text=context.bot_mode)
        self._set_button_colour(self.bot_mode_button, active_condition=context.bot_mode == "Manual")

        self._set_button_colour(self.speed_1x_button, active_condition=context.emulation_speed == 1)
        self._set_button_colour(self.speed_2x_button, active_condition=context.emulation_speed == 2)
        self._set_button_colour(self.speed_3x_button, active_condition=context.emulation_speed == 3)
        self._set_button_colour(self.speed_4x_button, active_condition=context.emulation_speed == 4)
        self._set_button_colour(self.unthrottled_button, active_condition=context.emulation_speed == 0)

        self._set_button_colour(self.toggle_video_button, active_condition=context.video)
        self._set_button_colour(
            self.toggle_audio_button, active_condition=context.audio, disabled_condition=context.emulation_speed == 0
        )

        self.bot_message.config(text=context.message)

    def on_frame_render(self):
        self._update_stats()
        if context.bot_mode != self.last_known_bot_mode:
            self.last_known_bot_mode = context.bot_mode
            self.update()

    def on_video_output_click(self, click_location: tuple[int, int], scale: int):
        pass

    def _add_bot_mode_controls(self, row: int, column: int):
        group = ttk.Frame(self.frame)
        group.grid(row=row, column=column, sticky="W")

        def select_bot_mode(mode: str):
            if mode == "Manual":
                context.set_manual_mode(enable_video_and_slow_down=False)
            else:
                context.bot_mode = mode
            if self.bot_mode_menu:
                self.bot_mode_menu.destroy()
                self.bot_mode_menu = None

        def open_bot_mode_menu():
            bold_font = tkinter.font.Font(self.window, weight="bold", size=10)

            self.bot_mode_menu = tkinter.Menu(self.window, tearoff=0)
            if context.bot_mode == "Manual":
                self.bot_mode_menu.add_command(label="Manual", font=bold_font)
            else:
                self.bot_mode_menu.add_command(label="Manual", command=lambda: select_bot_mode("Manual"))
            self.bot_mode_menu.add_separator()
            disabled_modes = []
            for mode in get_bot_modes():
                if mode.name() == context.bot_mode:
                    self.bot_mode_menu.add_command(label=mode.name(), font=bold_font)
                    continue

                if get_game_state() not in (GameState.TITLE_SCREEN, GameState.MAIN_MENU):
                    try:
                        is_selectable = mode.is_selectable()
                    except:
                        if context.debug:
                            console.print_exception()
                        is_selectable = False
                else:
                    is_selectable = False

                if is_selectable:
                    self.bot_mode_menu.add_command(label=mode.name(), command=lambda m=mode: select_bot_mode(m.name()))
                else:
                    disabled_modes.append(mode.name())
            if len(disabled_modes) > 0:
                if len(disabled_modes) < len(get_bot_modes()):
                    self.bot_mode_menu.add_separator()
                for mode_name in disabled_modes:
                    self.bot_mode_menu.add_command(label=mode_name, state="disabled")
            self.bot_mode_menu.tk_popup(
                self.bot_mode_button.winfo_rootx(),
                self.bot_mode_button.winfo_rooty() + self.bot_mode_button.winfo_height(),
            )

        ttk.Label(group, text="Bot Mode:", justify="left").grid(row=0, sticky="W")
        self.bot_mode_button = ttk.Button(
            group, text=context.bot_mode, width=20, padding=(0, 3), cursor="hand2", command=open_bot_mode_menu
        )
        self.bot_mode_button.grid(row=1, sticky="W", padx=0)

    def _add_speed_controls(self, row: int, column: int, sticky: str = "W"):
        group = ttk.Frame(self.frame)
        group.grid(row=row, column=column, sticky=sticky)

        ttk.Label(group, text="Emulation Speed:", justify="left").grid(row=0, columnspan=5, sticky="W")

        def set_emulation_speed(speed: int) -> None:
            context.emulation_speed = speed
            self.update()

        button_settings = {"width": 3, "padding": (0, 3), "cursor": "hand2"}
        self.speed_1x_button = ttk.Button(group, text="1×", **button_settings, command=lambda: set_emulation_speed(1))
        self.speed_2x_button = ttk.Button(group, text="2×", **button_settings, command=lambda: set_emulation_speed(2))
        self.speed_3x_button = ttk.Button(group, text="3×", **button_settings, command=lambda: set_emulation_speed(3))
        self.speed_4x_button = ttk.Button(group, text="4×", **button_settings, command=lambda: set_emulation_speed(4))
        self.unthrottled_button = ttk.Button(group, text="∞", **button_settings, command=lambda: set_emulation_speed(0))

        self.speed_1x_button.grid(row=1, column=0)
        self.speed_2x_button.grid(row=1, column=1)
        self.speed_3x_button.grid(row=1, column=2)
        self.speed_4x_button.grid(row=1, column=3)
        self.unthrottled_button.grid(row=1, column=4)

    def _add_settings_controls(self, row: int, column: int):
        group = ttk.Frame(self.frame)
        style = ttk.Style()
        style.map(
            "Accent.TButton",
            foreground=[("!active", "white"), ("active", "white"), ("pressed", "white")],
            background=[("!active", "purple1"), ("active", "purple3"), ("pressed", "purple1")],
        )
        group.grid(row=row, column=column, sticky="W")

        ttk.Label(group, text="Other Settings:").grid(row=0, columnspan=2, sticky="W")

        button_settings = {"width": 6, "padding": (0, 3), "cursor": "hand2"}
        self.toggle_video_button = ttk.Button(group, text="Video", **button_settings, command=context.toggle_video)
        self.toggle_audio_button = ttk.Button(group, text="Audio", **button_settings, command=context.toggle_audio)

        self.toggle_video_button.grid(row=1, column=0)
        self.toggle_audio_button.grid(row=1, column=1)

    def _add_message_area(self, row: int, column: int, columnspan: int = 1):
        group = ttk.LabelFrame(self.frame, text="Message:", padding=(10, 5))
        group.grid(row=row, column=column, columnspan=columnspan, sticky="NSWE", pady=10)

        self.bot_message = ttk.Label(group, wraplength=440, justify="left")
        self.bot_message.grid(row=0, sticky="NW")

    def _add_stats_and_version_notice(self, row: int, column: int, columnspan: int = 1):
        group = ttk.Frame(self.frame)
        group.columnconfigure(0, weight=1)
        group.grid(row=row, column=column, columnspan=columnspan, sticky="SWE")

        self.stats_label = ttk.Label(group, text="", foreground="grey", font=tkinter.font.Font(size=9))
        self.stats_label.grid(row=0, column=0, sticky="W")

        version_label = ttk.Label(
            group,
            text=f"{context.rom.short_game_name} - {pokebot_name} {pokebot_version}",
            foreground="grey",
            font=tkinter.font.Font(size=9),
        )
        version_label.grid(row=0, column=1, sticky="E")

    def _set_button_colour(self, button: ttk.Button, active_condition: bool, disabled_condition: bool = False) -> None:
        if disabled_condition:
            button.config(style="TButton", state="disabled")
        elif active_condition:
            button.config(style="Accent.TButton", state="normal")
        else:
            button.config(style="TButton", state="normal")

    def _update_stats(self):
        stats = []
        current_fps = context.emulator.get_current_fps()
        current_load = context.emulator.get_current_time_spent_in_bot_fraction()
        if current_fps:
            stats.append(f"{current_fps:,}fps ({current_fps / 59.73:0.2f}x)")
        if context.profile:
            from modules.stats import total_stats  # TODO prevent instantiating TotalStats class before profile selected

            stats.append(f"{total_stats.get_encounter_rate():,}/h")
        if context.debug:
            stats.append(f"{round(current_load * 100, 1)}%")
        self.stats_label.config(text=" | ".join(stats))


class DebugTab:
    def draw(self, root: ttk.Notebook):
        pass

    def update(self, emulator: "LibmgbaEmulator"):
        pass

    def on_video_output_click(self, click_location: tuple[int, int], scale: int):
        pass


class DebugEmulatorControls(EmulatorControls):
    def __init__(self, window: ThemedTk):
        super().__init__(window)
        self.debug_frame: Union[ttk.Frame, None] = None
        self.debug_notebook: ttk.Notebook
        self.debug_tabs: list[DebugTab] = []

    def get_additional_width(self) -> int:
        return 550

    def add_to_window(self):
        self.debug_frame = ttk.Frame(self.window, padding=(10, 5))
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
        self.debug_tabs[index].update(context.emulator)

    def on_video_output_click(self, click_location: tuple[int, int], scale: int):
        super().on_video_output_click(click_location, scale)
        index = self.debug_notebook.index("current")
        self.debug_tabs[index].on_video_output_click(click_location, scale)

    def on_tab_change(self, event):
        index = self.debug_notebook.index("current")
        self.debug_tabs[index].update(context.emulator)

    def remove_from_window(self):
        super().remove_from_window()

        if self.debug_frame:
            self.debug_frame.destroy()
        self.debug_frame = None
