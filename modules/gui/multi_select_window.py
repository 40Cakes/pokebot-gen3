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
    sprite: Path
    button_tooltip: str = ""
    button_enable: bool = True


def ask_for_choice(choices: list[Selection], window_title: str = "Choose...") -> str | None:
    window = Toplevel(context.gui.window)
    selected_value: str | None = None

    def remove_window(event=None):
        nonlocal window
        window.destroy()
        window = None

    def return_selection(value: str):
        nonlocal selected_value
        selected_value = value
        window.after(50, remove_window)

    window_geometry = (len(choices) * 164, 180)
    window.title(window_title)
    window.geometry(f"{window_geometry[0]}x{window_geometry[1]}")
    window.protocol("WM_DELETE_WINDOW", remove_window)
    window.bind("<Escape>", remove_window)
    window.rowconfigure(0, weight=1)
    window.columnconfigure(0, weight=1)

    frame = ttk.Frame(window)
    frame.pack(fill="both", expand=True)

    canvas = Canvas(frame)
    canvas.pack(side="left", fill="both", expand=True)
    canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    frame = ttk.Frame(canvas, width=window_geometry[1])
    for i in range(0, len(choices)):
        frame.columnconfigure(i, weight=1)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    photo_buffer = []
    column = 0
    for selection in choices:
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
        if selection.button_tooltip:
            Hovertip(button, selection.button_tooltip)
        column += 1

    while window is not None:
        window.update_idletasks()
        window.update()
        time.sleep(1 / 60)

    return selected_value
