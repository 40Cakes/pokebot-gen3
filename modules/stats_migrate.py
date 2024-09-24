import csv
import json
import os
import struct
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Iterable
from zipfile import ZipFile
from zoneinfo import ZoneInfo

import numpy
from rich.progress import Progress

from modules.battle_state import BattleOutcome
from modules.console import console
from modules.context import context
from modules.game import encode_string
from modules.player import get_player
from modules.pokemon import (
    get_species_by_name,
    get_species_by_index,
    StatsValues,
    ContestConditions,
    get_nature_by_index,
    LOCATION_MAP,
    POKEMON_DATA_SUBSTRUCTS_ORDER,
    Pokemon,
    Species,
)
from modules.profiles import Profile
from modules.stats import EncounterSummary, Encounter, ShinyPhase


def migrate_file_based_stats_to_sqlite(
    profile: Profile,
    insert_encounter: Callable[[Encounter], None],
    insert_shiny_phase: Callable[[ShinyPhase], None],
    update_shiny_phase: Callable[[ShinyPhase], None],
    insert_encounter_summary: Callable[[EncounterSummary], None],
    get_encounter_summaries: Callable[[], dict[int, EncounterSummary]],
    query_encounters: Callable[..., Iterable[Encounter]],
    query_shiny_phases: Callable[..., Iterable[ShinyPhase]],
    execute_statement: Callable[[str, any], any],
    commit: Callable[[], None],
):
    console.print("\n[bold green]Migrating old file-based stats to the new database format.[/]", end="")
    console.print("\n==========================================================\n\n", end="")
    console.print("This could take a while, depending on the size of your profile.\n\n", end="")

    with Progress() as progress:

        start_time = datetime.now()

        def get_encounters():
            encounters_from_shiny_log = []
            if (profile.path / "stats" / "shiny_log.json").exists():
                encounters_from_shiny_log = list(_get_encounters_from_shiny_log(profile))
                encounters_from_shiny_log.sort(key=lambda e: e.encounter_time)

            if (profile.path / "stats" / "encounters" / "_old.zip").exists():
                task = progress.add_task("[yellow]Importing encounters from `_old.zip`...", total=None)
                n = 0
                for e in _get_encounters_from_old_zip(profile):
                    while (
                        len(encounters_from_shiny_log) > 0
                        and e.encounter_time > encounters_from_shiny_log[0].encounter_time
                    ):
                        yield encounters_from_shiny_log[0]
                        del encounters_from_shiny_log[0]
                    yield e
                    n += 1
                    if n % 50 == 0:
                        progress.update(
                            task, advance=1, description=f"[yellow]Importing encounters from `_old.zip`...[/] ({n})"
                        )
                progress.update(
                    task, completed=True, description=f"[yellow]Importing encounters from `_old.zip`...[/] ({n})"
                )
                progress.stop_task(task)
            if len(list((profile.path / "stats" / "encounters").glob("*.csv"))) > 0:
                task = progress.add_task("[yellow]Importing encounters from Phase CSV files...", total=None)
                n = 0
                for e in _get_encounters_from_phase_csvs(profile):
                    while (
                        len(encounters_from_shiny_log) > 0
                        and e.encounter_time > encounters_from_shiny_log[0].encounter_time
                    ):
                        yield encounters_from_shiny_log[0]
                        del encounters_from_shiny_log[0]
                    yield e
                    n += 1
                    if n % 50 == 0:
                        progress.update(
                            task,
                            advance=1,
                            description=f"[yellow]Importing encounters from Phase CSV files...[/] ({n})",
                        )
                progress.update(
                    task, completed=True, description=f"[yellow]Importing encounters from Phase CSV files...[/] ({n})"
                )
                progress.stop_task(task)

            yield from encounters_from_shiny_log

        current_shiny_phase: ShinyPhase | None = None
        encounter_summaries: dict[int, EncounterSummary] = {}
        next_encounter_id = 1
        next_shiny_phase_id = 1
        known_personality_values: set[int] = set()

        for encounter in get_encounters():
            if encounter.pokemon.personality_value in known_personality_values:
                continue
            known_personality_values.add(encounter.pokemon.personality_value)

            encounter.encounter_time = datetime.fromtimestamp(encounter.encounter_time.timestamp(), tz=ZoneInfo("UTC"))

            if current_shiny_phase is None:
                current_shiny_phase = ShinyPhase(next_shiny_phase_id, encounter.encounter_time)
                next_shiny_phase_id += 1
                insert_shiny_phase(current_shiny_phase)
                commit()

            encounter.encounter_id = next_encounter_id
            encounter.shiny_phase_id = current_shiny_phase.shiny_phase_id
            insert_encounter(encounter)
            current_shiny_phase.update(encounter)

            if encounter.is_shiny:
                current_shiny_phase.update_snapshot(encounter_summaries)
                update_shiny_phase(current_shiny_phase)
                execute_statement(
                    "UPDATE shiny_phases SET end_time = ?, shiny_encounter_id = ? WHERE shiny_phase_id = ?",
                    (encounter.encounter_time, encounter.encounter_id, current_shiny_phase.shiny_phase_id),
                )
                current_shiny_phase = None
                commit()
                for species_id in encounter_summaries:
                    encounter_summaries[species_id].phase_encounters = 0
                    encounter_summaries[species_id].phase_highest_iv_sum = None
                    encounter_summaries[species_id].phase_lowest_iv_sum = None
                    encounter_summaries[species_id].phase_highest_sv = None
                    encounter_summaries[species_id].phase_lowest_sv = None

            if encounter.species_id not in encounter_summaries:
                encounter_summaries[encounter.species_id] = EncounterSummary.create(encounter)
            else:
                encounter_summaries[encounter.species_id].update(encounter)

            next_encounter_id += 1

        for species_id in encounter_summaries:
            insert_encounter_summary(encounter_summaries[species_id])

        if current_shiny_phase is not None:
            update_shiny_phase(current_shiny_phase)

        commit()

        # If there is a totals file, replace existing encounter summaries with that
        # as it is likely more reliable than the encounter list (which may be incomplete.)
        if (profile.path / "stats" / "totals.json").exists():
            totals = json.load((profile.path / "stats" / "totals.json").open("r"))
            encounter_summaries = get_encounter_summaries()

            def xmin(a: int | None, b: int | None) -> int | None:
                if a is None and b is None:
                    return None
                elif a is None:
                    return b
                elif b is None:
                    return a
                else:
                    return min(a, b)

            def xmax(a: int | None, b: int | None) -> int | None:
                if a is None and b is None:
                    return None
                elif a is None:
                    return b
                elif b is None:
                    return a
                else:
                    return max(a, b)

            for species_name in totals["pokemon"]:
                entry = totals["pokemon"][species_name]
                species = get_species_by_name(species_name)
                last_encounter_time = datetime.fromtimestamp(entry["last_encounter_time_unix"], tz=ZoneInfo("UTC"))
                if species.index not in encounter_summaries:
                    if "shiny_encounters" in entry and entry["shiny_encounters"] is not None:
                        shiny_encounters = entry["shiny_encounters"]
                    else:
                        shiny_encounters = 0
                    summary = EncounterSummary(
                        species=species,
                        total_encounters=entry["encounters"],
                        shiny_encounters=shiny_encounters,
                        catches=shiny_encounters,
                        total_highest_iv_sum=entry["total_highest_iv_sum"],
                        total_lowest_iv_sum=entry["total_lowest_iv_sum"],
                        total_highest_sv=entry["total_lowest_sv"],
                        total_lowest_sv=(
                            entry["phase_highest_sv"]
                            if entry["phase_highest_sv"] is not None
                            else entry["total_lowest_sv"]
                        ),
                        phase_encounters=entry["phase_encounters"],
                        phase_highest_iv_sum=entry["phase_highest_iv_sum"],
                        phase_lowest_iv_sum=entry["phase_lowest_iv_sum"],
                        phase_highest_sv=entry["phase_highest_sv"],
                        phase_lowest_sv=entry["phase_lowest_sv"],
                        last_encounter_time=last_encounter_time,
                    )
                else:
                    summary = encounter_summaries[species.index]
                    summary.total_encounters = max(summary.total_encounters, entry["encounters"])
                    summary.shiny_encounters = max(summary.shiny_encounters, entry["shiny_encounters"])
                    summary.catches = max(summary.catches, entry["shiny_encounters"])
                    summary.total_highest_iv_sum = max(summary.total_highest_iv_sum, entry["total_highest_iv_sum"])
                    summary.total_lowest_iv_sum = min(summary.total_lowest_iv_sum, entry["total_lowest_iv_sum"])
                    summary.total_highest_sv = max(
                        summary.total_highest_sv,
                        (
                            entry["phase_highest_sv"]
                            if entry["phase_highest_sv"] is not None
                            else entry["total_lowest_sv"]
                        ),
                    )
                    summary.total_lowest_sv = min(summary.total_lowest_sv, entry["total_lowest_sv"])
                    summary.phase_encounters = max(summary.phase_encounters, entry["phase_encounters"])
                    summary.phase_highest_iv_sum = xmax(summary.phase_highest_iv_sum, entry["phase_highest_iv_sum"])
                    summary.phase_lowest_iv_sum = xmin(summary.phase_lowest_iv_sum, entry["phase_lowest_iv_sum"])
                    summary.phase_highest_sv = xmax(summary.phase_highest_sv, entry["phase_highest_sv"])
                    summary.phase_lowest_sv = xmin(summary.phase_lowest_sv, entry["phase_lowest_sv"])
                    summary.last_encounter_time = max(summary.last_encounter_time, last_encounter_time)

                insert_encounter_summary(summary)

        # If there is a shiny log, use that as a more reliable source for stats
        if (profile.path / "stats" / "shiny_log.json").exists():
            shiny_log = json.load((profile.path / "stats" / "shiny_log.json").open("r"))
            for entry in shiny_log["shiny_log"]:
                # For some reason, there are non-shiny entries in the stream profile's shiny log.
                shiny_value = (
                    entry["pokemon"]["ot"]["tid"]
                    ^ entry["pokemon"]["ot"]["sid"]
                    ^ (entry["pokemon"]["pid"] & 0xFFFF)
                    ^ (entry["pokemon"]["pid"] >> 16)
                )
                if shiny_value >= 8:
                    continue

                encounter_time = datetime.fromtimestamp(int(entry["time_encountered"]), tz=ZoneInfo("UTC"))

                shiny_phases = list(
                    query_shiny_phases("encounters.personality_value = ?", (entry["pokemon"]["pid"],), 1)
                )
                execute_statement(
                    "UPDATE shiny_phases SET start_time = ?, end_time = ?, encounters = ?, snapshot_total_encounters = ?, snapshot_total_shiny_encounters = ?, snapshot_species_encounters = ?, snapshot_species_shiny_encounters = ? WHERE shiny_phase_id = ?",
                    (
                        min(encounter_time, shiny_phases[0].start_time),
                        encounter_time,
                        entry["snapshot_stats"]["phase_encounters"],
                        entry["snapshot_stats"]["total_encounters"],
                        entry["snapshot_stats"]["total_shiny_encounters"],
                        entry["snapshot_stats"]["species_encounters"],
                        entry["snapshot_stats"]["species_shiny_encounters"],
                        shiny_phases[0].shiny_phase_id,
                    ),
                )

            # mGBA CSV files do not contain timestamps, so we've been guessing them
            # based on the creation time of the CSV file. Try to fix it even more.
            all_shiny_phases: dict[int, ShinyPhase] = {}
            for shiny_phase in query_shiny_phases(None, limit=None):
                all_shiny_phases[shiny_phase.shiny_phase_id] = shiny_phase

            shiny_phase: ShinyPhase | None = None
            time_offset: datetime
            update_statements = []
            for encounter in query_encounters("bot_mode = 'Imported from Phase CSV (mGBA)'", limit=None):
                if shiny_phase is None or shiny_phase.shiny_phase_id != encounter.shiny_phase_id:
                    shiny_phase = all_shiny_phases[encounter.shiny_phase_id]
                    if shiny_phase.end_time:
                        time_offset = shiny_phase.end_time
                    else:
                        time_offset = datetime.now(tz=ZoneInfo("UTC"))

                if (
                    shiny_phase.shiny_encounter is not None
                    and encounter.encounter_id == shiny_phase.shiny_encounter.encounter_id
                ):
                    new_time = shiny_phase.end_time
                else:
                    time_offset -= timedelta(seconds=13)
                    new_time = time_offset

                update_statements.append(
                    (
                        "UPDATE encounters SET encounter_time = ? WHERE encounter_id = ?",
                        (new_time, encounter.encounter_id),
                    )
                )

            for statement in update_statements:
                execute_statement(*statement)

        commit()

    execute_statement("VACUUM;", ())

    console.print("\n[green]Done![/]")

    duration = int(datetime.now().timestamp() - start_time.timestamp())
    if duration < 60:
        duration = f"[bold cyan]{duration}[/] seconds"
    elif duration < 3600:
        duration = f"[bold cyan]{duration // 60:02d}:{duration % 60:02d}[/] minutes"
    else:
        duration = f"[bold cyan]{duration // 3600}:{(duration % 3600) // 60:02d}:{duration % 60:02d} hours[/]"
    console.print(f"This took only {duration}.\n")


