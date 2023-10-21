import os
import copy
import json
import math
import string
import sys
import time
import importlib
import pandas as pd
from threading import Thread
from datetime import datetime

from rich.table import Table
from modules.Colours import IVColour, IVSumColour, SVColour
from modules.Config import config, ForceManualMode
from modules.Console import console
from modules.Files import ReadFile, WriteFile
from modules.Gui import SetMessage, GetEmulator
from modules.Memory import GetGameState, GameState
from modules.Pokemon import Pokemon
from modules.Profiles import Profile

CustomCatchFilters = None
CustomHooks = None
block_list: list = []
session_encounters: int = 0
session_pokemon: list = []
stats = None
encounter_timestamps: list = []
cached_encounter_rate: int = 0
cached_timestamp: str = ""
encounter_log: list = []
shiny_log = None
stats_dir = None
files = None


def InitStats(profile: Profile):
    global CustomCatchFilters, CustomHooks, stats, encounter_log, shiny_log, stats_dir, files

    config_dir_path = profile.path / "profiles"
    stats_dir_path = profile.path / "stats"
    if not stats_dir_path.exists():
        stats_dir_path.mkdir()
    stats_dir = str(stats_dir_path)

    files = {"shiny_log": str(stats_dir_path / "shiny_log.json"), "totals": str(stats_dir_path / "totals.json")}

    try:
        if (config_dir_path / "CustomCatchFilters.py").is_file():
            CustomCatchFilters = importlib.import_module(
                ".CustomCatchFilters", f"profiles.{profile.path.name}.config"
            ).CustomCatchFilters
        else:
            from profiles.CustomCatchFilters import CustomCatchFilters

        if (config_dir_path / "CustomHooks.py").is_file():
            CustomHooks = importlib.import_module(".CustomHooks", f"profiles.{profile.path.name}.config").CustomHooks
        else:
            from profiles.CustomHooks import CustomHooks

        f_stats = ReadFile(files["totals"])
        stats = json.loads(f_stats) if f_stats else None
        f_shiny_log = ReadFile(files["shiny_log"])
        shiny_log = json.loads(f_shiny_log) if f_shiny_log else {"shiny_log": []}
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        sys.exit(1)


def GetRNGStateHistory(name: str) -> list:
    try:
        default = []
        file = ReadFile(f"{stats_dir}/rng/{name}.json")
        data = json.loads(file) if file else default
        return data
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return default


def SaveRNGStateHistory(name: str, data: list) -> bool:
    try:
        if WriteFile(f"{stats_dir}/rng/{name}.json", json.dumps(data)):
            return True
        else:
            return False
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return False


def GetEncounterRate() -> int:
    global cached_encounter_rate
    global cached_timestamp

    try:
        if len(encounter_timestamps) > 1 and session_encounters > 1:
            if cached_timestamp != encounter_timestamps[-1]:
                cached_timestamp = encounter_timestamps[-1]
                encounter_rate = int(
                    (
                        3600000
                        / (
                            (
                                encounter_timestamps[-1]
                                - encounter_timestamps[-min(session_encounters, len(encounter_timestamps))]
                            )
                            * 1000
                        )
                    )
                    * (min(session_encounters, len(encounter_timestamps)))
                )
                cached_encounter_rate = encounter_rate
                return encounter_rate
            else:
                return cached_encounter_rate
        return 0
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return 0


def FlattenData(data: dict) -> dict:
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + "_")
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + "_")
                i += 1
        else:
            out[name[:-1]] = x

    flatten(data)
    return out


