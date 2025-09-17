import time
import tkinter
from tkinter import Tk, Toplevel, ttk

from modules.context import context
from modules.debug_utilities import debug_create_pokemon, debug_write_party
from modules.items import get_item_by_index, get_item_by_name
from modules.pokemon import (
    Pokemon,
    get_species_by_national_dex,
    get_nature_by_index,
    get_move_by_index,
    StatsValues,
    Species,
    StatusCondition,
    get_move_by_name,
    get_species_by_name,
    LearnedMove,
    ContestConditions,
)
from modules.pokemon_party import get_party

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
        self.window.geometry("640x560")
        self.window.protocol("WM_DELETE_WINDOW", self._remove_window)
        self.window.bind("<Escape>", self._remove_window)
        self.window.rowconfigure(0, weight=1)
        self.window.columnconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.window)
        self.notebook.grid(sticky="NWES", padx=5, pady=5)
        # self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)

        self.save_button = ttk.Button(self.window, text="Save Party", command=self._save_party, style="Accent.TButton")
        self.save_button.grid(sticky="NE", row=1, column=0, padx=5, pady=5)

        self._pokemon_frames = []
        party = get_party()
        for n in range(6):
            pokemon = party[n] if n < len(party) else Pokemon(b"\x00" * 100)
            frame = PokemonEditFrame(self.window, self.notebook, pokemon)
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

        debug_write_party(new_party)

        self.close_window()