def _get_encounters_from_old_zip(profile: Profile):
    timezone = ZoneInfo("Australia/Sydney")
    with ZipFile(profile.path / "stats" / "encounters" / "_old.zip") as zip_file:
        list_of_files: list[tuple[str, datetime]] = []
        for file_entry in zip_file.infolist():
            if not file_entry.is_dir():
                list_of_files.append((file_entry.filename, datetime(*file_entry.date_time, tzinfo=timezone)))

        list_of_files.sort(key=lambda e: e[1])

        for file_path, timestamp in list_of_files:
            with zip_file.open(file_path) as encounter_file:
                file_contents = json.loads(encounter_file.read())

            pokemon = _map_old_zip_json_to_pokemon_data(file_contents)
            yield Encounter(
                encounter_id=0,
                shiny_phase_id=0,
                matching_custom_catch_filters=None,
                encounter_time=timestamp,
                map=None,
                coordinates=None,
                bot_mode="Imported from Old ZIP",
                type=None,
                outcome=BattleOutcome.Caught if pokemon.is_shiny else BattleOutcome.RanAway,
                pokemon=pokemon,
            )


def _get_encounters_from_phase_csvs(profile: Profile):
    csv_files = sorted((profile.path / "stats" / "encounters").glob("*.csv"), key=os.path.basename)
    timezone = ZoneInfo("Australia/Sydney")
    for file_path in csv_files:
        with file_path.open("r") as file:

            def read_csv_lines() -> dict:
                # print(os.path.basename(file.name))
                # Workaround for issues with some files in the stream profile, where the
                # format changes mid-file or some lines contain some extra columns that should
                # not be there.
                problematic_files = [
                    "Phase 125 Encounters.csv",
                    "Phase 169 Encounters.csv",
                    "Phase 169 Encounters.csv",
                    "Phase 172 Encounters.csv",
                    "Phase 177 Encounters.csv",
                    "Phase 183 Encounters.csv",
                    "Phase 184 Encounters.csv",
                    "Phase 185 Encounters.csv",
                    "Phase 188 Encounters.csv",
                    "Phase 201 Encounters.csv",
                    "Phase 203 Encounters.csv",
                    "Phase 204 Encounters.csv",
                    "Phase 207 Encounters.csv",
                    "Phase 235 Encounters.csv",
                    "Phase 242 Encounters.csv",
                    "Phase 249 Encounters.csv",
                    "Phase 251 Encounters.csv",
                    "Phase 256 Encounters.csv",
                    "Phase 265 Encounters.csv",
                    "Phase 269 Encounters.csv",
                    "Phase 271 Encounters.csv",
                    "Phase 289 Encounters.csv",
                    "Phase 302 Encounters.csv",
                    "Phase 461 Encounters.csv",
                    "Phase 462 Encounters.csv",
                    "Phase 462 Encounters.csv",
                    "Phase 464 Encounters.csv",
                ]

                if os.path.basename(file.name) in problematic_files:
                    csv_reader = csv.reader(file)
                    phase_number = int(os.path.basename(file.name)[6:9])
                    usual_field_list = next(csv_reader)
                    usual_field_count = len(usual_field_list)
                    for fields in csv_reader:
                        if len(fields) != usual_field_count:
                            if phase_number == 125:
                                new_fields = [*fields[0:57], "", *fields[57:]]
                            elif phase_number == 169:
                                new_fields = [*fields[0:43], *fields[44:]]
                                new_fields[11] = 70
                                new_fields[16] = 0
                            elif phase_number == 172:
                                if fields[1] == "Shield Dust":
                                    new_fields = [*fields[0:23], *fields[24:]]
                                    new_fields[11] = 70
                                    new_fields[16] = 0
                                else:
                                    new_fields = fields[1:]
                            elif phase_number == 177:
                                new_fields = [*fields[0:12], *fields[13:]]
                                new_fields[11] = 70
                            elif phase_number == 183:
                                new_fields = [*fields[0:18], *fields[19:]]
                                new_fields[16] = 0
                            elif phase_number == 184:
                                if fields[1] == "Shield Dust":
                                    new_fields = [*fields[0:3], *fields[4:]]
                                else:
                                    new_fields = [*fields[0:53], *fields[54:]]
                            elif phase_number == 185:
                                new_fields = [*fields[0:16], *fields[17:]]
                            elif phase_number == 188:
                                if fields[1] == "Shield Dust":
                                    new_fields = [*fields[0:47], 0, *fields[49:]]
                                else:
                                    new_fields = [*fields[0:11], *fields[12:]]
                            elif phase_number == 201:
                                new_fields = [*fields[0:19], *fields[20:]]
                            elif phase_number == 203:
                                new_fields = [*fields[0:43], *fields[44:]]
                            elif phase_number == 204:
                                new_fields = [*fields[0:53], *fields[54:]]
                            elif phase_number == 207:
                                if int(fields[0]) == 122:
                                    new_fields = [*fields[0:16], *fields[17:]]
                                else:
                                    new_fields = [*fields[0:44], *fields[45:]]
                            elif phase_number == 235:
                                new_fields = [*fields[0:21], *fields[22:]]
                            elif phase_number == 242:
                                new_fields = [*fields[0:39], *fields[40:]]
                            elif phase_number == 249:
                                new_fields = [*fields[0:6], *fields[7:]]
                            elif phase_number == 251:
                                new_fields = [*fields[0:23], *fields[24:]]
                            elif phase_number == 256:
                                new_fields = [*fields[0:16], *fields[17:]]
                            elif phase_number == 265:
                                new_fields = [*fields[0:61], *fields[62:]]
                            elif phase_number == 269:
                                new_fields = [*fields[0:43], *fields[44:]]
                            elif phase_number == 271:
                                if fields[1] == "Synchronize":
                                    new_fields = [*fields[0:6], *fields[7:]]
                                else:
                                    new_fields = [*fields[0:55], *fields[56:]]
                            elif phase_number == 289:
                                new_fields = [*fields[0:7], *fields[8:]]
                            elif phase_number == 302:
                                new_fields = [*fields[0:10], *fields[11:]]
                            elif phase_number == 461:
                                new_fields = [*fields[0:48], *fields[49:]]
                            elif phase_number == 462:
                                if int(fields[0]) == 131:
                                    new_fields = [*fields[0:32], *fields[33:]]
                                else:
                                    new_fields = [*fields[0:3], *fields[4:]]
                            elif phase_number == 464:
                                new_fields = [*fields[0:55], *fields[56:]]
                            else:
                                new_fields = fields
                            yield {usual_field_list[i]: new_fields[i] for i in range(usual_field_count)}
                        else:
                            yield {usual_field_list[i]: fields[i] for i in range(usual_field_count)}
                else:
                    yield from csv.DictReader(file)

            n = 0
            for row in read_csv_lines():
                if "IVs_attack" not in row:
                    bot_backend = "Bizhawk"
                    pokemon = _map_bizhawk_csv_row_to_pokemon_data(row)
                    date = row["date"].split("-")
                    time = row["time"].split(":")
                    timestamp = datetime(
                        int(date[0]),
                        int(date[1]),
                        int(date[2]),
                        int(time[0]),
                        int(time[1]),
                        int(time[2]),
                        tzinfo=timezone,
                    )
                else:
                    # The mGBA version's CSV file does not contain any timestamps, so we need
                    # to make some educated guesses based on the creation time of the CSV file
                    # and the encounter number therein... at 277 encounters/hr that would be one
                    # encounter about every 13 seconds, so we add that to the creation time.
                    bot_backend = "mGBA"
                    pokemon = _map_mgba_csv_row_to_pokemon_data(row)
                    timestamp = datetime.fromtimestamp(os.path.getctime(file_path), tz=ZoneInfo("UTC"))
                    timestamp += timedelta(seconds=13 * n)
                    n += 1
                if pokemon is None:
                    continue

                yield Encounter(
                    encounter_id=0,
                    shiny_phase_id=0,
                    matching_custom_catch_filters=None,
                    encounter_time=timestamp,
                    map=None,
                    coordinates=None,
                    bot_mode=f"Imported from Phase CSV ({bot_backend})",
                    type=None,
                    outcome=BattleOutcome.Caught if pokemon.is_shiny else BattleOutcome.RanAway,
                    pokemon=pokemon,
                )


