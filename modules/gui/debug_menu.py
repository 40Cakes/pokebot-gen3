import webbrowser
from tkinter import Tk, Menu

import plyer

from modules.context import context
from modules.debug_utilities import (
    debug_give_test_item_pack,
    debug_give_max_coins_and_money,
    import_flags_and_vars,
    export_flags_and_vars,
    debug_get_test_party,
    debug_write_party,
)
from modules.gui.debug_edit_item_bag import run_edit_item_bag_screen
from modules.gui.debug_edit_party import run_edit_party_screen
from modules.gui.debug_edit_pokedex import run_edit_pokedex_screen
from modules.gui.multi_select_window import ask_for_confirmation, ask_for_choice, Selection
from modules.pokemon_party import get_party, get_party_size
from modules.runtime import get_sprites_path


def _import_flags_and_vars() -> None:
    write_confirmation = ask_for_confirmation(
        "Warning: This action will overwrite the current event flags and variables with the data from your local flags and vars text files. To apply these changes, make sure to save your game and reset the bot. Are you sure you want to proceed?"
    )

    if not write_confirmation:
        return

    target_path = plyer.filechooser.open_file(
        path=str(context.profile.path / "event_vars_and_flags.txt"),
        filters=[
            ["Text Files", "*.txt", "*.ini"],
            ["All Files", "*"],
        ],
    )
    if target_path is None or len(target_path) != 1:
        return

    file_name = target_path[0].replace("\\", "/").split("/")[-1]
    affected_flags_and_vars = import_flags_and_vars(target_path[0])
    context.message = f"✅ Imported {affected_flags_and_vars:,} flags and vars from {file_name}"


def _give_test_party() -> None:
    pokemon_to_give = debug_get_test_party()

    if get_party_size() > (6 - len(pokemon_to_give)):
        sure = ask_for_confirmation(
            f"This will overwrite the last {len(pokemon_to_give)} slots of your party. Are you sure?"
        )
        if not sure:
            return
    debug_write_party([*get_party()[: (6 - len(pokemon_to_give))], *pokemon_to_give])
    context.message = "✅ Added a very strong Mewtwo, a Lotad for catching, and two HM slaves to your party."


def _give_test_item_pack() -> None:
    sure = ask_for_confirmation("This will overwrite your existing item bag. Are you sure that's what you want?")
    if not sure:
        return
    if context.rom.is_rse:
        rse_bicycle = ask_for_choice(
            [
                Selection("Acro Bike", get_sprites_path() / "items" / f"Acro Bike.png"),
                Selection("Mach Bike", get_sprites_path() / "items" / f"Mach Bike.png"),
            ],
            "Which bicycle do you want?",
        )
    else:
        rse_bicycle = None
    debug_give_test_item_pack(rse_bicycle)
    debug_give_max_coins_and_money()
    context.message = "✅ Added some goodies to your item bag."


def _export_flags_and_vars() -> None:
    target_path = plyer.filechooser.save_file(
        path=str(context.profile.path / "event_vars_and_flags.txt"),
        filters=[
            ["Text Files", "*.txt", "*.ini"],
            ["All Files", "*"],
        ],
    )
    if target_path is None or len(target_path) != 1:
        return

    export_flags_and_vars(target_path[0])
    context.message = f"✅ Exported flags and vars to {target_path[0].replace('\\', '/').split('/')[-1]}"


def _edit_party() -> None:
    run_edit_party_screen()


def _edit_item_bag() -> None:
    run_edit_item_bag_screen()


def _edit_pokedex() -> None:
    run_edit_pokedex_screen()


class DebugMenu(Menu):
    def __init__(self, window: Tk):
        super().__init__(window, tearoff=0)

        self.add_command(label="Export events and vars", command=_export_flags_and_vars)
        self.add_command(label="Import events and vars", command=_import_flags_and_vars)
        self.add_separator()
        self.add_command(label="Edit Party", command=_edit_party)
        self.add_command(label="Edit Item Bag", command=_edit_item_bag)
        self.add_command(label="Edit Pokédex", command=_edit_pokedex)
        self.add_separator()
        self.add_command(label="Test Party", command=_give_test_party)
        self.add_command(label="Test Item Pack", command=_give_test_item_pack)
        self.add_separator()
        self.add_command(
            label="Help",
            command=lambda: webbrowser.open_new_tab(
                "https://github.com/40Cakes/pokebot-gen3/blob/main/wiki/pages/Data%20Manipulation%20-%20Save%20Modification.md"
            ),
        )
