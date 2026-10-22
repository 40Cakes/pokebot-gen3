import tkinter
import webbrowser
import zlib
from datetime import datetime
from tkinter import Tk, Menu

import PIL.PngImagePlugin
import plyer

from modules.battle_state import battle_is_active
from modules.clock import get_clock_time
from modules.context import context
from modules.debug_utilities import (
    debug_give_test_item_pack,
    debug_give_max_coins_and_money,
    import_flags_and_vars,
    export_flags_and_vars,
    debug_get_test_party,
    debug_write_party,
    debug_give_fainted_first_slot_pokemon_with_special_ability,
    debug_create_pokemon,
)
from modules.gui.debug_edit_item_bag import run_edit_item_bag_screen
from modules.gui.debug_edit_party import run_edit_party_screen
from modules.gui.debug_edit_pokedex import run_edit_pokedex_screen
from modules.gui.multi_select_window import ask_for_confirmation, ask_for_choice, Selection
from modules.memory import (
    write_symbol,
    pack_uint16,
    pack_uint8,
    pack_uint32,
    set_event_var,
    GameState,
    read_symbol,
)
from modules.modes import BotListener, BotMode, FrameInfo
from modules.player import get_player
from modules.pokemon import get_opponent
from modules.pokemon_party import get_party, get_party_size
from modules.runtime import get_sprites_path, get_base_path


def _create_save_state() -> None:
    target_path = plyer.filechooser.save_file(
        path=str(get_base_path() / "tests" / "states"),
        filters=[".ss1"],
    )
    if target_path is None or len(target_path) != 1:
        return

    with open(target_path[0], "wb") as file:
        screenshot = context.emulator.get_screenshot()
        extra_chunks = PIL.PngImagePlugin.PngInfo()
        extra_chunks.add(b"gbAs", zlib.compress(context.emulator.get_save_state()))

        save_game = context.emulator.read_save_data()
        extra_chunks.add(b"gbAx", pack_uint32(2) + pack_uint32(len(save_game)) + zlib.compress(save_game))

        screenshot.save(file, format="PNG", pnginfo=extra_chunks)

    context.message = f"State saved to `{target_path[0]}`."


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


def _advance_rtc_hours(hours: int) -> None:
    context.emulator._core.rtc.advance_time(60 * 60 * 1000 * hours)
    rtc_value = datetime.fromtimestamp(datetime.now().timestamp() + context.emulator._core.rtc._core.rtc.value / 1000)
    context.message = f"RTC has been adjusted to {rtc_value.isoformat()}!"


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
    context.message = f"✅ Exported flags and vars to " + target_path[0].replace("\\", "/").split("/")[-1]


def _edit_party() -> None:
    run_edit_party_screen()


def _edit_item_bag() -> None:
    run_edit_item_bag_screen()


def _edit_pokedex() -> None:
    run_edit_pokedex_screen()


class InfiniteRepelListener(BotListener):
    def __del__(self) -> None:
        _disable_listener(InfiniteRepelListener)
        set_event_var("REPEL_STEP_COUNT", 0)

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        set_event_var("REPEL_STEP_COUNT", 250)


class InfiniteSafariZoneListener(BotListener):
    def __del__(self) -> None:
        _disable_listener(InfiniteSafariZoneListener)

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not battle_is_active():
            write_symbol("gNumSafariBalls", pack_uint8(30))
            step_counter_symbol = "sSafariZoneStepCounter" if context.rom.is_emerald else "gSafariZoneStepCounter"
            write_symbol(step_counter_symbol, pack_uint16(500))


class ForceShinyEncounterListener(BotListener):
    def __init__(self):
        self._battle_was_active = False
        self._game_state_was_battle = False

    def __del__(self) -> None:
        _disable_listener(ForceShinyEncounterListener)

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not self._battle_was_active and frame.task_is_active("Task_BattleStart"):
            self._battle_was_active = True
            player = get_player()
            opponent = get_opponent()
            ot = opponent.original_trainer
            if ot.id == player.trainer_id and ot.secret_id == player.secret_id and not opponent.is_shiny:
                new_opponent = debug_create_pokemon(
                    species=opponent.species,
                    level=opponent.level,
                    original_pokemon=opponent,
                    is_egg=False,
                    is_shiny=True,
                    gender=opponent.gender,
                    nickname="CHEAT",
                    held_item=opponent.held_item,
                    has_second_ability=opponent.ability is not opponent.species.abilities[0],
                    nature=opponent.nature,
                    experience=opponent.total_exp,
                    friendship=opponent.friendship,
                    moves=[move for move in opponent.moves if move is not None],
                    ivs=opponent.ivs,
                    evs=opponent.evs,
                    current_hp=opponent.current_hp,
                    status_condition=opponent.status_condition,
                )
                write_symbol("gEnemyParty", new_opponent.data)

        elif self._battle_was_active and not self._game_state_was_battle and frame.game_state is GameState.BATTLE:
            self._game_state_was_battle = True
        elif self._battle_was_active and self._game_state_was_battle and frame.game_state is not GameState.BATTLE:
            self._battle_was_active = False
            self._game_state_was_battle = False