def _get_encounters_from_shiny_log(profile: Profile):
    shiny_log = json.load((profile.path / "stats" / "shiny_log.json").open("r"))
    for entry in shiny_log["shiny_log"]:
        pokemon = _map_shiny_log_json_to_pokemon_data(entry["pokemon"])
        yield Encounter(
            encounter_id=0,
            shiny_phase_id=0,
            matching_custom_catch_filters=None,
            encounter_time=datetime.fromtimestamp(entry["time_encountered"], tz=ZoneInfo("UTC")),
            map=None,
            coordinates=None,
            bot_mode="Imported from Shiny Log",
            type=None,
            outcome=BattleOutcome.Caught,
            pokemon=pokemon,
        )


def _map_shiny_log_json_to_pokemon_data(pkm: dict) -> Pokemon:
    if "species" in pkm:
        species = get_species_by_index(pkm["species"])
    elif "name" in pkm:
        species = get_species_by_name(pkm["name"])
    else:
        raise RuntimeError("Cannot figure out species for Shiny encounter.")

    origin_language = 2
    if pkm["language"] == "J":
        origin_language = 1
    elif pkm["language"] == "F":
        origin_language = 3
    elif pkm["language"] == "I":
        origin_language = 4
    elif pkm["language"] == "G":
        origin_language = 5
    elif pkm["language"] == "S":
        origin_language = 7

    if "origins" in pkm:
        met_level = pkm["origins"]["metLevel"]
        if pkm["origins"]["game"] == "Ruby":
            origin_game = 1
        elif pkm["origins"]["game"] == "Sapphire":
            origin_game = 2
        elif pkm["origins"]["game"] == "FireRed":
            origin_game = 4
        elif pkm["origins"]["game"] == "LeafGreen":
            origin_game = 5
        else:
            origin_game = 3
    else:
        met_level = pkm["level"]
        if context.rom.is_ruby:
            origin_game = 1
        elif context.rom.is_sapphire:
            origin_game = 2
        elif context.rom.is_fr:
            origin_game = 4
        elif context.rom.is_lg:
            origin_game = 5
        else:
            origin_game = 3

    ivs = StatsValues(
        hp=pkm["IVs"]["hp"],
        attack=pkm["IVs"]["attack"],
        defence=pkm["IVs"]["defense"],
        speed=pkm["IVs"]["speed"],
        special_attack=pkm["IVs"]["spAttack"],
        special_defence=pkm["IVs"]["spDefense"],
    )

    has_second_ability = pkm["ability"] != species.abilities[0].name

    if "item" in pkm:
        held_item_id = pkm["item"]["id"]
    else:
        held_item_id = 0

    if "EVs" in pkm:
        evs = StatsValues(
            hp=pkm["EVs"]["hp"],
            attack=pkm["EVs"]["attack"],
            defence=pkm["EVs"]["defence"],
            speed=pkm["EVs"]["speed"],
            special_attack=pkm["EVs"]["spAttack"],
            special_defence=pkm["EVs"]["spDefense"],
        )
    else:
        evs = StatsValues(0, 0, 0, 0, 0, 0)

    if "condition" in pkm:
        conditions = ContestConditions(
            coolness=pkm["condition"]["cool"],
            beauty=pkm["condition"]["beauty"],
            cuteness=pkm["condition"]["cute"],
            smartness=pkm["condition"]["smart"],
            toughness=pkm["condition"]["tough"],
            feel=pkm["condition"]["feel"],
        )
    else:
        conditions = ContestConditions(0, 0, 0, 0, 0, 0)

    if "metLocation" in pkm:
        met_location = pkm["metLocation"]
    else:
        met_location = "Fateful Encounter"

    if "stats" in pkm:
        stats = StatsValues(
            hp=pkm["stats"]["maxHP"],
            attack=pkm["stats"]["attack"],
            defence=pkm["stats"]["defense"],
            speed=pkm["stats"]["speed"],
            special_attack=pkm["stats"]["spAttack"],
            special_defence=pkm["stats"]["spDefense"],
        )
    else:
        nature = get_nature_by_index(pkm["pid"] % 25)
        stats = StatsValues.calculate(species, ivs, evs, nature, pkm["level"])

    if "moves" in pkm:
        moves = pkm["moves"]
    else:
        moves = [
            {"id": 0, "remaining_pp": 0},
            {"id": 0, "remaining_pp": 0},
            {"id": 0, "remaining_pp": 0},
            {"id": 0, "remaining_pp": 0},
        ]
        level_up_moves = list(filter(lambda m: m.level <= pkm["level"], species.learnset.level_up))
        index = 0
        for level_up_move in level_up_moves[-4:]:
            moves[index]["id"] = level_up_move.move.index
            moves[index]["remaining_pp"] = level_up_move.move.pp
            index += 1

    return _create_pokemon_data(
        pkm["pid"],
        pkm["ot"]["tid"],
        pkm["ot"]["sid"],
        species,
        pkm["level"],
        held_item_id,
        pkm["experience"],
        pkm["friendship"],
        moves,
        has_second_ability,
        stats,
        ivs,
        evs,
        conditions,
        LOCATION_MAP.index(met_location),
        met_level,
        origin_game,
        origin_language,
    )


