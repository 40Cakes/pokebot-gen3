import random
import struct
import time
import tkinter
from tkinter import Tk, Toplevel, ttk
from typing import Literal

import numpy

from modules.context import context
from modules.game import encode_string
from modules.items import get_item_by_index, Item, get_item_by_name
from modules.memory import write_symbol
from modules.pokemon import (
    get_party,
    Pokemon,
    get_species_by_national_dex,
    get_nature_by_index,
    get_move_by_index,
    StatsValues,
    Species,
    POKEMON_DATA_SUBSTRUCTS_ORDER,
    Nature,
    StatusCondition,
    get_move_by_name,
    get_species_by_name,
)

status_name_map = {
    "Healthy": StatusCondition.Healthy,
    "Asleep": StatusCondition.Sleep,
    "Poisoned": StatusCondition.Poison,
    "Burned": StatusCondition.Burn,
    "Frozen": StatusCondition.Freeze,
    "Paralysed": StatusCondition.Paralysis,
    "Badly Poisoned": StatusCondition.BadPoison,
}


class PartyEditMenu:
    def __init__(self, main_window: Tk):
        self._main_window = main_window
        self.window: Toplevel | None = Toplevel(main_window)

        self.window.title("Edit Party")
        self.window.geometry("640x520")
        self.window.protocol("WM_DELETE_WINDOW", self._remove_window)
        self.window.bind("<Escape>", self._remove_window)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.window)
        self.notebook.grid(sticky="NWES", padx=5, pady=5)
        # self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.save_button = ttk.Button(self.window, text="Save Party", command=self._save_party)
        self.save_button.grid(sticky="NE", row=1, column=0, padx=5, pady=5)

        self._pokemon_frames = []
        party = get_party()
        for n in range(6):
            frame = PokemonEditFrame(self.window, self.notebook, party[n])
            self._pokemon_frames.append(frame)

            if n < len(party):
                label = party[n].species.name
            else:
                label = "(empty)"

            self.notebook.add(frame.frame, text=f"#{n + 1}: {label}")

    def loop(self) -> None:
        while self.window is not None:
            self.window.update_idletasks()
            self.window.update()
            time.sleep(1 / 60)

    def close_window(self):
        if self.window is not None:
            self.window.after(50, self._remove_window)

    def _remove_window(self, event=None):
        self.window.destroy()
        self.window = None

    def _save_party(self, event=None):
        new_party = []
        for frame in self._pokemon_frames:
            pokemon = frame.to_pokemon()
            if pokemon is not None:
                new_party.append(pokemon)

        if len(new_party) > 0:
            write_symbol("gPlayerPartyCount", len(new_party).to_bytes(1, byteorder="little"))
            new_party_data = b""
            for pokemon in new_party:
                new_party_data += pokemon.data
            write_symbol("gPlayerParty", new_party_data.ljust(600, b"\x00"))

        self.close_window()