class ForcePokenavCallListener(BotListener):
    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        match_call_state = read_symbol("sMatchCallState")
        new_match_call_state = (
            pack_uint32(get_clock_time().total_minutes() - 30) + match_call_state[4:6] + b"\x70" + match_call_state[7:8]
        )
        write_symbol("sMatchCallState", new_match_call_state)


def _enable_listener(listener_class: type[BotListener]) -> None:
    context.bot_listeners = [listener_class(), *context.bot_listeners]


def _disable_listener(listener_class: type[BotListener]) -> None:
    context.bot_listeners = [listener for listener in context.bot_listeners if not isinstance(listener, listener_class)]


class DebugMenu(Menu):
    def __init__(self, window: Tk):
        super().__init__(window, tearoff=0)

        def toggleable_listener(listener_class: type[BotListener]) -> tkinter.BooleanVar:
            var = tkinter.BooleanVar()

            def update_handler(*args):
                _disable_listener(listener_class)
                if var.get():
                    _enable_listener(listener_class)

            var.trace_add("write", update_handler)

            return var

        ability_menu = Menu(self, tearoff=0)
        ability_menu.add_command(
            label="Illuminate (double encounter rate)",
            command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Illuminate"),
        )
        if context.rom.is_emerald:
            ability_menu.add_command(
                label="Sticky Hold (more fishing encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Sticky Hold"),
            )
            ability_menu.add_command(
                label="Compound Eyes (higher chance of holding item)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Compoundeyes"),
            )
            ability_menu.add_command(
                label="Pressure (higher level encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Pressure"),
            )
            ability_menu.add_command(
                label="Intimidate (fewer level<=5 encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Intimidate"),
            )
            ability_menu.add_command(
                label="Magnet Pull (more Steel encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Magnet Pull"),
            )
            ability_menu.add_command(
                label="Static (more Electric encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Static"),
            )
            ability_menu.add_command(
                label="Synchronize (more same nature encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Synchronize"),
            )
            ability_menu.add_command(
                label="Cute Charm (more opposite gender encounters)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Cute Charm"),
            )
            ability_menu.add_command(
                label="Magma Armor (halves time for eggs to hatch)",
                command=lambda: debug_give_fainted_first_slot_pokemon_with_special_ability("Magma Armor"),
            )

        self.add_command(label="Edit Party", command=_edit_party)
        self.add_command(label="Edit Item Bag", command=_edit_item_bag)
        self.add_command(label="Edit Pokédex", command=_edit_pokedex)
        self.add_separator()
        self.add_command(label="Give Test Party", command=_give_test_party)
        self.add_command(label="Give Test Item Pack", command=_give_test_item_pack)
        self.add_cascade(label="Give Lead with Ability", menu=ability_menu)
        self.add_separator()
        self.add_checkbutton(label="Infinite Repel", variable=toggleable_listener(InfiniteRepelListener))
        self.add_checkbutton(label="Infinite Safari Zone", variable=toggleable_listener(InfiniteSafariZoneListener))
        self.add_checkbutton(label="Force Shiny Encounter", variable=toggleable_listener(ForceShinyEncounterListener))
        self.add_checkbutton(label="Force PokeNav Call", variable=toggleable_listener(ForcePokenavCallListener))
        self.add_separator()
        self.add_command(label="Advance RTC by one hour", command=lambda: _advance_rtc_hours(1))
        self.add_command(label="Advance RTC by one day", command=lambda: _advance_rtc_hours(24))
        self.add_command(label="Turn back RTC by one hour", command=lambda: _advance_rtc_hours(-1))
        self.add_command(label="Turn back RTC by one day", command=lambda: _advance_rtc_hours(-24))
        self.add_separator()
        self.add_command(label="Export events and vars", command=_export_flags_and_vars)
        self.add_command(label="Import events and vars", command=_import_flags_and_vars)
        self.add_command(label="Create state with save game", command=_create_save_state)
        self.add_separator()

        self.add_command(
            label="Help",
            command=lambda: webbrowser.open_new_tab(
                "https://github.com/40Cakes/pokebot-gen3/blob/main/wiki/pages/Data%20Manipulation%20-%20Save%20Modification.md"
            ),
        )