def _map_mgba_csv_row_to_pokemon_data(pkm: dict) -> Pokemon:
    species = get_species_by_index(int(pkm["species"]))

    origin_language = 2
    if pkm["language"] == "J":
        origin_language = 1
    elif pkm["language"] == "F":
        origin_language = 3
    elif pkm["language"] == "I":
        origin_language = 4
    elif pkm["language"] == "G":
        origin_language = 5
    elif pkm["language"] == "S":
        origin_language = 7

    if pkm["origins_game"] == "Ruby":
        origin_game = 1
    elif pkm["origins_game"] == "Sapphire":
        origin_game = 2
    elif pkm["origins_game"] == "FireRed":
        origin_game = 4
    elif pkm["origins_game"] == "LeafGreen":
        origin_game = 5
    else:
        origin_game = 3

    return _create_pokemon_data(
        personality_value=int(pkm["pid"]),
        ot_trainer_id=int(pkm["ot_tid"]),
        ot_secret_id=int(pkm["ot_sid"]),
        species=species,
        level=int(pkm["level"]),
        held_item_id=int(pkm["item_id"]),
        experience=int(pkm["experience"]),
        friendship=int(pkm["friendship"]),
        moves=[
            {"id": int(pkm["moves_0_id"]), "remaining_pp": int(pkm["moves_0_pp"])},
            {"id": int(pkm["moves_1_id"]), "remaining_pp": int(pkm["moves_1_pp"])},
            {"id": int(pkm["moves_2_id"]), "remaining_pp": int(pkm["moves_2_pp"])},
            {"id": int(pkm["moves_3_id"]), "remaining_pp": int(pkm["moves_3_pp"])},
        ],
        has_second_ability=pkm["ability"] != species.abilities[0].name,
        stats=StatsValues(
            hp=int(pkm["stats_maxHP"]),
            attack=int(pkm["stats_attack"]),
            defence=int(pkm["stats_defense"]),
            speed=int(pkm["stats_speed"]),
            special_attack=int(pkm["stats_spAttack"]),
            special_defence=int(pkm["stats_spDefense"]),
        ),
        ivs=StatsValues(
            hp=int(pkm["IVs_hp"]),
            attack=int(pkm["IVs_attack"]),
            defence=int(pkm["IVs_defense"]),
            speed=int(pkm["IVs_speed"]),
            special_attack=int(pkm["IVs_spAttack"]),
            special_defence=int(pkm["IVs_spDefense"]),
        ),
        evs=StatsValues(0, 0, 0, 0, 0, 0),
        conditions=ContestConditions(0, 0, 0, 0, 0, 0),
        met_location_index=LOCATION_MAP.index(pkm["metLocation"]),
        met_level=int(pkm["origins_metLevel"]),
        origin_game=origin_game,
        origin_language=origin_language,
    )


