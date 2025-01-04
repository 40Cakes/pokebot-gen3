import time
from tkinter import *

from rich.prompt import IntPrompt

from modules.context import context
from modules.pokemon import Pokemon
from modules.pokemon import StatsValues
from modules.pokemon_party import get_party


def ask_for_ev_targets(pokemon: "Pokemon") -> StatsValues:
    if context.gui.is_headless:
        return StatsValues(
            hp=IntPrompt.ask("Choose target HP EVs", default=pokemon.evs.hp),
            attack=IntPrompt.ask("Choose target Attack EVs", default=pokemon.evs.attack),
            defence=IntPrompt.ask("Choose target Defence EVs", default=pokemon.evs.defence),
            speed=IntPrompt.ask("Choose target Speed EVs", default=pokemon.evs.speed),
            special_attack=IntPrompt.ask("Choose target Special Attack EVs", default=pokemon.evs.special_attack),
            special_defence=IntPrompt.ask("Choose target Special Defence EVs", default=pokemon.evs.special_defence),
        )

    spinboxes: list[Spinbox] = []
    selected_ev_targets: StatsValues | None = None

    def remove_window(event=None):
        nonlocal window
        window.destroy()
        window = None

    def return_selection():
        nonlocal spinboxes, selected_ev_targets
        selected_ev_targets = StatsValues(
            hp=int(spinboxes[0].get()),
            attack=int(spinboxes[1].get()),
            defence=int(spinboxes[2].get()),
            speed=int(spinboxes[5].get()),
            special_attack=int(spinboxes[3].get()),
            special_defence=int(spinboxes[4].get()),
        )
        window.after(50, remove_window)

    window = Toplevel(context.gui.window)
    window.title("EV goals")
    window.protocol("WM_DELETE_WINDOW", remove_window)
    window.bind("<Escape>", remove_window)

    Label(window, text=get_party()[0].name).grid(row=1, column=0)

    Label(window, text="HP").grid(row=0, column=1)
    Label(window, text="Atk").grid(row=0, column=2)
    Label(window, text="Def").grid(row=0, column=3)
    Label(window, text="SpA").grid(row=0, column=4)
    Label(window, text="SpD").grid(row=0, column=5)
    Label(window, text="Spe").grid(row=0, column=6)

    for stat in ("hp", "attack", "defence", "special_attack", "special_defence", "speed"):
        spinbox = Spinbox(window, from_=0, to=252, increment=4, wrap=True, width=8)
        spinbox.delete(0, last=None)
        spinbox.insert(0, str(pokemon.evs[stat]))
        spinbox.grid(row=1, column=len(spinboxes) + 1, padx=10, pady=3)
        spinboxes.append(spinbox)

    Button(window, text="EV Train", width=20, height=1, bg="lightblue", command=return_selection).grid(
        row=7, column=3, columnspan=2, pady=15
    )

    while window is not None:
        window.update_idletasks()
        window.update()
        time.sleep(1 / 60)

    return selected_ev_targets
