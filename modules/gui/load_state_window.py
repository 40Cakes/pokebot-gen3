import random
import re
import time
from pathlib import Path
from tkinter import ttk, Toplevel, Canvas, PhotoImage, TclError
from ttkthemes import ThemedTk

import PIL.Image
import PIL.ImageDraw
import PIL.ImageTk

from modules.context import context
from modules.runtime import get_sprites_path


class LoadStateWindow:
    def __init__(self, window: ThemedTk):
        state_directory = context.profile.path / "states"
        if not state_directory.is_dir():
            return

        state_files: list[Path] = [file for file in state_directory.glob("*.ss1")]
        if len(state_files) < 1:
            return

        def remove_window(event=None):
            self._load_save_window.destroy()
            self._load_save_window = None

        def load_state(state: Path):
            context.emulator.load_save_state(state.read_bytes())
            self._load_save_window.after(50, remove_window)

        self._load_save_window = Toplevel(window)
        self._load_save_window.title("Load a Save State")
        self._load_save_window.geometry("525x500")
        self._load_save_window.protocol("WM_DELETE_WINDOW", remove_window)
        self._load_save_window.bind("<Escape>", remove_window)
        self._load_save_window.rowconfigure(0, weight=1)
        self._load_save_window.columnconfigure(0, weight=1)

        scrollable_frame = ttk.Frame(self._load_save_window)
        scrollable_frame.pack(fill="both", expand=True)

        canvas = Canvas(scrollable_frame)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(scrollable_frame, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        frame = ttk.Frame(canvas, width=500)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        canvas.create_window((0, 0), window=frame, anchor="nw")

        def filter_state_files(files: list[Path]):
            maximum_number_of_autosave_files = 3

            autosaves_already_included = 0
            autosave_pattern = re.compile("^\\d{4}-\\d{2}-\\d{2}_\\d{2}-\\d{2}-\\d{2}\\.ss1$")
            files.sort(reverse=True, key=lambda file: file.stat().st_mtime)
            for file in files:
                if file.name == "current_state.ss1" or autosave_pattern.match(file.name):
                    if autosaves_already_included >= maximum_number_of_autosave_files:
                        continue
                    autosaves_already_included += 1
                yield file

        photo_buffer = []
        column = 0
        row = 0
        for state in filter_state_files(state_files):
            with open(state, "rb") as file:
                is_png = file.read(4) == b"\x89PNG"

            photo = None
            if is_png:
                try:
                    photo = PhotoImage(master=canvas, file=state)
                except TclError:
                    photo = None

            if photo is None:
                placeholder = PIL.Image.new(mode="RGBA", size=(240, 160))
                draw = PIL.ImageDraw.Draw(placeholder)
                draw.rectangle(xy=[(0, 0), (placeholder.width, placeholder.height)], fill="#000000FF")
                possible_sprites = [
                    "TM01.png",
                    "TM26.png",
                    "TM44.png",
                    "TM Dark.png",
                    "TM Dragon.png",
                    "TM Electric.png",
                    "TM Fire.png",
                    "TM Flying.png",
                    "TM Ghost.png",
                    "TM Grass.png",
                    "TM Ice.png",
                    "TM Normal.png",
                    "TM Poison.png",
                    "TM Rock.png",
                    "TM Steel.png",
                    "TM Water.png",
                ]
                sprite = PIL.Image.open(get_sprites_path() / "items" / random.choice(possible_sprites))
                if sprite.mode != "RGBA":
                    sprite = sprite.convert("RGBA")
                sprite = sprite.resize((sprite.width * 3, sprite.height * 3), resample=False)
                sprite_position = (
                    placeholder.width // 2 - sprite.width // 2,
                    placeholder.height // 2 - sprite.height // 2,
                )
                placeholder.paste(sprite, sprite_position, sprite)
                photo_buffer.append(placeholder)
                photo = PIL.ImageTk.PhotoImage(master=canvas, image=placeholder)

            photo_buffer.append(photo)
            button_frame = ttk.Frame(frame, padding=5)
            button_frame.rowconfigure(0, weight=1)
            button_frame.columnconfigure(0, weight=1)
            button_frame.grid(row=int(row), column=column, sticky="NSWE")
            button = ttk.Button(
                button_frame,
                text=state.name,
                image=photo,
                compound="top",
                padding=0,
                width=1,
                command=lambda s=state: load_state(s),
            )
            button.grid(sticky="NSWE")
            column = 1 if column == 0 else 0
            row += 0.5

        while self._load_save_window is not None:
            self._load_save_window.update_idletasks()
            self._load_save_window.update()
            time.sleep(1 / 60)

    def focus(self):
        self._load_save_window.focus_force()