def _map_bizhawk_csv_row_to_pokemon_data(pkm: dict) -> Pokemon | None:
    # The Bizhawk version's CSV files seem to be a bit unreliable, so we'll attempt
    # to calculate as much as we can from the Personality Value here.

    personality_value = int(pkm["personality"])
    try:
        # The Bizhawk version of the bot reported the wrong species IDs -- they are
        # always one higher than they should be.
        species = get_species_by_index(int(pkm["species"]) - 1)
    except IndexError:
        return None
    level = int(pkm["level"])

    moves = [
        {"id": 0, "remaining_pp": 0},
        {"id": 0, "remaining_pp": 0},
        {"id": 0, "remaining_pp": 0},
        {"id": 0, "remaining_pp": 0},
    ]
    level_up_moves = list(filter(lambda m: m.level <= level, species.learnset.level_up))
    index = 0
    for level_up_move in level_up_moves[-4:]:
        moves[index]["id"] = level_up_move.move.index
        moves[index]["remaining_pp"] = level_up_move.move.pp
        index += 1

    ivs = StatsValues(
        hp=int(pkm["hpIV"]) if int(pkm["hpIV"]) <= 31 else 16,
        attack=int(pkm["attackIV"]) if int(pkm["attackIV"]) <= 31 else 16,
        defence=int(pkm["defenseIV"]) if int(pkm["defenseIV"]) <= 31 else 16,
        speed=int(pkm["speedIV"]) if int(pkm["speedIV"]) <= 31 else 16,
        special_attack=int(pkm["spAttackIV"]) if int(pkm["spAttackIV"]) <= 31 else 16,
        special_defence=int(pkm["spDefenseIV"]) if int(pkm["spDefenseIV"]) <= 31 else 16,
    )

    nature = get_nature_by_index(personality_value % 25)
    stats = StatsValues.calculate(species, ivs, StatsValues(0, 0, 0, 0, 0, 0), nature, level)

    return _create_pokemon_data(
        personality_value=personality_value,
        ot_trainer_id=int(pkm["otId"]) & 0xFFFF,
        ot_secret_id=int(pkm["otId"]) >> 16,
        species=species,
        level=level,
        held_item_id=int(pkm["heldItem"]),
        experience=species.level_up_type.get_experience_needed_for_level(level),
        friendship=species.base_friendship,
        moves=moves,
        has_second_ability=int(pkm["altAbility"]) != 0,
        stats=stats,
        ivs=ivs,
        evs=StatsValues(0, 0, 0, 0, 0, 0),
        conditions=ContestConditions(0, 0, 0, 0, 0, 0),
        met_location_index=int(pkm["metLocation"]),
        met_level=int(pkm["metLevel"]),
        origin_game=int(pkm["metGame"]),
        origin_language=int(pkm["language"]),
    )


