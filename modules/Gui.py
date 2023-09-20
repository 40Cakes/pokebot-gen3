import os
import tkinter

import PIL.Image
import PIL.ImageTk

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


class Gui:
    scale: int

    def __init__(self, emulator, dimensions: tuple[int, int]):
        self.emulator = emulator
        self.width = dimensions[0]
        self.height = dimensions[1]

        self.window = tkinter.Tk()
        self.window.title('libmgba dancing queen')
        self.window.bind('<KeyPress>', self.HandleKeyDownEvent)
        self.window.bind('<KeyRelease>', self.HandleKeyUpEvent)
        self.canvas = tkinter.Canvas(self.window, width=self.width, height=self.height, bg="#000000")
        self.center_of_canvas = (self.width // 2, self.height // 2)
        self.canvas.pack()
        self.SetScale(2)

        self.input = 0

    def SetScale(self, scale: int) -> None:
        self.scale = scale
        self.window.geometry(f"{self.width * self.scale}x{self.height * self.scale}")
        self.canvas.config(width=self.width * self.scale, height=self.height * self.scale)
        self.center_of_canvas = (self.scale * self.width // 2, self.scale * self.height // 2)

    def _KeyDown(self, key: str):
        input = self.emulator.GetInputs() | input_map[key]
        self.emulator.SetInputs(input)

    def _KeyUp(self, key: str):
        input = self.emulator.GetInputs() & ~input_map[key]
        self.emulator.SetInputs(input)

    def HandleKeyDownEvent(self, event):
        match event.keysym:
            case 'Escape':
                self.emulator.SaveState()
                os._exit(1)

            case 'Tab':
                self.emulator.SetThrottle(not self.emulator.GetThrottle())

            case '1':
                self.emulator.SetTargetSecondsPerFrame(1/60)

            case '2':
                self.emulator.SetTargetSecondsPerFrame(1/120)

            case '3':
                self.emulator.SetTargetSecondsPerFrame(1/180)

            case '4':
                self.emulator.SetTargetSecondsPerFrame(1/240)

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

    def HandleKeyUpEvent(self, event):
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

    def UpdateImage(self, image: PIL.Image) -> None:
        if self.emulator._performance_tracker.current_fps:
            self.window.title(f"libmgba dancing queen ({self.emulator._performance_tracker.current_fps} fps)")

        photo_image = PIL.ImageTk.PhotoImage(image=image.resize((self.width * self.scale, self.height * self.scale), resample=False))
        self.canvas.create_image(self.center_of_canvas, image=photo_image, state="normal")
        self.window.update_idletasks()
        self.window.update()