class PokemonEditFrame:
    def __init__(self, window: Toplevel, parent: ttk.Widget, pokemon: Pokemon | None):
        self._window = window
        self._parent = parent
        self._pokemon = pokemon
        self._species: ttk.Combobox
        self._held_item: ttk.Combobox
        self._ability: ttk.Combobox
        self._nature: ttk.Combobox
        self._nickname_var = tkinter.StringVar(
            parent, value="" if pokemon.nickname == pokemon.species.name.upper() else pokemon.nickname
        )
        self._experience = tkinter.IntVar(value=pokemon.total_exp)
        self._level = tkinter.IntVar(value=pokemon.level)
        self._is_shiny_var = tkinter.BooleanVar(value=pokemon.is_shiny)
        self._gender_var = tkinter.StringVar(value="none" if pokemon.gender is None else pokemon.gender)

        self._iv_vars = {
            "hp": tkinter.IntVar(value=pokemon.ivs.hp),
            "attack": tkinter.IntVar(value=pokemon.ivs.attack),
            "defence": tkinter.IntVar(value=pokemon.ivs.defence),
            "speed": tkinter.IntVar(value=pokemon.ivs.speed),
            "special_attack": tkinter.IntVar(value=pokemon.ivs.special_attack),
            "special_defence": tkinter.IntVar(value=pokemon.ivs.special_defence),
        }

        self._ev_vars = {
            "hp": tkinter.IntVar(value=pokemon.evs.hp),
            "attack": tkinter.IntVar(value=pokemon.evs.attack),
            "defence": tkinter.IntVar(value=pokemon.evs.defence),
            "speed": tkinter.IntVar(value=pokemon.evs.speed),
            "special_attack": tkinter.IntVar(value=pokemon.evs.special_attack),
            "special_defence": tkinter.IntVar(value=pokemon.evs.special_defence),
        }

        self._moves: list[ttk.Combobox] = []

        self._move_pp_vars = [
            tkinter.IntVar(value=pokemon.moves[0].pp if pokemon.moves[0] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[1].pp if pokemon.moves[1] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[2].pp if pokemon.moves[2] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[3].pp if pokemon.moves[3] is not None else 0),
        ]

        self._move_pp_ups_vars = [
            tkinter.IntVar(value=pokemon.moves[0].pp_ups if pokemon.moves[0] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[1].pp_ups if pokemon.moves[1] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[2].pp_ups if pokemon.moves[2] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[3].pp_ups if pokemon.moves[3] is not None else 0),
        ]

        self._current_hp_var = tkinter.IntVar(value=pokemon.current_hp)
        self._friendship_var = tkinter.IntVar(value=pokemon.friendship)
        self._status_condition: ttk.Combobox
        self.frame = self._build_frame()

    def to_pokemon(self) -> Pokemon | None:
        species_name = self._species.get()
        if species_name == "(Empty)":
            return None

        species = get_species_by_name(species_name[5:])
        if self._held_item.get() == "(None)":
            held_item = None
        else:
            held_item = get_item_by_name(self._held_item.get())

        moves = []
        for n in range(4):
            selection = self._moves[n].get()
            if selection == "(None)":
                moves.append({"id": 0, "remaining_pp": 0, "pp_ups": 0})
            else:
                move = get_move_by_name(selection)
                moves.append(
                    {
                        "id": move.index,
                        "remaining_pp": self._move_pp_vars[n].get(),
                        "pp_ups": self._move_pp_ups_vars[n].get(),
                    }
                )

        return _create_pokemon(
            self._pokemon,
            is_shiny=self._is_shiny_var.get(),
            gender=None if self._gender_var.get() not in ("male", "female") else self._gender_var.get(),
            species=species,
            nickname=self._nickname_var.get(),
            level=self._level.get(),
            held_item=held_item,
            has_second_ability=self._ability.current() != 0,
            nature=get_nature_by_index(self._nature.current()),
            experience=self._experience.get(),
            friendship=self._friendship_var.get(),
            moves=moves,
            ivs=StatsValues(
                self._iv_vars["hp"].get(),
                self._iv_vars["attack"].get(),
                self._iv_vars["defence"].get(),
                self._iv_vars["speed"].get(),
                self._iv_vars["special_attack"].get(),
                self._iv_vars["special_defence"].get(),
            ),
            evs=StatsValues(
                self._ev_vars["hp"].get(),
                self._ev_vars["attack"].get(),
                self._ev_vars["defence"].get(),
                self._ev_vars["speed"].get(),
                self._ev_vars["special_attack"].get(),
                self._ev_vars["special_defence"].get(),
            ),
            current_hp=self._current_hp_var.get(),
            status_condition=status_name_map[self._status_condition.get()],
        )

    def _build_frame(self) -> ttk.Frame:
        frame = ttk.Frame(self._parent)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(0, weight=1)

        left_box = ttk.LabelFrame(frame, text="Basic Information")
        left_box.grid(sticky="NWES", column=0, row=0, padx=5, pady=5)

        center_box = ttk.Frame(frame)
        center_box.grid(sticky="NWES", column=1, row=0, padx=5, pady=5)

        right_box = ttk.LabelFrame(frame, text="Stats")
        right_box.grid(sticky="NWES", column=2, row=0, padx=5, pady=5)

        species_values = ["(Empty)"]
        for n in range(386):
            species_values.append(f"#{n + 1:03d} {get_species_by_national_dex(n + 1).name}")

        species_frame = ttk.Frame(left_box, padding=5)
        label = ttk.Label(species_frame, text="Species:")
        label.grid(sticky="NWES", column=0, row=0)
        self._species = ttk.Combobox(species_frame, values=species_values, state="readonly")
        self._species.current(self._pokemon.species.national_dex_number)
        self._species.grid(column=0, row=1)
        species_frame.grid(sticky="W", column=0, row=0)

        nickname_frame = ttk.Frame(left_box, padding=5)
        label = ttk.Label(nickname_frame, text="Nickname:")
        label.grid(sticky="NWES", column=0, row=0)
        entry = ttk.Entry(nickname_frame, textvariable=self._nickname_var)
        entry.grid(column=0, row=1)
        nickname_frame.grid(sticky="W", column=0, row=1)

        item_values = ["(None)"]
        for n in range(376):
            item = get_item_by_index(n + 1)
            if not item.name.startswith("?"):
                item_values.append(item.name)
        item_values.sort()

        held_item_frame = ttk.Frame(left_box, padding=5)
        label = ttk.Label(held_item_frame, text="Held Item:")
        label.grid(sticky="NWES", column=0, row=0)
        self._held_item = ttk.Combobox(held_item_frame, values=item_values, state="readonly")
        self._held_item.current(
            0 if self._pokemon.held_item is None else item_values.index(self._pokemon.held_item.name)
        )
        self._held_item.grid(column=0, row=1)
        held_item_frame.grid(sticky="W", column=0, row=2)

        nature_values = []
        for n in range(25):
            nature_values.append(get_nature_by_index(n).name_with_modifiers)

        nature_frame = ttk.Frame(left_box, padding=5)
        label = ttk.Label(nature_frame, text="Nature:")
        label.grid(sticky="NWES", column=0, row=0)
        self._nature = ttk.Combobox(nature_frame, values=nature_values, state="readonly")
        self._nature.current(self._pokemon.nature.index)
        self._nature.grid(column=0, row=1)
        nature_frame.grid(sticky="W", column=0, row=3)

        ability_frame = ttk.Frame(left_box, padding=5)
        label = ttk.Label(ability_frame, text="Ability:")
        label.grid(sticky="NWES", column=0, row=0)
        ability_values = [ability.name for ability in self._pokemon.species.abilities]
        self._ability = ttk.Combobox(ability_frame, values=ability_values, state="readonly")
        self._ability.current(0 if self._pokemon.ability is self._pokemon.species.abilities[0] else 1)
        self._ability.grid(column=0, row=1)
        ability_frame.grid(sticky="W", column=0, row=4)

        exp_frame = ttk.Frame(left_box, padding=5)
        level_button = ttk.Button(exp_frame, command=self._set_experience)
        level_button.grid(sticky="W", column=0, row=0)
        exp_left = ttk.Label(exp_frame, font=(None, 8))
        exp_left.grid(sticky="W", column=0, row=1)

        def update_exp_labels(_=None, __=None, ___=None):
            level_button.configure(text=f"Level: {self._level.get()}")
            if self._level.get() < 100:
                exp_needed_until_next_level = (
                    self._pokemon.species.level_up_type.get_experience_needed_for_level(self._level.get() + 1)
                    - self._experience.get()
                )
                exp_left.configure(text=f"({exp_needed_until_next_level:,} Exp. until level-up)")
            else:
                exp_left.configure(text="")

        update_exp_labels()
        self._experience.trace_add("write", update_exp_labels)

        exp_frame.grid(sticky="NWES", column=0, row=5)

        shiny_frame = ttk.Frame(left_box, padding=5)
        ttk.Checkbutton(shiny_frame, text="Shiny", variable=self._is_shiny_var).grid(sticky="W")
        shiny_frame.grid(sticky="NWES", column=0, row=6)

        gender_frame = ttk.Frame(left_box, padding=5)
        ttk.Label(gender_frame, text="Gender:").grid(sticky="W", column=0, row=0)
        gender_frame.grid(sticky="NWES", column=0, row=7)
        if 0 < self._pokemon.species.gender_ratio < 254:
            female_button = ttk.Radiobutton(gender_frame, text="Female", variable=self._gender_var, value="female")
            male_button = ttk.Radiobutton(gender_frame, text="Male", variable=self._gender_var, value="male")
            female_button.grid(sticky="W", row=1, column=0)
            male_button.grid(sticky="W", row=2, column=0)
        elif self._pokemon.species.gender_ratio == 0:
            ttk.Label(gender_frame, text="Male").grid(sticky="W", row=1, column=0)
        elif self._pokemon.species.gender_ratio == 254:
            ttk.Label(gender_frame, text="Female").grid(sticky="W", row=1, column=0)
        else:
            ttk.Label(gender_frame, text="None").grid(sticky="W", row=1, column=0)

        move_list = ["(None)"]
        for n in range(354):
            move = get_move_by_index(n + 1)
            move_list.append(move.name)
        move_list.sort()

        for n in range(4):
            learned_move = self._pokemon.moves[n]
            move = None if learned_move is None else learned_move.move

            move_frame = ttk.LabelFrame(center_box, text=f"Move #{n + 1}:", padding=5)

            combobox = ttk.Combobox(move_frame, values=move_list, state="readonly")
            combobox.current(0 if move is None else move_list.index(move.name))
            combobox.grid(column=0, row=0, sticky="NW")
            self._moves.append(combobox)

            if learned_move is not None:
                pp_frame = ttk.Frame(move_frame)
                label = ttk.Label(pp_frame, text="PP:")
                label.grid(column=0, row=0)

                pp_spinbox = ttk.Spinbox(
                    pp_frame, from_=0, to=learned_move.total_pp, width=3, textvariable=self._move_pp_vars[n]
                )
                pp_spinbox.grid(column=1, row=0, pady=5)

                suffix = ttk.Label(pp_frame, text=f"/{learned_move.total_pp}")
                suffix.grid(column=2, row=0)

                pp_frame.grid(column=0, row=1, sticky="NW")

                pp_up_frame = ttk.Frame(move_frame)
                label = ttk.Label(pp_up_frame, text="PP Ups:")
                label.grid(column=0, row=0)

                pp_up_spinbox = ttk.Spinbox(pp_up_frame, from_=0, to=3, width=3, textvariable=self._move_pp_ups_vars[n])
                pp_up_spinbox.grid(column=1, row=0)

                pp_up_frame.grid(column=0, row=2, sticky="NW")

            move_frame.grid(sticky="NWES", column=0, row=n, pady=(0, 5))

        stats_list = {
            "attack": "Atk",
            "defence": "Def",
            "speed": "Speed",
            "special_attack": "SpAtk",
            "special_defence": "SpDef",
        }

        stats_frame = ttk.Frame(right_box)
        stats_frame.columnconfigure(0, weight=1)
        ttk.Label(stats_frame, text="Stat").grid(sticky="W", column=0, row=0)
        ttk.Label(stats_frame, text="IVs").grid(sticky="W", column=1, row=0)
        ttk.Label(stats_frame, text="EVs").grid(sticky="W", column=2, row=0)
        stats_frame.grid(sticky="NWES", column=0, row=0, padx=5, pady=5)

        n = 0
        for stat in stats_list:
            n += 1
            ttk.Label(stats_frame, text=stats_list[stat]).grid(sticky="W", column=0, row=n)
            iv_field = ttk.Spinbox(stats_frame, from_=0, to=31, width=3, textvariable=self._iv_vars[stat])
            iv_field.grid(sticky="W", column=1, row=n, padx=5)
            ev_field = ttk.Spinbox(stats_frame, from_=0, to=255, width=3, textvariable=self._ev_vars[stat])
            ev_field.grid(sticky="W", column=2, row=n)

        current_hp_frame = ttk.Frame(right_box)
        label = ttk.Label(current_hp_frame, text="Current HP: ")
        label.grid(sticky="NWES", column=0, row=0)
        current_hp = ttk.Spinbox(
            current_hp_frame, from_=0, to=self._pokemon.stats.hp, width=3, textvariable=self._current_hp_var
        )
        current_hp.grid(sticky="NWES", column=1, row=0)
        suffix_label = ttk.Label(current_hp_frame, text=f"/{self._pokemon.stats.hp}")
        suffix_label.grid(sticky="NWES", column=2, row=0)
        current_hp_frame.grid(sticky="W", column=0, row=1, padx=5, pady=15)

        friendship_frame = ttk.Frame(right_box)
        label = ttk.Label(friendship_frame, text="Friendship: ")
        label.grid(sticky="NWES", column=0, row=0)
        friendship = ttk.Spinbox(friendship_frame, from_=0, to=255, width=3, textvariable=self._friendship_var)
        friendship.grid(sticky="NWES", column=1, row=0)
        suffix_label = ttk.Label(friendship_frame, text="/255")
        suffix_label.grid(sticky="NWES", column=2, row=0)
        friendship_frame.grid(sticky="NWES", column=0, row=7, padx=5, pady=(0, 15))

        status_frame = ttk.Frame(right_box)
        label = ttk.Label(status_frame, text="Status Condition:")
        label.grid(sticky="W", column=0, row=0)
        self._status_condition = ttk.Combobox(status_frame, state="readonly", values=list(status_name_map.keys()))
        self._status_condition.current(list(status_name_map.values()).index(self._pokemon.status_condition))
        self._status_condition.grid(sticky="W", column=0, row=1)
        status_frame.grid(sticky="W", column=0, row=8, padx=5)

        return frame

    def _set_experience(self):
        exp_window = Toplevel(self._window)

        def remove_window(event=None):
            nonlocal exp_window
            exp_window.destroy()
            exp_window = None

        exp_window.title(f"Set Experience for {self._pokemon.species.name}")
        exp_window.geometry("360x160")
        exp_window.protocol("WM_DELETE_WINDOW", remove_window)
        exp_window.bind("<Escape>", remove_window)
        exp_window.rowconfigure(0, weight=1)
        exp_window.columnconfigure(0, weight=1)

        frame = ttk.Frame(exp_window)
        frame.grid(sticky="NWES", column=0, row=0, padx=5, pady=5)

        level_type = self._pokemon.species.level_up_type
        set_type = tkinter.StringVar(value="exp")
        experience = tkinter.IntVar(value=self._pokemon.total_exp)
        level = tkinter.IntVar(value=self._pokemon.level)

        experience_entry: ttk.Spinbox | None = None
        level_entry: ttk.Spinbox | None = None

        def on_type_change(var, index, mode):
            if set_type.get() == "exp":
                experience_entry.configure(state="normal", increment=1)
                level_entry.configure(state="readonly", increment=0)
            else:
                experience_entry.configure(state="readonly", increment=0)
                level_entry.configure(state="normal", increment=1)
                on_number_change(str(level), None, None)

        def on_number_change(var, index, mode):
            if var == str(experience):
                state = str(experience_entry.configure()["state"][4])
                if state != "readonly":
                    level_with_this_exp = level_type.get_level_from_total_experience(experience.get())
                    if level_with_this_exp != level.get():
                        level.set(level_with_this_exp)

            if var == str(level):
                state = str(level_entry.configure()["state"][4])
                if state != "readonly" and 0 < level.get() <= 100:
                    if set_type.get() == "level_end" and level.get() <= 99:
                        experience_value = level_type.get_experience_needed_for_level(level.get() + 1) - 1
                    else:
                        experience_value = level_type.get_experience_needed_for_level(level.get())
                    if experience_value != experience.get():
                        experience.set(experience_value)

        set_type.trace_add("write", on_type_change)
        experience.trace_add("write", on_number_change)
        level.trace_add("write", on_number_change)

        first_row = ttk.Frame(frame)
        first_row.grid(sticky="NW", column=0, row=0, pady=(5, 15), padx=5)

        label = ttk.Label(first_row, text="Exp.: ")
        label.grid(sticky="W", column=0, row=0)
        max_exp = level_type.get_experience_needed_for_level(100)
        experience_entry = ttk.Spinbox(first_row, from_=0, to=max_exp, width=8, textvariable=experience)
        experience_entry.grid(sticky="W", column=1, row=0, padx=(0, 15))

        label = ttk.Label(first_row, text="Level: ")
        label.grid(sticky="W", column=2, row=0)
        level_entry = ttk.Spinbox(
            first_row, from_=1, to=100, width=3, textvariable=level, state="readonly", increment=0
        )
        level_entry.grid(sticky="W", column=3, row=0)

        radio1 = ttk.Radiobutton(frame, text="Set custom number of Experience", variable=set_type, value="exp")
        radio2 = ttk.Radiobutton(
            frame, text="Set level, with 0 Exp. towards the next level", variable=set_type, value="level_start"
        )
        radio3 = ttk.Radiobutton(
            frame, text="Set level, with 1 Exp. missing until levelling up", variable=set_type, value="level_end"
        )
        radio1.grid(sticky="W", column=0, row=2, padx=5)
        radio2.grid(sticky="W", column=0, row=3, padx=5)
        radio3.grid(sticky="W", column=0, row=4, padx=5)

        def do_save(event=None):
            self._level.set(level.get())
            self._experience.set(experience.get())
            exp_window.after(50, remove_window)

        save_button = ttk.Button(frame, text="Set Experience", command=do_save)
        save_button.grid(sticky="W", column=0, row=5, padx=5, pady=(15, 5))

        while exp_window is not None:
            exp_window.update_idletasks()
            exp_window.update()
            time.sleep(1 / 60)