def _map_old_zip_json_to_pokemon_data(pkm: dict) -> Pokemon:
    return _create_pokemon_data(
        personality_value=pkm["personality"],
        ot_trainer_id=pkm["otId"] & 0xFFFF,
        ot_secret_id=pkm["otId"] >> 16,
        # The Bizhawk version of the bot reported the wrong species IDs -- they are
        # always one higher than they should be.
        species=get_species_by_index(pkm["species"] - 1),
        level=pkm["level"],
        held_item_id=pkm["heldItem"],
        experience=pkm["experience"],
        friendship=pkm["friendship"],
        moves=[
            {"id": pkm["moves"][0], "remaining_pp": pkm["pp"][0]},
            {"id": pkm["moves"][1], "remaining_pp": pkm["pp"][1]},
            {"id": pkm["moves"][2], "remaining_pp": pkm["pp"][2]},
            {"id": pkm["moves"][3], "remaining_pp": pkm["pp"][3]},
        ],
        has_second_ability=pkm["altAbility"] != 0,
        stats=StatsValues(
            hp=pkm["maxHP"],
            attack=pkm["attack"],
            defence=pkm["defense"],
            speed=pkm["speed"],
            special_attack=pkm["spAttack"],
            special_defence=pkm["spDefense"],
        ),
        ivs=StatsValues(
            hp=pkm["hpIV"],
            attack=pkm["attackIV"],
            defence=pkm["defenseIV"],
            speed=pkm["speedIV"],
            special_attack=pkm["spAttackIV"],
            special_defence=pkm["spDefenseIV"],
        ),
        evs=StatsValues(
            hp=pkm["hpEV"],
            attack=pkm["attackEV"],
            defence=pkm["defenseEV"],
            speed=pkm["speedEV"],
            special_attack=pkm["spAttackEV"],
            special_defence=pkm["spDefenseEV"],
        ),
        conditions=ContestConditions(
            coolness=pkm["cool"],
            beauty=pkm["beauty"],
            cuteness=pkm["cute"],
            smartness=pkm["smart"],
            toughness=pkm["tough"],
            feel=pkm["sheen"],
        ),
        met_location_index=pkm["metLocation"],
        met_level=pkm["metLevel"],
        origin_game=pkm["metGame"],
        origin_language=pkm["language"],
    )


