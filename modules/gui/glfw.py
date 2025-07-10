import threading
from typing import TYPE_CHECKING

import glfw
from OpenGL.GL import *

from mgba import ffi
from modules.context import context
from modules.game import set_rom
from modules.libmgba import LibmgbaEmulator

if TYPE_CHECKING:
    from pokebot import StartupSettings


WIDTH = 240
HEIGHT = 160


class GlfwGui:
    def __init__(self, main_loop: callable, on_exit: callable):
        self._main_loop = main_loop
        self._on_exit = on_exit
        # The GLFW frontend doesn't have any way to open confirmation
        # windows, so setting this to `True` means that any question
        # will be asked on the command line instead.
        self.is_headless = True

        self._scale = 2

    def run(self, startup_settings: "StartupSettings"):
        if startup_settings.profile is None:
            raise RuntimeError("The GLFW frontend cannot be started without selecting a profile.")

        context.profile = startup_settings.profile
        context.config.load(startup_settings.profile.path, strict=False)
        set_rom(startup_settings.profile.rom)
        context.emulator = LibmgbaEmulator(startup_settings.profile, self._on_frame)
        context.audio = not startup_settings.no_audio
        context.video = not startup_settings.no_video
        context.emulation_speed = startup_settings.emulation_speed
        context.debug = False
        context.bot_mode = startup_settings.bot_mode

        threading.Thread(target=self.run_opengl_window, daemon=True).start()
        self._main_loop()

    def run_opengl_window(self):
        if not glfw.init():
            return

        window = glfw.create_window(WIDTH * self._scale, HEIGHT * self._scale, "Pokebot OpenGL", None, None)
        if not window:
            glfw.terminate()
            return

        glfw.make_context_current(window)

        # Generate texture
        texture = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)

        def handle_input(w, key: int, scancode: int, action: int, modifiers: int):
            if action == glfw.PRESS:
                if key == glfw.KEY_UP:
                    context.emulator.hold_button("Up")
                elif key == glfw.KEY_DOWN:
                    context.emulator.hold_button("Down")
                elif key == glfw.KEY_LEFT:
                    context.emulator.hold_button("Left")
                elif key == glfw.KEY_RIGHT:
                    context.emulator.hold_button("Right")
                elif key == glfw.KEY_X:
                    context.emulator.hold_button("A")
                elif key == glfw.KEY_Z:
                    context.emulator.hold_button("B")
                elif key == glfw.KEY_ENTER:
                    context.emulator.hold_button("Start")
                elif key == glfw.KEY_BACKSPACE:
                    context.emulator.hold_button("Select")
                elif key == glfw.KEY_TAB:
                    context.toggle_manual_mode()
                    context.emulator.set_inputs(0)
                elif key == glfw.KEY_EQUAL and modifiers == glfw.MOD_SHIFT:
                    self._scale = min(5, self._scale + 1)
                    glfw.set_window_size(window, WIDTH * self._scale, HEIGHT * self._scale)
                elif key == glfw.KEY_MINUS:
                    self._scale = max(1, self._scale - 1)
                    glfw.set_window_size(window, WIDTH * self._scale, HEIGHT * self._scale)
                elif key == glfw.KEY_1:
                    context.emulation_speed = 1
                elif key == glfw.KEY_2:
                    context.emulation_speed = 2
                elif key == glfw.KEY_3:
                    context.emulation_speed = 3
                elif key == glfw.KEY_4:
                    context.emulation_speed = 4
                elif key == glfw.KEY_5:
                    context.emulation_speed = 8
                elif key == glfw.KEY_6:
                    context.emulation_speed = 16
                elif key == glfw.KEY_7:
                    context.emulation_speed = 32
                elif key == glfw.KEY_0:
                    context.emulation_speed = 0
                elif key == glfw.KEY_C and modifiers == glfw.MOD_CONTROL:
                    context.reload_config()
            elif action == glfw.RELEASE:
                if key == glfw.KEY_UP:
                    context.emulator.release_button("Up")
                elif key == glfw.KEY_DOWN:
                    context.emulator.release_button("Down")
                elif key == glfw.KEY_LEFT:
                    context.emulator.release_button("Left")
                elif key == glfw.KEY_RIGHT:
                    context.emulator.release_button("Right")
                elif key == glfw.KEY_X:
                    context.emulator.release_button("A")
                elif key == glfw.KEY_Z:
                    context.emulator.release_button("B")
                elif key == glfw.KEY_ENTER:
                    context.emulator.release_button("Start")
                elif key == glfw.KEY_BACKSPACE:
                    context.emulator.release_button("Select")

        glfw.set_key_callback(window, handle_input)

        while not glfw.window_should_close(window):
            # Simulate frame update
            frame_data = bytes(ffi.buffer(context.emulator._screen.buffer))
            # frame_data = context.emulator._screen.to_bytes()

            glClear(GL_COLOR_BUFFER_BIT)

            # Upload texture data
            if frame_data is not None:
                glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0, GL_RGBA, GL_UNSIGNED_BYTE, frame_data)

            # Draw a fullscreen textured quad
            glEnable(GL_TEXTURE_2D)
            glBegin(GL_QUADS)
            glTexCoord2f(0, 1)
            glVertex2f(-1, -1)
            glTexCoord2f(1, 1)
            glVertex2f(1, -1)
            glTexCoord2f(1, 0)
            glVertex2f(1, 1)
            glTexCoord2f(0, 0)
            glVertex2f(-1, 1)
            glEnd()

            glfw.swap_buffers(window)
            glfw.poll_events()

        glfw.terminate()

    def on_settings_updated(self) -> None:
        pass

    def _on_frame(self):
        if (
            context.emulator.get_speed_factor() == 1
            or context.emulator._performance_tracker.time_since_last_render() >= (1 / 60) * 1_000_000_000
        ):
            context.emulator._performance_tracker.track_render()
