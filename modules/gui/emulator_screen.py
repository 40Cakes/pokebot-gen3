from collections import deque
from tkinter import Button, PhotoImage, Tk

import PIL.Image
import PIL.ImageTk

from modules.gui.debug_tabs import *
from modules.gui.emulator_controls import DebugEmulatorControls, EmulatorControls
from modules.sprites import generate_placeholder_image
from modules.version import pokebot_name, pokebot_version


# Defines how many frames can be reverted at the most in stepping mode.
stepping_mode_frame_history_size = 128
stepping_mode_forward_key = "<space>"
stepping_mode_reverse_key = "<Control-space>"


class EmulatorScreen:
    def __init__(self, window: Tk):
        self.window = window
        self.frame: Union[ttk.Frame, None] = None
        self.canvas: Union[Canvas, None] = None
        self.current_canvas_image: Union[PhotoImage, None] = None
        self._current_canvas_image_id: int | None = None
        self._placeholder_image: Union[PhotoImage, None] = None
        self.center_of_canvas: tuple[int, int] = (240, 160)

        self.width: int = 240
        self.height: int = 160
        self._scale: int = 2

        self._stepping_mode: bool = False
        self._stepping_button: Union[Button, None] = None
        self._current_step: int = 0
        self._step_history: deque[bytes] = deque(maxlen=stepping_mode_frame_history_size + 1)
        self._stepping_mode_bound_keys: list[tuple[str, str]] = []

        self._controls: EmulatorControls | None = None

    def _initialise_controls(self, debug: bool = False) -> None:
        if debug:
            controls = DebugEmulatorControls(self.window)
            controls.add_tab(TasksTab())
            controls.add_tab(BattleTab())
            controls.add_tab(PlayerTab())
            controls.add_tab(MapTab(self.canvas))
            controls.add_tab(MiscTab())
            controls.add_tab(SymbolsTab())
            controls.add_tab(EventFlagsTab())
            controls.add_tab(EventVarsTab())
            controls.add_tab(EmulatorTab())
        else:
            controls = EmulatorControls(self.window)
        self._controls = controls

    def enable(self) -> None:
        self.window.title(f"{context.profile.path.name} | {pokebot_name} {pokebot_version}")
        self.window.resizable(context.debug, context.debug)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.frame = ttk.Frame(self.window)
        self.frame.grid(sticky="NSWE")
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self._add_canvas()
        self._initialise_controls(context.debug)
        self.scale = 2

    def disable(self) -> None:
        if self.frame:
            self.frame.destroy()
        self.window.geometry("540x400")
        self.window.resizable(context.debug, True)

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

            def update_back_button():
                if len(self._step_history) > 1:
                    self._back_button.config(background="orange", state="normal")
                else:
                    self._back_button.config(background="grey", state="disabled")

            def next_step(*args):
                if len(args) > 0 and args[0].state & 4 != 0 and not stepping_mode_forward_key.startswith("<Control-"):
                    return

                self._current_step += 1
                self._step_history.append(context.emulator.get_save_state())
                update_back_button()

            def previous_step(*args):
                if len(args) > 0 and args[0].state & 4 != 0 and not stepping_mode_reverse_key.startswith("<Control-"):
                    return

                if len(self._step_history) > 1:
                    self._current_step -= 1
                    self._step_history.pop()
                    save_state = self._step_history[-1]
                    context.emulator.load_save_state(save_state)
                    update_back_button()

            self._stepping_button = Button(
                self.window, text="⮞", padx=8, background="red", foreground="white", command=next_step, cursor="hand2"
            )
            self._stepping_button.place(x=32, y=0)

            self._back_button = Button(
                self.window, text="⮜", padx=8, foreground="white", command=previous_step, cursor="hand2"
            )
            self._back_button.place(x=0, y=0)
            update_back_button()

            self._current_step = 0
            self._step_history.append(context.emulator.get_save_state())

            bind_reference_forward = self.window.bind(stepping_mode_forward_key, next_step)
            bind_reference_reverse = self.window.bind(stepping_mode_reverse_key, previous_step)

            self._stepping_mode_bound_keys.append((stepping_mode_forward_key, bind_reference_forward))
            self._stepping_mode_bound_keys.append((stepping_mode_reverse_key, bind_reference_reverse))
        else:
            self._back_button.destroy()
            self._stepping_button.destroy()
            self._step_history.clear()
            for sequence, function_reference in self._stepping_mode_bound_keys:
                self.window.unbind(sequence, function_reference)
            self._stepping_mode_bound_keys.clear()

    def _generate_placeholder_image(self):
        image = generate_placeholder_image(self.width * self.scale, self.height * self.scale)
        self._placeholder_image = PIL.ImageTk.PhotoImage(image)
        self.current_canvas_image = self._placeholder_image
        self.canvas.create_image(self.center_of_canvas, image=self.current_canvas_image, state="normal")

    def _update_image(self, image: PIL.Image):
        if self._current_canvas_image_id:
            self.canvas.delete(self._current_canvas_image_id)
        self.current_canvas_image = PIL.ImageTk.PhotoImage(
            image=image.resize((self.width * self.scale, self.height * self.scale), resample=False)
        )
        self._current_canvas_image_id = self.canvas.create_image(
            self.center_of_canvas, image=self.current_canvas_image, state="normal"
        )
        self._update_window()

    def _update_window(self):
        if self.scale > 1:
            self._controls.on_frame_render()

        self.window.update_idletasks()
        self.window.update()

    def _add_canvas(self) -> None:
        self.canvas = Canvas(self.window, width=480, height=320)
        self.canvas.grid(sticky="NW", row=0, column=0)
        if context.debug:

            def handle_click_on_video_output(event):
                if context.video:
                    self._controls.on_video_output_click((event.x // self.scale, event.y // self.scale), self.scale)

            self.canvas.bind("<Button-1>", handle_click_on_video_output)