def PrintStats(pokemon: Pokemon) -> None:
    try:
        type_colour = pokemon.species.types[0].name.lower()
        rich_name = f"[{type_colour}]{pokemon.species.name}[/]"
        console.print("\n")
        console.rule(f"{rich_name} encountered at {pokemon.location_met}", style=type_colour)

        match config["logging"]["console"]["encounter_data"]:
            case "verbose":
                pokemon_table = Table()
                pokemon_table.add_column("PID", justify="center", width=10)
                pokemon_table.add_column("Level", justify="center")
                pokemon_table.add_column("Item", justify="center", width=10)
                pokemon_table.add_column("Nature", justify="center", width=10)
                pokemon_table.add_column("Ability", justify="center", width=15)
                pokemon_table.add_column(
                    "Hidden Power", justify="center", width=15, style=pokemon.hidden_power_type.name.lower()
                )
                pokemon_table.add_column("Shiny Value", justify="center", style=SVColour(pokemon.shiny_value), width=10)
                pokemon_table.add_row(
                    str(hex(pokemon.personality_value)[2:]).upper(),
                    str(pokemon.level),
                    pokemon.held_item.name if pokemon.held_item else "-",
                    pokemon.nature.name,
                    pokemon.ability.name,
                    f"{pokemon.hidden_power_type.name} ({pokemon.hidden_power_damage})",
                    f"{pokemon.shiny_value:,}",
                )
                console.print(pokemon_table)
            case "basic":
                console.print(
                    f"{rich_name}: PID: {str(hex(pokemon.personality_value)[2:]).upper()} | "
                    f"Lv.: {pokemon.level:,} | "
                    f"Item: {pokemon.held_item.name if pokemon.held_item else '-'} | "
                    f"Nature: {pokemon.nature.name} | "
                    f"Ability: {pokemon.ability.name} | "
                    f"Shiny Value: {pokemon.shiny_value:,}"
                )

        match config["logging"]["console"]["encounter_ivs"]:
            case "verbose":
                iv_table = Table(title=f"{pokemon.species.name} IVs")
                iv_table.add_column("HP", justify="center", style=IVColour(pokemon.ivs.hp))
                iv_table.add_column("ATK", justify="center", style=IVColour(pokemon.ivs.attack))
                iv_table.add_column("DEF", justify="center", style=IVColour(pokemon.ivs.defence))
                iv_table.add_column("SPATK", justify="center", style=IVColour(pokemon.ivs.special_attack))
                iv_table.add_column("SPDEF", justify="center", style=IVColour(pokemon.ivs.special_defence))
                iv_table.add_column("SPD", justify="center", style=IVColour(pokemon.ivs.speed))
                iv_table.add_column("Total", justify="right", style=IVSumColour(pokemon.ivs.sum()))
                iv_table.add_row(
                    f"{pokemon.ivs.hp}",
                    f"{pokemon.ivs.attack}",
                    f"{pokemon.ivs.defence}",
                    f"{pokemon.ivs.special_attack}",
                    f"{pokemon.ivs.special_defence}",
                    f"{pokemon.ivs.speed}",
                    f"{pokemon.ivs.sum()}",
                )
                console.print(iv_table)
            case "basic":
                console.print(
                    f"IVs: HP: [{IVColour(pokemon.ivs.hp)}]{pokemon.ivs.hp}[/] | "
                    f"ATK: [{IVColour(pokemon.ivs.attack)}]{pokemon.ivs.attack}[/] | "
                    f"DEF: [{IVColour(pokemon.ivs.defence)}]{pokemon.ivs.defence}[/] | "
                    f"SPATK: [{IVColour(pokemon.ivs.special_attack)}]{pokemon.ivs.special_attack}[/] | "
                    f"SPDEF: [{IVColour(pokemon.ivs.special_defence)}]{pokemon.ivs.special_defence}[/] | "
                    f"SPD: [{IVColour(pokemon.ivs.speed)}]{pokemon.ivs.speed}[/] | "
                    f"Sum: [{IVSumColour(pokemon.ivs.sum())}]{pokemon.ivs.sum()}[/]"
                )

        match config["logging"]["console"]["encounter_moves"]:
            case "verbose":
                move_table = Table(title=f"{pokemon.species.name} Moves")
                move_table.add_column("Name", justify="left", width=20)
                move_table.add_column("Kind", justify="center", width=10)
                move_table.add_column("Type", justify="center", width=10)
                move_table.add_column("Power", justify="center", width=10)
                move_table.add_column("Accuracy", justify="center", width=10)
                move_table.add_column("PP", justify="center", width=5)
                for i in range(4):
                    learned_move = pokemon.move(i)
                    if learned_move is not None:
                        move = learned_move.move
                        move_table.add_row(
                            move.name,
                            move.type.kind,
                            move.type.name,
                            str(move.base_power),
                            str(move.accuracy),
                            str(learned_move.pp),
                        )
                console.print(move_table)
            case "basic":
                for i in range(4):
                    learned_move = pokemon.move(i)
                    if learned_move is not None:
                        move = learned_move.move
                        move_colour = move.type.name.lower()
                        console.print(
                            f"[{move_colour}]Move {i + 1}[/]: {move.name} | "
                            f"{move.type.kind} | "
                            f"[{move_colour}]{move.type.name}[/] | "
                            f"Pwr: {move.base_power} | "
                            f"Acc: {move.accuracy} | "
                            f"PP: {learned_move.pp}"
                        )

        match config["logging"]["console"]["statistics"]:
            case "verbose":
                stats_table = Table(title="Statistics")
                stats_table.add_column("", justify="left", width=10)
                stats_table.add_column("Phase IV Records", justify="center", width=10)
                stats_table.add_column("Phase SV Records", justify="center", width=15)
                stats_table.add_column("Phase Encounters", justify="right", width=10)
                stats_table.add_column("Phase %", justify="right", width=10)
                stats_table.add_column("Shiny Encounters", justify="right", width=10)
                stats_table.add_column("Total Encounters", justify="right", width=10)
                stats_table.add_column("Shiny Average", justify="right", width=10)

                for p in sorted(set(session_pokemon)):
                    stats_table.add_row(
                        p,
                        f"[red]{stats['pokemon'][p].get('phase_lowest_iv_sum', -1)}[/] / [green]{stats['pokemon'][p].get('phase_highest_iv_sum', -1)}",
                        f"[green]{stats['pokemon'][p].get('phase_lowest_sv', -1):,}[/] / [{SVColour(stats['pokemon'][p].get('phase_highest_sv', -1))}]{stats['pokemon'][p].get('phase_highest_sv', -1):,}",
                        f"{stats['pokemon'][p].get('phase_encounters', 0):,}",
                        f"{(stats['pokemon'][p].get('phase_encounters', 0) / stats['totals'].get('phase_encounters', 0)) * 100:0.2f}%",
                        f"{stats['pokemon'][p].get('shiny_encounters', 0):,}",
                        f"{stats['pokemon'][p].get('encounters', 0):,}",
                        f"{stats['pokemon'][p].get('shiny_average', 'N/A')}",
                    )
                stats_table.add_row(
                    "[bold yellow]Total",
                    f"[red]{stats['totals'].get('phase_lowest_iv_sum', -1)}[/] / [green]{stats['totals'].get('phase_highest_iv_sum', -1)}",
                    f"[green]{stats['totals'].get('phase_lowest_sv', -1):,}[/] / [{SVColour(stats['totals'].get('phase_highest_sv', -1))}]{stats['totals'].get('phase_highest_sv', -1):,}",
                    f"[bold yellow]{stats['totals'].get('phase_encounters', 0):,}",
                    "[bold yellow]100%",
                    f"[bold yellow]{stats['totals'].get('shiny_encounters', 0):,}",
                    f"[bold yellow]{stats['totals'].get('encounters', 0):,}",
                    f"[bold yellow]{stats['totals'].get('shiny_average', 'N/A')}",
                )
                console.print(stats_table)
            case "basic":
                console.print(
                    f"{rich_name} Phase Encounters: {stats['pokemon'][pokemon.species.name].get('phase_encounters', 0):,} | "
                    f"{rich_name} Total Encounters: {stats['pokemon'][pokemon.species.name].get('encounters', 0):,} | "
                    f"{rich_name} Shiny Encounters: {stats['pokemon'][pokemon.species.name].get('shiny_encounters', 0):,}"
                )
                console.print(
                    f"{rich_name} Phase IV Records [red]{stats['pokemon'][pokemon.species.name].get('phase_lowest_iv_sum', -1)}[/]/[green]{stats['pokemon'][pokemon.species.name].get('phase_highest_iv_sum', -1)}[/] | "
                    f"{rich_name} Phase SV Records [green]{stats['pokemon'][pokemon.species.name].get('phase_lowest_sv', -1):,}[/]/[{SVColour(stats['pokemon'][pokemon.species.name].get('phase_highest_sv', -1))}]{stats['pokemon'][pokemon.species.name].get('phase_highest_sv', -1):,}[/] | "
                    f"{rich_name} Shiny Average: {stats['pokemon'][pokemon.species.name].get('shiny_average', 'N/A')}"
                )
                console.print(
                    f"Phase Encounters: {stats['totals'].get('phase_encounters', 0):,} | "
                    f"Phase IV Records [red]{stats['totals'].get('phase_lowest_iv_sum', -1)}[/]/[green]{stats['totals'].get('phase_highest_iv_sum', -1)}[/] | "
                    f"Phase SV Records [green]{stats['totals'].get('phase_lowest_sv', -1):,}[/]/[{SVColour(stats['totals'].get('phase_highest_sv', -1))}]{stats['totals'].get('phase_highest_sv', -1):,}[/]"
                )
                console.print(
                    f"Total Shinies: {stats['totals'].get('shiny_encounters', 0):,} | "
                    f"Total Encounters: {stats['totals'].get('encounters', 0):,} | "
                    f"Total Shiny Average: {stats['totals'].get('shiny_average', 'N/A')})"
                )

        console.print(f"[yellow]Encounter rate[/]: {GetEncounterRate():,}/h")
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def LogEncounter(pokemon: Pokemon, block_list: list) -> None:
    global stats, encounter_log, encounter_timestamps, session_pokemon, session_encounters

    try:
        if not stats:  # Set up stats file if it doesn't exist
            stats = {}
        if not "pokemon" in stats:
            stats["pokemon"] = {}
        if not "totals" in stats:
            stats["totals"] = {}

        if not pokemon.species.name in stats["pokemon"]:  # Set up a Pokémon stats if first encounter
            stats["pokemon"].update({pokemon.species.name: {}})

        # Increment encounters stats
        session_pokemon.append(pokemon.species.name)
        session_pokemon = list(set(session_pokemon))
        stats["totals"]["encounters"] = stats["totals"].get("encounters", 0) + 1
        stats["totals"]["phase_encounters"] = stats["totals"].get("phase_encounters", 0) + 1

        # Update Pokémon stats
        stats["pokemon"][pokemon.species.name]["encounters"] = (
            stats["pokemon"][pokemon.species.name].get("encounters", 0) + 1
        )
        stats["pokemon"][pokemon.species.name]["phase_encounters"] = (
            stats["pokemon"][pokemon.species.name].get("phase_encounters", 0) + 1
        )
        stats["pokemon"][pokemon.species.name]["last_encounter_time_unix"] = time.time()
        stats["pokemon"][pokemon.species.name]["last_encounter_time_str"] = str(datetime.now())

        # Pokémon phase highest shiny value
        if not stats["pokemon"][pokemon.species.name].get("phase_highest_sv", None):
            stats["pokemon"][pokemon.species.name]["phase_highest_sv"] = pokemon.shiny_value
        else:
            stats["pokemon"][pokemon.species.name]["phase_highest_sv"] = max(
                pokemon.shiny_value, stats["pokemon"][pokemon.species.name].get("phase_highest_sv", -1)
            )

        # Pokémon phase lowest shiny value
        if not stats["pokemon"][pokemon.species.name].get("phase_lowest_sv", None):
            stats["pokemon"][pokemon.species.name]["phase_lowest_sv"] = pokemon.shiny_value
        else:
            stats["pokemon"][pokemon.species.name]["phase_lowest_sv"] = min(
                pokemon.shiny_value, stats["pokemon"][pokemon.species.name].get("phase_lowest_sv", 65536)
            )

        # Pokémon total lowest shiny value
        if not stats["pokemon"][pokemon.species.name].get("total_lowest_sv", None):
            stats["pokemon"][pokemon.species.name]["total_lowest_sv"] = pokemon.shiny_value
        else:
            stats["pokemon"][pokemon.species.name]["total_lowest_sv"] = min(
                pokemon.shiny_value, stats["pokemon"][pokemon.species.name].get("total_lowest_sv", 65536)
            )

        # Phase highest shiny value
        if not stats["totals"].get("phase_highest_sv", None):
            stats["totals"]["phase_highest_sv"] = pokemon.shiny_value
            stats["totals"]["phase_highest_sv_pokemon"] = pokemon.species.name
        elif pokemon.shiny_value >= stats["totals"].get("phase_highest_sv", -1):
            stats["totals"]["phase_highest_sv"] = pokemon.shiny_value
            stats["totals"]["phase_highest_sv_pokemon"] = pokemon.species.name

        # Phase lowest shiny value
        if not stats["totals"].get("phase_lowest_sv", None):
            stats["totals"]["phase_lowest_sv"] = pokemon.shiny_value
            stats["totals"]["phase_lowest_sv_pokemon"] = pokemon.species.name
        elif pokemon.shiny_value <= stats["totals"].get("phase_lowest_sv", 65536):
            stats["totals"]["phase_lowest_sv"] = pokemon.shiny_value
            stats["totals"]["phase_lowest_sv_pokemon"] = pokemon.species.name

        # Pokémon highest phase IV record
        if not stats["pokemon"][pokemon.species.name].get("phase_highest_iv_sum") or pokemon.ivs.sum() >= stats[
            "pokemon"
        ][pokemon.species.name].get("phase_highest_iv_sum", -1):
            stats["pokemon"][pokemon.species.name]["phase_highest_iv_sum"] = pokemon.ivs.sum()

        # Pokémon highest total IV record
        if pokemon.ivs.sum() >= stats["pokemon"][pokemon.species.name].get("total_highest_iv_sum", -1):
            stats["pokemon"][pokemon.species.name]["total_highest_iv_sum"] = pokemon.ivs.sum()

        # Pokémon lowest phase IV record
        if not stats["pokemon"][pokemon.species.name].get("phase_lowest_iv_sum") or pokemon.ivs.sum() <= stats[
            "pokemon"
        ][pokemon.species.name].get("phase_lowest_iv_sum", 999):
            stats["pokemon"][pokemon.species.name]["phase_lowest_iv_sum"] = pokemon.ivs.sum()

        # Pokémon lowest total IV record
        if pokemon.ivs.sum() <= stats["pokemon"][pokemon.species.name].get("total_lowest_iv_sum", 999):
            stats["pokemon"][pokemon.species.name]["total_lowest_iv_sum"] = pokemon.ivs.sum()

        # Phase highest IV sum record
        if not stats["totals"].get("phase_highest_iv_sum") or pokemon.ivs.sum() >= stats["totals"].get(
            "phase_highest_iv_sum", -1
        ):
            stats["totals"]["phase_highest_iv_sum"] = pokemon.ivs.sum()
            stats["totals"]["phase_highest_iv_sum_pokemon"] = pokemon.species.name

        # Phase lowest IV sum record
        if not stats["totals"].get("phase_lowest_iv_sum") or pokemon.ivs.sum() <= stats["totals"].get(
            "phase_lowest_iv_sum", 999
        ):
            stats["totals"]["phase_lowest_iv_sum"] = pokemon.ivs.sum()
            stats["totals"]["phase_lowest_iv_sum_pokemon"] = pokemon.species.name

        # Total highest IV sum record
        if pokemon.ivs.sum() >= stats["totals"].get("highest_iv_sum", -1):
            stats["totals"]["highest_iv_sum"] = pokemon.ivs.sum()
            stats["totals"]["highest_iv_sum_pokemon"] = pokemon.species.name

        # Total lowest IV sum record
        if pokemon.ivs.sum() <= stats["totals"].get("lowest_iv_sum", 999):
            stats["totals"]["lowest_iv_sum"] = pokemon.ivs.sum()
            stats["totals"]["lowest_iv_sum_pokemon"] = pokemon.species.name

        pokemon_json = pokemon.to_json()
        if config["logging"]["log_encounters"]:
            # Log all encounters to a CSV file per phase
            csvpath = f"{stats_dir}/encounters/"
            csvfile = f"Phase {stats['totals'].get('shiny_encounters', 0)} Encounters.csv"
            pd_pokemon = (
                pd.DataFrame.from_dict(FlattenData(pokemon_json), orient="index")
                .drop(
                    [
                        "EVs_attack",
                        "EVs_defence",
                        "EVs_hp",
                        "EVs_spAttack",
                        "EVs_spDefense",
                        "EVs_speed",
                        "markings_circle",
                        "markings_heart",
                        "markings_square",
                        "markings_triangle",
                        "moves_0_effect",
                        "moves_1_effect",
                        "moves_2_effect",
                        "moves_3_effect",
                        "pokerus_days",
                        "pokerus_strain",
                        "status_badPoison",
                        "status_burn",
                        "status_freeze",
                        "status_paralysis",
                        "status_poison",
                        "status_sleep",
                        "condition_beauty",
                        "condition_cool",
                        "condition_cute",
                        "condition_feel",
                        "condition_smart",
                        "condition_tough",
                    ],
                    errors="ignore",
                )
                .sort_index()
                .transpose()
            )
            os.makedirs(csvpath, exist_ok=True)
            header = False if os.path.exists(f"{csvpath}{csvfile}") else True
            pd_pokemon.to_csv(f"{csvpath}{csvfile}", mode="a", encoding="utf-8", index=False, header=header)

        # Pokémon shiny average
        if stats["pokemon"][pokemon.species.name].get("shiny_encounters"):
            avg = int(
                math.floor(
                    stats["pokemon"][pokemon.species.name]["encounters"]
                    / stats["pokemon"][pokemon.species.name]["shiny_encounters"]
                )
            )
            stats["pokemon"][pokemon.species.name]["shiny_average"] = f"1/{avg:,}"

        # Total shiny average
        if stats["totals"].get("shiny_encounters"):
            avg = int(math.floor(stats["totals"]["encounters"] / stats["totals"]["shiny_encounters"]))
            stats["totals"]["shiny_average"] = f"1/{avg:,}"

        # Log encounter to encounter_log
        log_obj = {
            "time_encountered": time.time(),
            "pokemon": pokemon_json,
            "snapshot_stats": {
                "phase_encounters": stats["totals"]["phase_encounters"],
                "species_encounters": stats["pokemon"][pokemon.species.name]["encounters"],
                "species_shiny_encounters": stats["pokemon"][pokemon.species.name].get("shiny_encounters", 0),
                "total_encounters": stats["totals"]["encounters"],
                "total_shiny_encounters": stats["totals"].get("shiny_encounters", 0),
            },
        }

        encounter_timestamps.append(time.time())
        if len(encounter_timestamps) > 100:
            encounter_timestamps = encounter_timestamps[-100:]

        encounter_log.append(log_obj)
        if len(encounter_log) > 10:
            encounter_log = encounter_log[-10:]

        if pokemon.is_shiny:
            shiny_log["shiny_log"].append(log_obj)
            WriteFile(files["shiny_log"], json.dumps(shiny_log, indent=4, sort_keys=True))

        # Same Pokémon encounter streak records
        if len(encounter_log) > 1 and encounter_log[-2]["pokemon"]["name"] == pokemon.species.name:
            stats["totals"]["current_streak"] = stats["totals"].get("current_streak", 0) + 1
        else:
            stats["totals"]["current_streak"] = 1
        if stats["totals"].get("current_streak", 0) >= stats["totals"].get("phase_streak", 0):
            stats["totals"]["phase_streak"] = stats["totals"].get("current_streak", 0)
            stats["totals"]["phase_streak_pokemon"] = pokemon.species.name

        if pokemon.is_shiny:
            stats["pokemon"][pokemon.species.name]["shiny_encounters"] = (
                stats["pokemon"][pokemon.species.name].get("shiny_encounters", 0) + 1
            )
            stats["totals"]["shiny_encounters"] = stats["totals"].get("shiny_encounters", 0) + 1

        PrintStats(pokemon)

        if pokemon.is_shiny:
            #  TODO fix all this OBS crap
            for i in range(config["obs"].get("shiny_delay", 1)):
                GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)

        if config["obs"]["screenshot"] and pokemon.is_shiny:
            from modules.OBS import OBSHotKey

            while GetGameState() != GameState.BATTLE:
                GetEmulator().PressButton("B")  # Throw out Pokémon for screenshot
                GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
            for i in range(180):
                GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
            OBSHotKey("OBS_KEY_F11", pressCtrl=True)

        # Run custom code in CustomHooks in a thread
        hook = (Pokemon(pokemon.data), copy.deepcopy(stats), copy.deepcopy(block_list))
        Thread(target=CustomHooks, args=(hook,)).start()

        if pokemon.is_shiny:
            # Total longest phase
            if stats["totals"]["phase_encounters"] > stats["totals"].get("longest_phase_encounters", 0):
                stats["totals"]["longest_phase_encounters"] = stats["totals"]["phase_encounters"]
                stats["totals"]["longest_phase_pokemon"] = pokemon.species.name

            # Total shortest phase
            if (
                not stats["totals"].get("shortest_phase_encounters", None)
                or stats["totals"]["phase_encounters"] <= stats["totals"]["shortest_phase_encounters"]
            ):
                stats["totals"]["shortest_phase_encounters"] = stats["totals"]["phase_encounters"]
                stats["totals"]["shortest_phase_pokemon"] = pokemon.species.name

            # Reset phase stats
            session_pokemon = []
            stats["totals"].pop("phase_encounters", None)
            stats["totals"].pop("phase_highest_sv", None)
            stats["totals"].pop("phase_highest_sv_pokemon", None)
            stats["totals"].pop("phase_lowest_sv", None)
            stats["totals"].pop("phase_lowest_sv_pokemon", None)
            stats["totals"].pop("phase_highest_iv_sum", None)
            stats["totals"].pop("phase_highest_iv_sum_pokemon", None)
            stats["totals"].pop("phase_lowest_iv_sum", None)
            stats["totals"].pop("phase_lowest_iv_sum_pokemon", None)
            stats["totals"].pop("current_streak", None)
            stats["totals"].pop("phase_streak", None)
            stats["totals"].pop("phase_streak_pokemon", None)

            # Reset Pokémon phase stats
            for n in stats["pokemon"]:
                stats["pokemon"][n].pop("phase_encounters", None)
                stats["pokemon"][n].pop("phase_highest_sv", None)
                stats["pokemon"][n].pop("phase_lowest_sv", None)
                stats["pokemon"][n].pop("phase_highest_iv_sum", None)
                stats["pokemon"][n].pop("phase_lowest_iv_sum", None)

        # Save stats file
        WriteFile(files["totals"], json.dumps(stats, indent=4, sort_keys=True))
        session_encounters += 1

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


