import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import Canvas, PhotoImage, Toplevel, ttk

from rich.prompt import Prompt

from modules.context import context


@dataclass
class Selection:
    button_label: str
    sprite: Path
    button_enable: bool = True


def ask_for_choice(choices: list[Selection], window_title: str = "Choose...") -> str | None:
    if context.gui.is_headless:
        return Prompt.ask(window_title, choices=[choice.button_label for choice in choices])

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

    maximum_number_of_lines = 1 + max(choice.button_label.count("\n") for choice in choices)

    window_geometry = (len(choices) * 164, 160 + (maximum_number_of_lines * 20))
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
    for i in range(len(choices)):
        frame.columnconfigure(i, weight=1)
    canvas.create_window((0, 0), window=frame, anchor="nw")

    photo_buffer = []
    column = 0
    for selection in choices:
        photo = PhotoImage(master=canvas, file=selection.sprite)
        if photo.width() < 128:
            photo = photo.zoom(128 // photo.width())

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
        column += 1

    while window is not None:
        window.update_idletasks()
        window.update()
        time.sleep(1 / 60)

    return selected_value