def _create_pokemon(
    original_pokemon: Pokemon,
    is_shiny: bool,
    gender: Literal["male", "female"] | None,
    species: Species,
    nickname: str,
    level: int,
    held_item: Item | None,
    has_second_ability: bool,
    nature: Nature,
    experience: int,
    friendship: int,
    moves: list[dict],
    ivs: StatsValues,
    evs: StatsValues,
    current_hp: int,
    status_condition: StatusCondition,
) -> Pokemon:
    iv_egg_ability = (
        ivs.hp
        | (ivs.attack << 5)
        | (ivs.defence << 10)
        | (ivs.speed << 15)
        | (ivs.special_attack << 20)
        | (ivs.special_defence << 25)
    )
    if has_second_ability:
        iv_egg_ability |= 1 << 31

    pp_bonuses = (
        (moves[0]["pp_ups"] << 6) | (moves[1]["pp_ups"] << 4) | (moves[2]["pp_ups"] << 2) | (moves[3]["pp_ups"] << 0)
    )

    data_to_encrypt = (
        species.index.to_bytes(2, byteorder="little")
        + (held_item.index if held_item is not None else 0).to_bytes(2, byteorder="little")
        + experience.to_bytes(4, byteorder="little")
        + pp_bonuses.to_bytes(1)
        + friendship.to_bytes(1)
        + original_pokemon._decrypted_data[10:12]
        + moves[0]["id"].to_bytes(2, byteorder="little")
        + moves[1]["id"].to_bytes(2, byteorder="little")
        + moves[2]["id"].to_bytes(2, byteorder="little")
        + moves[3]["id"].to_bytes(2, byteorder="little")
        + moves[0]["remaining_pp"].to_bytes(1)
        + moves[1]["remaining_pp"].to_bytes(1)
        + moves[2]["remaining_pp"].to_bytes(1)
        + moves[3]["remaining_pp"].to_bytes(1)
        + evs.hp.to_bytes(1)
        + evs.attack.to_bytes(1)
        + evs.defence.to_bytes(1)
        + evs.speed.to_bytes(1)
        + evs.special_attack.to_bytes(1)
        + evs.special_defence.to_bytes(1)
        + original_pokemon._decrypted_data[62:68]
        + original_pokemon._decrypted_data[68:72]
        + iv_egg_ability.to_bytes(4, byteorder="little")
        + original_pokemon._decrypted_data[76:80]
    )

    if nickname != "" and nickname != species.name.upper():
        encoded_nickname = encode_string(nickname)
    else:
        encoded_nickname = encode_string(species.name.upper())

    stats = StatsValues.calculate(species, ivs, evs, nature, level)

    def personality_value_matches_criteria(pv: int) -> bool:
        if pv % 25 != nature.index:
            return False

        if 0 < species.gender_ratio < 254:
            is_male = pv & 0xFF >= species.gender_ratio
            if is_male and gender != "male":
                return False
            if not is_male and gender == "male":
                return False

        shiny_value = (
            original_pokemon.original_trainer.id
            ^ original_pokemon.original_trainer.secret_id
            ^ (pv >> 16)
            ^ (pv & 0xFFFF)
        )
        if is_shiny and shiny_value > 7:
            return False
        if not is_shiny and shiny_value <= 7:
            return False

        return True

    personality_value = original_pokemon.personality_value
    n = 0
    while not personality_value_matches_criteria(personality_value):
        if n > 10_000_000:
            raise RuntimeError("Could not find a suitable PV in time.")
        n += 1
        personality_value = random.randint(0, 2**32)

    data = (
        personality_value.to_bytes(length=4, byteorder="little")
        + original_pokemon.data[4:8]
        + encoded_nickname.ljust(10, b"\xFF")
        + original_pokemon.data[18:28]
        + (sum(struct.unpack("<24H", data_to_encrypt)) & 0xFFFF).to_bytes(length=2, byteorder="little")
        + original_pokemon.data[30:32]
        + data_to_encrypt
        + status_condition.to_bitfield().to_bytes(length=1, byteorder="little")
        + original_pokemon.data[81:84]
        + level.to_bytes(length=1, byteorder="little")
        + original_pokemon.data[85:86]
        + current_hp.to_bytes(length=2, byteorder="little")
        + stats.hp.to_bytes(length=2, byteorder="little")
        + stats.attack.to_bytes(length=2, byteorder="little")
        + stats.defence.to_bytes(length=2, byteorder="little")
        + stats.speed.to_bytes(length=2, byteorder="little")
        + stats.special_attack.to_bytes(length=2, byteorder="little")
        + stats.special_defence.to_bytes(length=2, byteorder="little")
    )

    u32le = numpy.dtype("<u4")
    personality_value_bytes = numpy.frombuffer(data, count=1, dtype=u32le)
    original_trainer_id = numpy.frombuffer(data, count=1, offset=4, dtype=u32le)
    key = numpy.repeat(personality_value_bytes ^ original_trainer_id, 3)
    order = POKEMON_DATA_SUBSTRUCTS_ORDER[personality_value % 24]

    encrypted_data = numpy.concatenate(
        [numpy.frombuffer(data, count=3, offset=32 + (order.index(i) * 12), dtype=u32le) ^ key for i in range(4)]
    )

    return Pokemon(data[:32] + encrypted_data.tobytes() + data[80:100])


def run_edit_party_screen():
    PartyEditMenu(context.gui.window).loop()
