from tkinter import Tk, Button, Canvas, PhotoImage

import PIL.Image
import PIL.ImageTk

from modules.gui.debug_tabs import *
from modules.gui.emulator_controls import EmulatorControls, DebugEmulatorControls
from modules.sprites import generate_placeholder_image
from modules.version import pokebot_name, pokebot_version


class EmulatorScreen:
    def __init__(self, window: Tk):
        self.window = window
        self.frame: Union[ttk.Frame, None] = None
        self.canvas: Union[Canvas, None] = None
        self.current_canvas_image: Union[PhotoImage, None] = None
        self._placeholder_image: Union[PhotoImage, None] = None
        self.center_of_canvas: tuple[int, int] = (240, 160)

        self.width: int = 240
        self.height: int = 160
        self._scale: int = 2

        self._stepping_mode: bool = False
        self._stepping_button: Union[Button, None] = None
        self._current_step: int = 0

        if context.debug:
            controls = DebugEmulatorControls(self.window)
            controls.add_tab(TasksTab())
            controls.add_tab(BattleTab())
            controls.add_tab(TrainerTab())
            controls.add_tab(DaycareTab())
            controls.add_tab(SymbolsTab())
            controls.add_tab(EventFlagsTab())
            controls.add_tab(InputsTab())
        else:
            controls = EmulatorControls(self.window)
        self._controls = controls

    def enable(self) -> None:
        self.window.title(f"{context.profile.path.name} | {pokebot_name} {pokebot_version}")
        self.window.resizable(False, False)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self.window)
        self.frame.grid(sticky="NSWE")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self._add_canvas()
        self.scale = 2

    def disable(self) -> None:
        if self.frame:
            self.frame.destroy()

    def update(self) -> None:
        if context.emulator._performance_tracker.time_since_last_render() >= (1 / 60) * 1_000_000_000:
            if context.emulator.get_video_enabled():
                self._update_image(context.emulator.get_current_screen_image())
            else:
                self._update_window()
            context.emulator._performance_tracker.track_render()

        previous_step = self._current_step
        while self._stepping_mode and previous_step == self._current_step:
            self.window.update_idletasks()
            self.window.update()
            time.sleep(1 / 60)

    def on_settings_updated(self) -> None:
        self._controls.update()
        if not context.video and self._placeholder_image is None:
            self._generate_placeholder_image()
        elif context.video and self._placeholder_image is not None:
            self._placeholder_image = None

    @property
    def scale(self) -> int:
        return self._scale

    @scale.setter
    def scale(self, scale: int) -> None:
        self._controls.remove_from_window()
        self._scale = scale
        if scale > 1:
            self.window.geometry(
                "%dx%d"
                % (
                    self.width * self._scale + self._controls.get_additional_width(),
                    self.height * self._scale + self._controls.get_additional_height(),
                )
            )
        else:
            self.window.geometry(f"{self.width}x{self.height}")

        self.window.rowconfigure(0, weight=0, minsize=self.height * self._scale)
        self.window.rowconfigure(1, weight=1)
        self.window.columnconfigure(0, weight=0, minsize=self.width * self._scale)
        self.window.columnconfigure(1, weight=1)

        self.canvas.config(width=self.width * self._scale, height=self.height * self._scale)
        self.center_of_canvas = (self._scale * self.width // 2, self._scale * self.height // 2)

        if not context.video:
            self._generate_placeholder_image()

        if scale > 1:
            self._controls.add_to_window()

    def toggle_stepping_mode(self) -> None:
        self._stepping_mode = not self._stepping_mode
        if self._stepping_mode:
            def next_step():
                self._current_step += 1

            self._stepping_button = Button(self.window, text="⮞", padx=8, background="red", foreground="white",
                                           command=next_step, cursor="hand2")
            self._stepping_button.place(x=0, y=0)
            self._current_step = 0
        else:
            self._stepping_button.destroy()

    def _generate_placeholder_image(self):
        image = generate_placeholder_image(self.width * self.scale, self.height * self.scale)
        self._placeholder_image = PIL.ImageTk.PhotoImage(image)
        self.current_canvas_image = self._placeholder_image
        self.canvas.create_image(self.center_of_canvas, image=self.current_canvas_image, state="normal")

    def _update_image(self, image: PIL.Image):
        self.current_canvas_image = PIL.ImageTk.PhotoImage(
            image=image.resize((self.width * self.scale, self.height * self.scale), resample=False))
        self.canvas.create_image(self.center_of_canvas, image=self.current_canvas_image, state="normal")
        self._update_window()

    def _update_window(self):
        if self.scale > 1:
            self._controls.on_frame_render()

        self.window.update_idletasks()
        self.window.update()

    def _add_canvas(self) -> None:
        self.canvas = Canvas(self.window, width=480, height=320)
        self.canvas.grid(sticky="NW", row=0, column=0)