class PokemonEditFrame:
    def __init__(self, window: Toplevel, parent: ttk.Widget, pokemon: Pokemon | None):
        self._window = window
        self._parent = parent
        self._pokemon = pokemon
        self._species: Species | None = None if pokemon.is_empty else pokemon.species
        self._species_var: tkinter.StringVar
        self._held_item: ttk.Combobox
        self._ability: ttk.Combobox
        self._nature: ttk.Combobox
        self._nickname_var = tkinter.StringVar(parent, value=pokemon.nickname)
        if pokemon.is_empty or pokemon.nickname.upper() == pokemon.species.localised_names[context.rom.language.value]:
            self._nickname_var.set("")
        self._experience = tkinter.IntVar(value=pokemon.total_exp)
        self._level = tkinter.IntVar(value=pokemon.level)
        self._is_shiny_var = tkinter.BooleanVar(value=pokemon.is_shiny and not pokemon.is_empty)
        self._is_egg_var = tkinter.BooleanVar(value=pokemon.is_egg)
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

        self._contest_conditions = {
            "coolness": tkinter.IntVar(value=pokemon.contest_conditions.coolness),
            "beauty": tkinter.IntVar(value=pokemon.contest_conditions.beauty),
            "cuteness": tkinter.IntVar(value=pokemon.contest_conditions.cuteness),
            "smartness": tkinter.IntVar(value=pokemon.contest_conditions.smartness),
            "toughness": tkinter.IntVar(value=pokemon.contest_conditions.toughness),
            "feel": tkinter.IntVar(value=pokemon.contest_conditions.feel),
        }

        self._moves = (
            tkinter.StringVar(value=pokemon.moves[0].move.name if pokemon.moves[0] is not None else "(None)"),
            tkinter.StringVar(value=pokemon.moves[1].move.name if pokemon.moves[1] is not None else "(None)"),
            tkinter.StringVar(value=pokemon.moves[2].move.name if pokemon.moves[2] is not None else "(None)"),
            tkinter.StringVar(value=pokemon.moves[3].move.name if pokemon.moves[3] is not None else "(None)"),
        )

        self._move_pp_spinbox: list[ttk.Spinbox] = []

        self._move_pp_vars = [
            tkinter.IntVar(value=pokemon.moves[0].pp if pokemon.moves[0] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[1].pp if pokemon.moves[1] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[2].pp if pokemon.moves[2] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[3].pp if pokemon.moves[3] is not None else 0),
        ]

        self._move_max_pp_labels: list[ttk.Label] = []

        self._move_pp_ups_vars = [
            tkinter.IntVar(value=pokemon.moves[0].pp_ups if pokemon.moves[0] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[1].pp_ups if pokemon.moves[1] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[2].pp_ups if pokemon.moves[2] is not None else 0),
            tkinter.IntVar(value=pokemon.moves[3].pp_ups if pokemon.moves[3] is not None else 0),
        ]

        self._current_hp_var = tkinter.IntVar(value=pokemon.current_hp)
        self._total_hp_label: ttk.Label
        self._friendship_var = tkinter.IntVar(value=pokemon.friendship)
        self._status_condition: ttk.Combobox
        self.frame = self._build_frame()

    def to_pokemon(self) -> Pokemon | None:
        if self._species is None:
            return None

        if self._held_item.get() == "(None)":
            held_item = None
        else:
            held_item = get_item_by_name(self._held_item.get())

        moves = []
        for n in range(4):
            selection = self._moves[n].get()
            if selection != "(None)":
                move = get_move_by_name(selection)
                moves.append(
                    LearnedMove.create(
                        move, remaining_pp=self._move_pp_vars[n].get(), pp_ups=self._move_pp_ups_vars[n].get()
                    )
                )
        if len(moves) == 0:
            moves.append(LearnedMove.create(get_move_by_name("Splash"), remaining_pp=1, pp_ups=0))

        return debug_create_pokemon(
            species=self._species,
            level=self._level.get(),
            original_pokemon=self._pokemon,
            is_shiny=self._is_shiny_var.get(),
            is_egg=self._is_egg_var.get(),
            gender=None if self._gender_var.get() not in ("male", "female") else self._gender_var.get(),
            nickname=self._nickname_var.get(),
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
            contest_conditions=ContestConditions(
                self._contest_conditions["coolness"].get(),
                self._contest_conditions["beauty"].get(),
                self._contest_conditions["cuteness"].get(),
                self._contest_conditions["smartness"].get(),
                self._contest_conditions["toughness"].get(),
                self._contest_conditions["feel"].get(),
            ),
        )

    def _build_frame(self) -> ttk.Frame:
        frame = ttk.Frame(self._parent)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(0, weight=1)

        left_box = ttk.LabelFrame(frame, text="Basic Information")
        left_box.grid(sticky="NWE", column=0, row=0, padx=5, pady=5)

        center_box = ttk.Frame(frame)
        center_box.grid(sticky="NWE", column=1, row=0, padx=5, pady=5)

        right_box = ttk.LabelFrame(frame, text="Stats")
        right_box.grid(sticky="NWE", column=2, row=0, padx=5, pady=5)

        species_values = ["(Empty)"]
        for n in range(386):
            species_values.append(f"#{n + 1:03d} {get_species_by_national_dex(n + 1).name}")

        species_frame = ttk.Frame(left_box, padding=5)
        label = ttk.Label(species_frame, text="Species:")
        label.grid(sticky="NWES", column=0, row=0)
        self._species_var = tkinter.StringVar(
            value=species_values[self._pokemon.species.national_dex_number if not self._pokemon.is_empty else 0]
        )
        species = ttk.Combobox(species_frame, values=species_values, state="readonly", textvariable=self._species_var)
        species.grid(column=0, row=1)
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

        exp_frame.grid(sticky="NWES", column=0, row=5)

        shiny_frame = ttk.Frame(left_box, padding=5)
        ttk.Checkbutton(shiny_frame, text="Shiny", variable=self._is_shiny_var).grid(sticky="W")
        ttk.Checkbutton(shiny_frame, text="Egg", variable=self._is_egg_var).grid(sticky="W", row=1)
        shiny_frame.grid(sticky="NWES", column=0, row=6)

        gender_frame = ttk.Frame(left_box, padding=5)
        ttk.Label(gender_frame, text="Gender:").grid(sticky="W", column=0, row=0)
        gender_frame.grid(sticky="NWES", column=0, row=7)
        female_button = ttk.Radiobutton(gender_frame, text="Female", variable=self._gender_var, value="female")
        male_button = ttk.Radiobutton(gender_frame, text="Male", variable=self._gender_var, value="male")
        gender_label = ttk.Label(gender_frame, text="Male")
        if 0 < self._pokemon.species.gender_ratio < 254:
            female_button.grid(sticky="W", row=1, column=0)
            male_button.grid(sticky="W", row=2, column=0)
        elif self._pokemon.species.gender_ratio == 0:
            gender_label.configure(text="Male")
            gender_label.grid(sticky="W", row=1, column=0)
        elif self._pokemon.species.gender_ratio == 254:
            gender_label.configure(text="Female")
            gender_label.grid(sticky="W", row=1, column=0)
        else:
            gender_label.configure(text="None")
            gender_label.grid(sticky="W", row=1, column=0)

        move_list = ["(None)"]
        for n in range(354):
            move = get_move_by_index(n + 1)
            move_list.append(move.name)
        move_list.sort()

        def on_move_change(var, index, mode):
            for n in range(4):
                if str(self._moves[n]) == var or str(self._move_pp_ups_vars[n]) == var:
                    max_pp = get_move_by_name(self._moves[n].get()).pp if self._moves[n].get() != "(None)" else 0
                    try:
                        max_pp += (max_pp * 20 * self._move_pp_ups_vars[n].get()) // 100
                    except tkinter.TclError:
                        continue
                    self._move_max_pp_labels[n].configure(text=f"/{max_pp}")
                    self._move_pp_vars[n].set(max_pp)
                    self._move_pp_spinbox[n].configure(to=max_pp)

        for n in range(4):
            move_frame = ttk.LabelFrame(center_box, text=f"Move #{n + 1}:", padding=5)
            combobox = ttk.Combobox(move_frame, values=move_list, state="readonly", textvariable=self._moves[n])
            combobox.grid(column=0, row=0, sticky="NW")
            self._moves[n].trace_add("write", on_move_change)

            if self._pokemon.moves[n] is not None:
                total_pp = self._pokemon.moves[n].total_pp
            else:
                total_pp = 0

            pp_frame = ttk.Frame(move_frame)
            label = ttk.Label(pp_frame, text="PP:")
            label.grid(column=0, row=0)

            spinbox = ttk.Spinbox(pp_frame, from_=0, to=total_pp, width=3, textvariable=self._move_pp_vars[n])
            spinbox.grid(column=1, row=0, pady=5)
            self._move_pp_spinbox.append(spinbox)

            suffix = ttk.Label(pp_frame, text=f"/{total_pp}")
            suffix.grid(column=2, row=0)
            self._move_max_pp_labels.append(suffix)

            pp_frame.grid(column=0, row=1, sticky="NW")

            pp_up_frame = ttk.Frame(move_frame)
            label = ttk.Label(pp_up_frame, text="PP Ups:")
            label.grid(column=0, row=0)

            pp_up_spinbox = ttk.Spinbox(pp_up_frame, from_=0, to=3, width=3, textvariable=self._move_pp_ups_vars[n])
            pp_up_spinbox.grid(column=1, row=0)
            self._move_pp_ups_vars[n].trace_add("write", on_move_change)

            pp_up_frame.grid(column=0, row=2, sticky="NW")

            move_frame.grid(sticky="NWES", column=0, row=n, pady=(0, 5))

        stats_list = {
            "hp": "HP",
            "attack": "Atk",
            "defence": "Def",
            "speed": "Speed",
            "special_attack": "SpAtk",
            "special_defence": "SpDef",
        }

        stats_frame = ttk.Frame(right_box)
        stats_frame.columnconfigure(0, weight=1)
        ttk.Label(stats_frame, text="").grid(sticky="W", column=0, row=0)
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
        self._total_hp_label = ttk.Label(current_hp_frame, text=f"/{self._pokemon.stats.hp}")
        self._total_hp_label.grid(sticky="NWES", column=2, row=0)
        current_hp_frame.grid(sticky="W", column=0, row=1, padx=5, pady=15)

        friendship_frame = ttk.Frame(right_box)
        friendship_label = ttk.Label(friendship_frame, text="Friendship: ")
        friendship_label.grid(sticky="NWES", column=0, row=0)
        friendship = ttk.Spinbox(friendship_frame, from_=0, to=255, width=3, textvariable=self._friendship_var)
        friendship.grid(sticky="NWES", column=1, row=0)
        suffix_label = ttk.Label(friendship_frame, text="/255")
        suffix_label.grid(sticky="NWES", column=2, row=0)
        friendship_frame.grid(sticky="NWES", column=0, row=7, padx=5, pady=(0, 15))

        def update_friendship_label(var=None, index=None, mode=None):
            if self._is_egg_var.get():
                friendship_label.configure(text="Egg Cycles: ")
            else:
                friendship_label.configure(text="Friendship: ")

        update_friendship_label()
        self._is_egg_var.trace_add("write", update_friendship_label)

        status_frame = ttk.Frame(right_box)
        label = ttk.Label(status_frame, text="Status Condition:")
        label.grid(sticky="W", column=0, row=0)
        self._status_condition = ttk.Combobox(status_frame, state="readonly", values=list(status_name_map.keys()))
        self._status_condition.current(list(status_name_map.values()).index(self._pokemon.status_condition))
        self._status_condition.grid(sticky="W", column=0, row=1)
        status_frame.grid(sticky="W", column=0, row=8, padx=5, pady=(0, 5))

        contest_frame = ttk.Frame(right_box)
        label = ttk.Label(contest_frame, text="Contest Conditions:")
        label.grid(sticky="W", column=0, row=0)
        n = 1
        for condition in ["coolness", "beauty", "cuteness", "smartness", "toughness", "feel"]:
            ttk.Label(contest_frame, text=condition.title()).grid(sticky="W", column=0, row=n)
            condition_field = ttk.Spinbox(
                contest_frame, from_=0, to=255, width=3, textvariable=self._contest_conditions[condition]
            )
            condition_field.grid(sticky="W", column=1, row=n, padx=5)
            n += 1
        contest_frame.grid(sticky="W", column=0, row=9, padx=5, pady=(8, 5))

        def recalculate_max_hp(var=None, index=None, mode=None):
            if self._species is None:
                return

            try:
                ivs = StatsValues(self._iv_vars["hp"].get(), 0, 0, 0, 0, 0)
                evs = StatsValues(self._ev_vars["hp"].get(), 0, 0, 0, 0, 0)
                max_hp = StatsValues.calculate(self._species, ivs, evs, get_nature_by_index(0), self._level.get()).hp
            except tkinter.TclError:
                return
            self._current_hp_var.set(int(min(max_hp, self._current_hp_var.get())))
            self._total_hp_label.configure(text=f"/{max_hp}")

        self._iv_vars["hp"].trace_add("write", recalculate_max_hp)
        self._ev_vars["hp"].trace_add("write", recalculate_max_hp)

        def update_exp_labels(_=None, __=None, ___=None):
            level_button.configure(text=f"Level: {self._level.get()}")
            if self._level.get() < 100 and self._species is not None:
                exp_needed_until_next_level = (
                    self._species.level_up_type.get_experience_needed_for_level(self._level.get() + 1)
                    - self._experience.get()
                )
                exp_left.configure(text=f"({exp_needed_until_next_level:,} Exp. until level-up)")
            else:
                exp_left.configure(text="")
            recalculate_max_hp()

        self._experience.trace_add("write", update_exp_labels)
        update_exp_labels()

        def on_change_species(var, index, mode):
            new_species = self._species_var.get()
            if new_species == "(Empty)":
                self._species = None
                return

            new_species = get_species_by_name(new_species[5:])
            if new_species is not self._species:
                is_second_ability = self._ability.current() != 0
                choices = [ability.name for ability in new_species.abilities]
                self._ability.configure(values=choices)
                self._ability.current(1 if is_second_ability and len(choices) > 1 else 0)

                previous_pokemon = self.to_pokemon()
                if previous_pokemon is not None and not previous_pokemon.is_empty:
                    hp_fraction = previous_pokemon.current_hp_percentage / 100
                    exp_fraction = previous_pokemon.exp_fraction_to_next_level
                else:
                    hp_fraction = 1
                    exp_fraction = 0
                    self._level.set(int(max(1, self._level.get())))
                    if self._friendship_var.get() == 0:
                        self._friendship_var.set(new_species.base_friendship)

                self._species = new_species
                new_pokemon = self.to_pokemon()

                max_hp = new_pokemon.stats.hp
                self._current_hp_var.set(int(max_hp * hp_fraction))
                self._total_hp_label.configure(text=f"/{new_pokemon.stats.hp}")

                level_group = new_species.level_up_type
                exp = level_group.get_experience_needed_for_level(self._level.get())
                if self._level.get() < 100:
                    exp_next_level = level_group.get_experience_needed_for_level(self._level.get() + 1)
                    exp_diff = exp_next_level - exp
                    exp += int(exp_diff * exp_fraction)
                self._experience.set(exp)

                female_button.grid_forget()
                male_button.grid_forget()
                gender_label.grid_forget()
                if 0 < new_species.gender_ratio < 254:
                    if self._gender_var.get() not in ("male", "female"):
                        if new_species.gender_ratio < 127:
                            self._gender_var.set("male")
                        else:
                            self._gender_var.set("female")
                    female_button.grid(sticky="W", row=1, column=0)
                    male_button.grid(sticky="W", row=2, column=0)
                elif new_species.gender_ratio == 0:
                    self._gender_var.set("male")
                    gender_label.configure(text="Male")
                    gender_label.grid(sticky="W", row=1, column=0)
                elif new_species.gender_ratio == 254:
                    self._gender_var.set("female")
                    gender_label.configure(text="Female")
                    gender_label.grid(sticky="W", row=1, column=0)
                else:
                    self._gender_var.set("none")
                    gender_label.configure(text="None")
                    gender_label.grid(sticky="W", row=1, column=0)

        self._species_var.trace_add("write", on_change_species)

        return frame

    def _set_experience(self):
        exp_window = Toplevel(self._window)

        def remove_window(event=None):
            nonlocal exp_window
            exp_window.destroy()
            exp_window = None

        exp_window.title(f"Set Experience for {self._species.name}")
        exp_window.geometry("360x160")
        exp_window.protocol("WM_DELETE_WINDOW", remove_window)
        exp_window.bind("<Escape>", remove_window)
        exp_window.rowconfigure(0, weight=1)
        exp_window.columnconfigure(0, weight=1)

        frame = ttk.Frame(exp_window)
        frame.grid(sticky="NWES", column=0, row=0, padx=5, pady=5)

        level_type = self._species.level_up_type
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
            try:
                level.get()
                experience.get()
            except tkinter.TclError:
                return

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


def run_edit_party_screen():
    PartyEditMenu(context.gui.window).loop()