def _create_pokemon_data(
    personality_value: int,
    ot_trainer_id: int,
    ot_secret_id: int,
    species: Species,
    level: int,
    held_item_id: int,
    experience: int,
    friendship: int,
    moves: list[dict],
    has_second_ability: bool,
    stats: StatsValues,
    ivs: StatsValues,
    evs: StatsValues,
    conditions: ContestConditions,
    met_location_index: int,
    met_level: int,
    origin_game: int,
    origin_language: int,
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

    origins_info = met_level | (origin_game << 7) | (4 << 11)
    if get_player().gender == "female":
        origins_info |= 1 << 15

    data_to_encrypt = (
        species.index.to_bytes(2, byteorder="little")
        + held_item_id.to_bytes(2, byteorder="little")
        + experience.to_bytes(4, byteorder="little")
        + b"\x00"
        + friendship.to_bytes(1)
        + b"\x00\x00"
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
        + conditions.coolness.to_bytes(1)
        + conditions.beauty.to_bytes(1)
        + conditions.cuteness.to_bytes(1)
        + conditions.smartness.to_bytes(1)
        + conditions.toughness.to_bytes(1)
        + conditions.feel.to_bytes(1)
        + b"\x00"
        + met_location_index.to_bytes(1)
        + origins_info.to_bytes(2, byteorder="little")
        + iv_egg_ability.to_bytes(4, byteorder="little")
        + b"\x00\x00\x00\x00"
    )

    data = (
        personality_value.to_bytes(length=4, byteorder="little")
        + ot_trainer_id.to_bytes(length=2, byteorder="little")
        + ot_secret_id.to_bytes(length=2, byteorder="little")
        + encode_string(species.name.upper()).ljust(10, b"\xFF")
        + origin_language.to_bytes(length=1, byteorder="little")
        + b"\x01"
        + encode_string(get_player().name).ljust(7, b"\xFF")
        + b"\x00"
        + (sum(struct.unpack("<24H", data_to_encrypt)) & 0xFFFF).to_bytes(length=2, byteorder="little")
        + b"\x00\x00"
        + data_to_encrypt
        + b"\x00\x00\x00\x00"
        + level.to_bytes(length=1, byteorder="little")
        + b"\x00"
        + stats.hp.to_bytes(length=2, byteorder="little")
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
