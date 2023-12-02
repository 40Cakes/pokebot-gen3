import time
from dataclasses import dataclass
from idlelib.tooltip import Hovertip
from pathlib import Path
from tkinter import Tk, ttk, Toplevel, Canvas, PhotoImage
from typing import List

from modules.context import context


@dataclass
class Selection:
    button_label: str
    button_enable: bool
    button_tooltip: str
    sprite: Path


@dataclass
class MultiSelector:
    window_title: str
    selections: List[Selection]


class MultiSelectWindow:
    def __init__(self, window: Tk, options: MultiSelector):
        def remove_window(event=None):
            self._multi_select_window.destroy()
            self._multi_select_window = None

        def return_selection(selection: str):
            context.selected_pokemon = selection
            self._multi_select_window.after(50, remove_window)

        window_geometry = (len(options.selections) * 164, 180)

        self._multi_select_window = Toplevel(window)
        self._multi_select_window.title(options.window_title)
        self._multi_select_window.geometry(f"{window_geometry[0]}x{window_geometry[1]}")
        self._multi_select_window.protocol("WM_DELETE_WINDOW", remove_window)
        self._multi_select_window.bind("<Escape>", remove_window)
        self._multi_select_window.rowconfigure(0, weight=1)
        self._multi_select_window.columnconfigure(0, weight=1)

        frame = ttk.Frame(self._multi_select_window)
        frame.pack(fill="both", expand=True)

        canvas = Canvas(frame)
        canvas.pack(side="left", fill="both", expand=True)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        frame = ttk.Frame(canvas, width=window_geometry[1])
        for i in range(0, len(options.selections)):
            frame.columnconfigure(i, weight=1)
        canvas.create_window((0, 0), window=frame, anchor="nw")

        photo_buffer = []
        column = 0
        for selection in options.selections:
            photo = PhotoImage(master=canvas, file=selection.sprite)

            photo_buffer.append(photo)
            button_frame = ttk.Frame(frame, padding=5)
            button_frame.grid(row=1, column=column, sticky="NSWE")
            button = ttk.Button(
                button_frame,
                text=selection.button_label,
                image=photo,
                compound="top",
                padding=10,
                width=1,
                command=lambda s=selection.button_label: return_selection(s),
            )
            button.grid(sticky="NSWE")
            button.state(["!disabled"] if selection.button_enable else ["disabled"])
            Hovertip(button, selection.button_tooltip)
            column += 1

        while self._multi_select_window is not None:
            self._multi_select_window.update_idletasks()
            self._multi_select_window.update()
            time.sleep(1 / 60)

    def focus(self):
        self._multi_select_window.focus_force()