dirsafe_chars = f"-_.() {string.ascii_letters}{string.digits}"


def EncounterPokemon(pokemon: Pokemon) -> None:
    """
    Call when a Pokémon is encountered, decides whether to battle, flee or catch.
    Expects the trainer's state to be MISC_MENU (battle started, no longer in the overworld).

    :return:
    """

    global block_list
    if pokemon.is_shiny or block_list == []:
        # Load catch block config file - allows for editing while bot is running
        from modules.Config import catch_block_schema, LoadConfig

        config_catch_block = LoadConfig("catch_block.yml", catch_block_schema)
        block_list = config_catch_block["block_list"]

    LogEncounter(pokemon, block_list)
    SetMessage(f"Encountered a {pokemon.species.name} with a shiny value of {pokemon.shiny_value:,}!")

    # TODO temporary until auto-catch is ready
    custom_found = CustomCatchFilters(pokemon)
    if pokemon.is_shiny or custom_found:
        if pokemon.is_shiny:
            state_tag = "shiny"
            console.print("[bold yellow]Shiny found!")
            SetMessage("Shiny found! Bot has been switched to manual mode so you can catch it.")
        elif custom_found:
            state_tag = "customfilter"
            console.print("[bold green]Custom filter Pokemon found!")
            SetMessage("Custom filter triggered! Bot has been switched to manual mode so you can catch it.")
        else:
            state_tag = ""

        if not custom_found and pokemon.species.name in block_list:
            console.print("[bold yellow]" + pokemon.species.name + " is on the catch block list, skipping encounter...")
        else:
            filename_suffix = f"{state_tag}_{pokemon.species.name}"
            filename_suffix = "".join(c for c in filename_suffix if c in dirsafe_chars)
            GetEmulator().CreateSaveState(suffix=filename_suffix)

            ForceManualMode()
