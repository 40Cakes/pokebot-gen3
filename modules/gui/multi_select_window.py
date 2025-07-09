import time
from dataclasses import dataclass
from pathlib import Path
from tkinter import Canvas, PhotoImage, Toplevel, ttk

from rich.prompt import Prompt

from modules.console import console
from modules.context import context


@dataclass
class Selection:
    button_label: str
    sprite: Path
    button_enable: bool = True


def ask_for_choice(choices: list[Selection], window_title: str = "Choose...") -> str | None:
    if context.gui.is_headless:
        console.print(f"\n[bold]{window_title}[/]")
        for index, choice in enumerate(choices):
            console.print(f"  [bold magenta]\\[{index + 1}][/] " + choice.button_label.replace("\n", " "))
        chosen_index = Prompt.ask(
            "Choose option (number)", show_choices=False, choices=[str(n + 1) for n in range(len(choices))]
        )
        return choices[int(chosen_index) - 1].button_label

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


def ask_for_confirmation(message: str, window_title: str = "Confirmation") -> bool | None:
    """
    Displays a confirmation window with the given message and Yes/No buttons.

    Parameters:
        message (str): The message to display in the confirmation window.
        window_title (str): The title of the window (default: "Confirmation").

    Returns:
        bool | None: True if 'Yes' is selected, False if 'No' is selected, or None if the window is closed.
    """
    if context.gui.is_headless:
        response = Prompt.ask(message, choices=["Yes", "No"])
        return response == "Yes"

    window = Toplevel(context.gui.window)
    user_choice: bool | None = None

    def on_yes():
        nonlocal user_choice
        user_choice = True
        window.after(50, remove_window)

    def on_no():
        nonlocal user_choice
        user_choice = False
        window.after(50, remove_window)

    def remove_window(event=None):
        nonlocal window
        window.destroy()
        window = None

    window.title(window_title)
    window.geometry("400x180")
    window.protocol("WM_DELETE_WINDOW", remove_window)
    window.bind("<Escape>", remove_window)
    window.rowconfigure(0, weight=1)
    window.columnconfigure(0, weight=1)

    frame = ttk.Frame(window, padding=10)
    frame.pack(fill="both", expand=True)

    label = ttk.Label(frame, text=message, anchor="center", wraplength=250)
    label.pack(pady=20)

    button_frame = ttk.Frame(frame)
    button_frame.pack()
    yes_button = ttk.Button(button_frame, text="Yes", command=on_yes)
    yes_button.grid(row=0, column=0, padx=10)
    no_button = ttk.Button(button_frame, text="No", command=on_no)
    no_button.grid(row=0, column=1, padx=10)

    checked_window_height = False
    while window is not None:
        window.update_idletasks()
        window.update()

        # Scale the window to fit the label.
        if not checked_window_height:
            checked_window_height = True
            window_height = label.winfo_reqheight() + 100
            if window_height > 180:
                window.geometry(f"400x{window_height}")

        time.sleep(1 / 60)

    return user_choice


def ask_for_choice_scroll(
    choices: list[Selection],
    window_title: str = "Choose...",
    options_per_row: int = 3,
    button_width: int = 165,
    button_height: int = 165,
    visible_rows: int = 2,
) -> str | None:
    if context.gui.is_headless:
        console.print(f"\n[bold]{window_title}[/]")
        for index, choice in enumerate(choices):
            console.print(f"  [bold magenta]\\[{index + 1}][/] " + choice.button_label.replace("\n", " "))
        chosen_index = Prompt.ask(
            "Choose option (number)", show_choices=False, choices=[str(n + 1) for n in range(len(choices))]
        )
        return choices[int(chosen_index) - 1].button_label

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

    scrollbar_width = 20

    window_width = options_per_row * button_width + scrollbar_width
    window_height = visible_rows * button_height + 50
    window_geometry = (window_width, window_height)

    window.title(window_title)
    window.geometry(f"{window_geometry[0]}x{window_geometry[1]}")
    window.protocol("WM_DELETE_WINDOW", remove_window)
    window.bind("<Escape>", remove_window)

    frame = ttk.Frame(window)
    frame.pack(fill="both", expand=True)

    canvas = Canvas(frame)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")

    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

    content_frame = ttk.Frame(canvas)
    canvas.create_window((0, 0), window=content_frame, anchor="nw")

    photo_buffer = []
    row = 0
    column = 0

    for selection in choices:
        photo = PhotoImage(master=canvas, file=selection.sprite)
        if photo.width() < 128:
            photo = photo.zoom(128 // photo.width())

        photo_buffer.append(photo)
        button_frame = ttk.Frame(content_frame, padding=5)
        button_frame.grid(row=row, column=column, sticky="NSWE", padx=5, pady=5)

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
        if column >= options_per_row:
            column = 0
            row += 1

    for i in range(options_per_row):
        content_frame.columnconfigure(i, weight=1)

    while window is not None:
        window.update_idletasks()
        window.update()
        time.sleep(1 / 60)

    return selected_value
