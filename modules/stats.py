import json
import numpy
import sqlite3
import struct
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Iterable

from modules.battle import BattleOutcome
from modules.console import print_stats
from modules.context import context
from modules.game import encode_string
from modules.player import get_player_location, get_player
from modules.pokemon import (
    Pokemon,
    get_species_by_index,
    get_species_by_name,
    LOCATION_MAP,
    POKEMON_DATA_SUBSTRUCTS_ORDER,
)

if TYPE_CHECKING:
    from modules.items import Item, get_item_by_index
    from modules.profiles import Profile


current_schema_version = 1


class StatsDatabaseSchemaTooNew(Exception):
    pass


@dataclass
class Encounter:
    encounter_id: int
    shiny_phase_id: int
    matching_custom_catch_filters: str | None
    encounter_time: datetime
    map: str | None
    coordinates: str | None
    bot_mode: str
    outcome: BattleOutcome | None
    pokemon: "Pokemon"

    @classmethod
    def from_row_data(cls, row: list | tuple) -> "Encounter":
        return Encounter(
            encounter_id=row[0],
            shiny_phase_id=row[3],
            matching_custom_catch_filters=row[6],
            encounter_time=datetime.fromisoformat(row[7]),
            map=row[8],
            coordinates=row[9],
            bot_mode=row[10],
            outcome=BattleOutcome(row[11]) if row[11] else None,
            pokemon=Pokemon(row[12]),
        )

    @property
    def species_id(self) -> int:
        return self.pokemon.species.index

    @property
    def species_name(self) -> str:
        return self.pokemon.species.name

    @property
    def is_shiny(self) -> bool:
        return self.pokemon.is_shiny

    @property
    def iv_sum(self) -> int:
        return self.pokemon.ivs.sum()

    @property
    def shiny_value(self) -> int:
        return self.pokemon.shiny_value

    @property
    def data(self) -> bytes:
        return self.pokemon.data

    def to_dict(self) -> dict:
        return {
            "encounter_id": self.encounter_id,
            "shiny_phase_id": self.shiny_phase_id,
            "matching_custom_catch_filters": self.matching_custom_catch_filters,
            "encounter_time": self.encounter_time.isoformat(),
            "map": self.map,
            "coordinates": self.coordinates,
            "bot_mode": self.bot_mode,
            "outcome": self.outcome.value if self.outcome is not None else None,
            "pokemon": self.pokemon.to_dict(),
        }


@dataclass
class ShinyPhase:
    shiny_phase_id: int
    start_time: datetime
    end_time: datetime | None = None
    shiny_encounter_id: int | None = None
    encounters: int = 0
    highest_iv_sum: int | None = None
    lowest_iv_sum: int | None = None
    highest_sv: int | None = None
    lowest_sv: int | None = None
    longest_streak: int = 0
    longest_streak_species: str | None = None
    current_streak: int = 0
    current_streak_species: str | None = None

    @classmethod
    def from_row_data(cls, row: list | tuple) -> "ShinyPhase":
        return ShinyPhase(
            row[0],
            datetime.fromisoformat(row[1]),
            datetime.fromisoformat(row[2]) if row[2] is not None else None,
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8],
            row[9],
            row[10],
        )

    @classmethod
    def create(cls, shiny_phase_id: int, start_time: datetime) -> "ShinyPhase":
        return cls(shiny_phase_id=shiny_phase_id, start_time=start_time)

    def update(self, encounter: Encounter):
        self.encounters += 1

        if self.highest_iv_sum is None or self.highest_iv_sum < encounter.iv_sum:
            self.highest_iv_sum = encounter.iv_sum

        if self.lowest_iv_sum is None or self.lowest_iv_sum > encounter.iv_sum:
            self.lowest_iv_sum = encounter.iv_sum

        if not encounter.is_shiny:
            if self.highest_sv is None or self.highest_sv < encounter.shiny_value:
                self.highest_sv = encounter.shiny_value

            if self.lowest_sv is None or self.lowest_sv > encounter.shiny_value:
                self.lowest_sv = encounter.shiny_value

        if self.current_streak_species != encounter.species_name:
            self.current_streak = 1
            self.current_streak_species = encounter.species_name
        else:
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
                self.longest_streak_species = self.current_streak_species

        if encounter.is_shiny:
            self.shiny_encounter_id = encounter.encounter_id
            self.end_time = encounter.encounter_time

    def to_dict(self, shiny_encounter: Encounter | None) -> dict:
        return {
            "phase": {
                "shiny_phase_id": self.shiny_phase_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time is not None else None,
                "encounters": self.encounters,
                "highest_iv_sum": self.highest_iv_sum,
                "lowest_iv_sum": self.lowest_iv_sum,
                "highest_sv": self.highest_sv,
                "lowest_sv": self.lowest_sv,
                "longest_streak": self.longest_streak,
                "longest_streak_species": self.longest_streak_species,
                "current_streak": self.current_streak,
                "current_streak_species": self.current_streak_species,
            },
            "shiny_encounter": shiny_encounter.to_dict() if shiny_encounter is not None else None,
        }


@dataclass
class EncounterSummary:
    species: "Species | None"
    total_encounters: int
    shiny_encounters: int
    catches: int
    total_highest_iv_sum: int
    total_lowest_iv_sum: int
    total_highest_sv: int
    total_lowest_sv: int
    phase_encounters: int
    phase_highest_iv_sum: int | None
    phase_lowest_iv_sum: int | None
    phase_highest_sv: int | None
    phase_lowest_sv: int | None
    last_encounter_time: datetime

    @classmethod
    def create(cls, encounter: Encounter) -> "EncounterSummary":
        return cls(
            species=encounter.pokemon.species,
            total_encounters=1,
            shiny_encounters=0 if not encounter.is_shiny else 1,
            catches=0,
            total_highest_iv_sum=encounter.iv_sum,
            total_lowest_iv_sum=encounter.iv_sum,
            total_highest_sv=encounter.shiny_value,
            total_lowest_sv=encounter.shiny_value,
            phase_encounters=1 if not encounter.is_shiny else 0,
            phase_highest_iv_sum=encounter.iv_sum if not encounter.is_shiny else None,
            phase_lowest_iv_sum=encounter.iv_sum if not encounter.is_shiny else None,
            phase_highest_sv=encounter.shiny_value if not encounter.is_shiny else None,
            phase_lowest_sv=encounter.shiny_value if not encounter.is_shiny else None,
            last_encounter_time=encounter.encounter_time,
        )

    @classmethod
    def create_totals(cls, encounter_summaries: dict[int, "EncounterSummary"]) -> "EncounterSummary":
        totals = cls(
            species=None,
            total_encounters=0,
            shiny_encounters=0,
            catches=0,
            total_highest_iv_sum=0,
            total_lowest_iv_sum=0,
            total_highest_sv=0,
            total_lowest_sv=0,
            phase_encounters=0,
            phase_highest_iv_sum=None,
            phase_lowest_iv_sum=None,
            phase_highest_sv=None,
            phase_lowest_sv=None,
            last_encounter_time=datetime.fromisoformat("0000-00-00T00:00:00+00:00"),
        )

        for species_id in encounter_summaries:
            encounter_summary = encounter_summaries[species_id]
            totals.total_encounters += encounter_summary.total_encounters
            totals.shiny_encounters += encounter_summary.shiny_encounters
            totals.catches += encounter_summary.catches
            totals.total_highest_iv_sum = max(totals.total_highest_iv_sum, encounter_summary.total_highest_iv_sum)
            totals.total_lowest_iv_sum = min(totals.total_lowest_iv_sum, encounter_summary.total_lowest_iv_sum)
            totals.total_highest_sv = max(totals.total_highest_sv, encounter_summary.total_highest_sv)
            totals.total_lowest_sv = min(totals.total_lowest_sv, encounter_summary.total_lowest_sv)
            totals.phase_encounters += encounter_summary.phase_encounters
            totals.phase_highest_iv_sum = max(totals.phase_highest_iv_sum, encounter_summary.phase_highest_iv_sum)
            totals.phase_lowest_iv_sum = min(totals.phase_lowest_iv_sum, encounter_summary.phase_lowest_iv_sum)
            totals.phase_highest_sv = max(totals.phase_highest_sv, encounter_summary.phase_highest_sv)
            totals.phase_lowest_sv = min(totals.phase_lowest_sv, encounter_summary.phase_lowest_sv)
            totals.last_encounter_time = max(totals.last_encounter_time, encounter_summary.last_encounter_time)

        return totals

    def update(self, encounter: Encounter):
        self.total_encounters += 1
        self.last_encounter_time = encounter.encounter_time

        if self.total_highest_iv_sum < encounter.iv_sum:
            self.total_highest_iv_sum = encounter.iv_sum

        if self.total_lowest_iv_sum > encounter.iv_sum:
            self.total_lowest_iv_sum = encounter.iv_sum

        if self.total_highest_sv < encounter.shiny_value:
            self.total_highest_sv = encounter.shiny_value

        if self.total_lowest_sv > encounter.shiny_value:
            self.total_lowest_sv = encounter.shiny_value

        if encounter.is_shiny:
            self.shiny_encounters += 1
            self.phase_encounters = 0
            self.phase_highest_iv_sum = None
            self.phase_lowest_iv_sum = None
            self.phase_highest_sv = None
            self.phase_lowest_sv = None
        else:
            self.phase_encounters += 1

            if self.phase_highest_iv_sum is None or self.phase_highest_iv_sum < encounter.iv_sum:
                self.phase_highest_iv_sum = encounter.iv_sum

            if self.phase_lowest_iv_sum is None or self.phase_lowest_iv_sum > encounter.iv_sum:
                self.phase_lowest_iv_sum = encounter.iv_sum

            if self.phase_highest_sv is None or self.phase_highest_sv < encounter.shiny_value:
                self.phase_highest_sv = encounter.shiny_value

            if self.phase_lowest_sv is None or self.phase_lowest_sv > encounter.shiny_value:
                self.phase_lowest_sv = encounter.shiny_value

    def update_outcome(self, outcome: BattleOutcome) -> None:
        if outcome is BattleOutcome.Caught:
            self.catches += 1

    def to_dict(self) -> dict:
        return {
            "encounters": self.total_encounters,
            "phase_encounters": self.phase_encounters,
            "total_highest_iv_sum": self.total_highest_iv_sum,
            "total_lowest_iv_sum": self.total_lowest_iv_sum,
            "total_highest_sv": self.total_highest_sv,
            "total_lowest_sv": self.total_lowest_sv,
            "phase_highest_iv_sum": self.phase_highest_iv_sum,
            "phase_lowest_iv_sum": self.phase_lowest_iv_sum,
            "phase_highest_sv": self.phase_highest_sv,
            "phase_lowest_sv": self.phase_lowest_sv,
            "last_encounter_time_str": self.last_encounter_time.isoformat(),
            "last_encounter_time_unix": self.last_encounter_time.timestamp(),
        }


@dataclass
class PickupItem:
    item: "Item"
    times_picked_up: int = 0


class StatsDatabase:
    def __init__(self, profile: "Profile"):
        self.encounter_rate: int = 0
        self.encounter_rate_at_1x: float = 0.0

        self._connection = sqlite3.connect(profile.path / "stats.db", check_same_thread=False)
        self._cursor = self._connection.cursor()

        db_schema_version = self._get_schema_version()
        if db_schema_version < current_schema_version:
            self._update_schema(db_schema_version)
            if db_schema_version == 0:
                self._migrate_old_stats(profile)
        elif db_schema_version > current_schema_version:
            raise StatsDatabaseSchemaTooNew(
                f"The profile's stats database schema has version {db_schema_version}, but this version of the bot only supports version {current_schema_version}. Cannot load stats."
            )

        self._current_shiny_phase: ShinyPhase | None = self._get_current_shiny_phase()
        self._next_encounter_id: int = self._get_next_encounter_id()
        self._encounter_summaries: dict[int, EncounterSummary] = self._get_encounter_summaries()
        self._pickup_items: dict[int, PickupItem] = self._get_pickup_items()
        self._last_encounter: Encounter | None = self._get_last_encounter()

        self._encounter_timestamps: deque[float] = deque(maxlen=100)
        self._encounter_frames: deque[int] = deque(maxlen=100)

    def log_encounter(self, pokemon: "Pokemon", custom_filter_result: str | bool):
        now_in_utc = datetime.now(timezone.utc)
        map_enum, local_coordinates = get_player_location()

        self._update_encounter_rates()

        if custom_filter_result is True:
            custom_filter_result = "True"

        if self._current_shiny_phase is None:
            shiny_phase_id = self._get_next_shiny_phase_id()
            self._current_shiny_phase = ShinyPhase.create(shiny_phase_id, now_in_utc)
            self._insert_shiny_phase(self._current_shiny_phase)

        encounter = Encounter(
            encounter_id=self._next_encounter_id,
            shiny_phase_id=self._current_shiny_phase.shiny_phase_id,
            matching_custom_catch_filters=custom_filter_result,
            encounter_time=now_in_utc,
            map=map_enum.name,
            coordinates=f"{local_coordinates[0]}:{local_coordinates[1]}",
            bot_mode=context.bot_mode,
            outcome=None,
            pokemon=pokemon,
        )

        self._last_encounter = encounter
        self._insert_encounter(encounter)
        self._current_shiny_phase.update(encounter)
        self._update_shiny_phase(self._current_shiny_phase)

        if pokemon.is_shiny:
            self._reset_phase_in_database(encounter)
            self._current_shiny_phase = None
            for species_id in self._encounter_summaries:
                encounter_summary = self._encounter_summaries[species_id]
                encounter_summary.phase_encounters = 0
                encounter_summary.phase_highest_iv_sum = None
                encounter_summary.phase_lowest_iv_sum = None
                encounter_summary.phase_highest_sv = None
                encounter_summary.phase_lowest_sv = None

        if pokemon.species.index not in self._encounter_summaries:
            self._encounter_summaries[pokemon.species.index] = EncounterSummary.create(encounter)
        else:
            self._encounter_summaries[pokemon.species.index].update(encounter)

        self._insert_or_update_encounter_summary(self._encounter_summaries[pokemon.species.index])
        self._connection.commit()
        self._next_encounter_id += 1

        print_stats(
            self.get_total_stats(include_shortest_and_longest_phase=False),
            pokemon,
            set([e.species.name for e in self._encounter_summaries.values() if e.phase_encounters > 0]),
        )

    def log_end_of_battle(self, battle_outcome: "BattleOutcome"):
        if self._last_encounter is not None:
            self._last_encounter.outcome = battle_outcome
            self._update_encounter_outcome(self._last_encounter)

    def log_pickup_items(self, picked_up_items: list["Item"]) -> None:
        need_updating: set[PickupItem] = set()
        for item in picked_up_items:
            if item.index not in self._pickup_items:
                self._pickup_items[item.index] = PickupItem(item)
            self._pickup_items[item.index].times_picked_up += 1
            need_updating.add(self._pickup_items[item.index])
        for pickup_item in need_updating:
            self._insert_or_update_pickup_item(pickup_item)

    def get_total_stats(self, include_shortest_and_longest_phase: bool = True) -> dict:
        if include_shortest_and_longest_phase:
            shortest_phase = self._cursor.execute(
                """
                SELECT shiny_phases.encounters, encounters.species_id
                FROM shiny_phases
                JOIN encounters ON shiny_phases.shiny_encounter_id = encounters.encounter_id
                ORDER BY shiny_phases.encounters
                LIMIT 1
                """
            ).fetchone()

            longest_phase = self._cursor.execute(
                """
                SELECT shiny_phases.encounters, encounters.species_id
                FROM shiny_phases
                JOIN encounters ON shiny_phases.shiny_encounter_id = encounters.encounter_id
                ORDER BY shiny_phases.encounters DESC
                LIMIT 1
                """
            ).fetchone()
        else:
            shortest_phase = 0, None
            longest_phase = 0, None

        pickup = {}
        for index in self._pickup_items:
            pickup_item = self._pickup_items[index]
            pickup[pickup_item.item.name] = pickup_item.times_picked_up

        pokemon = {}
        totals = {
            "encounters": 0,
            "phase_encounters": 0,
            "shiny_encounters": 0,
            "last_encounter_pid": self._last_encounter.pokemon.personality_value if self._last_encounter else None,
            "highest_iv_sum": None,
            "highest_iv_sum_pokemon": None,
            "lowest_iv_sum": None,
            "lowest_iv_sum_pokemon": None,
            "phase_highest_iv_sum": None,
            "phase_highest_iv_sum_pokemon": None,
            "phase_lowest_iv_sum": None,
            "phase_lowest_iv_sum_pokemon": None,
            "phase_highest_sv": None,
            "phase_highest_sv_pokemon": None,
            "phase_lowest_sv": None,
            "phase_lowest_sv_pokemon": None,
            "phase_streak": self._current_shiny_phase.longest_streak if self._current_shiny_phase is not None else None,
            "phase_streak_pokemon": (
                self._current_shiny_phase.longest_streak_species if self._current_shiny_phase is not None else None
            ),
            "current_streak": (
                self._current_shiny_phase.current_streak if self._current_shiny_phase is not None else None
            ),
            "current_streak_pokemon": (
                self._current_shiny_phase.current_streak_species if self._current_shiny_phase is not None else None
            ),
            "shortest_phase_encounters": shortest_phase[0],
            "shortest_phase_pokemon": (
                get_species_by_index(shortest_phase[1]).name if shortest_phase[1] is not None else None
            ),
            "longest_phase_encounters": longest_phase[0],
            "longest_phase_pokemon": (
                get_species_by_index(longest_phase[1]).name if longest_phase[1] is not None else None
            ),
            "pickup": pickup,
        }

        for species_id in self._encounter_summaries:
            encounter_summary = self._encounter_summaries[species_id]

            totals["encounters"] += encounter_summary.total_encounters
            totals["phase_encounters"] += encounter_summary.total_encounters
            totals["shiny_encounters"] += encounter_summary.phase_encounters

            if totals["highest_iv_sum"] is None or totals["highest_iv_sum"] < encounter_summary.total_highest_iv_sum:
                totals["highest_iv_sum"] = encounter_summary.total_highest_iv_sum
                totals["highest_iv_sum_pokemon"] = encounter_summary.species.name

            if totals["lowest_iv_sum"] is None or totals["lowest_iv_sum"] > encounter_summary.total_lowest_iv_sum:
                totals["lowest_iv_sum"] = encounter_summary.total_lowest_iv_sum
                totals["lowest_iv_sum_pokemon"] = encounter_summary.species.name

            if encounter_summary.phase_highest_iv_sum is not None and (
                totals["phase_highest_iv_sum"] is None
                or totals["phase_highest_iv_sum"] < encounter_summary.phase_highest_iv_sum
            ):
                totals["phase_highest_iv_sum"] = encounter_summary.phase_highest_iv_sum
                totals["phase_highest_iv_sum_pokemon"] = encounter_summary.species.name

            if encounter_summary.phase_lowest_iv_sum is not None and (
                totals["phase_lowest_iv_sum"] is None
                or totals["phase_lowest_iv_sum"] < encounter_summary.phase_lowest_iv_sum
            ):
                totals["phase_lowest_iv_sum"] = encounter_summary.phase_lowest_iv_sum
                totals["phase_lowest_iv_sum_pokemon"] = encounter_summary.species.name

            if encounter_summary.phase_highest_sv is not None and (
                totals["phase_highest_sv"] is None or totals["phase_highest_sv"] < encounter_summary.phase_highest_sv
            ):
                totals["phase_highest_sv"] = encounter_summary.phase_highest_sv
                totals["phase_highest_sv_pokemon"] = encounter_summary.species.name

            if encounter_summary.phase_lowest_iv_sum is not None and (
                totals["phase_lowest_sv"] is None or totals["phase_lowest_sv"] < encounter_summary.phase_lowest_sv
            ):
                totals["phase_lowest_sv"] = encounter_summary.phase_lowest_sv
                totals["phase_lowest_sv_pokemon"] = encounter_summary.species.name

            pokemon[encounter_summary.species.name] = encounter_summary.to_dict()

        return {"pokemon": pokemon, "totals": totals}

    def get_encounter_log(self) -> list[Encounter]:
        return list(self._query_encounters())

    def get_shiny_log(self) -> list[tuple[ShinyPhase, Encounter]]:
        result = []
        for shiny_encounter in list(self._query_encounters("is_shiny = 1")):
            shiny_phase = self._get_shiny_phase_by_id(shiny_encounter.shiny_phase_id)
            if shiny_phase is not None:
                result.append((shiny_phase, shiny_encounter))
        return result

    def _query_encounters(
        self, where_clause: str | None = None, limit: int = 10, offset: int = 0
    ) -> Iterable[Encounter]:
        result = self._cursor.execute(
            f"""
            SELECT
                encounter_id,
                species_id,
                personality_value,
                shiny_phase_id,
                is_shiny,
                is_roamer,
                matching_custom_catch_filters,
                encounter_time,
                map,
                coordinates,
                bot_mode,
                outcome,
                data
            FROM encounters
            {f'WHERE {where_clause}' if where_clause is not None else ''}
            ORDER BY encounter_id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        for row in result:
            yield Encounter.from_row_data(row)

    def _update_encounter_rates(self) -> None:
        self._encounter_timestamps.append(time.time())
        self._encounter_frames.append(context.frame)

        number_of_encounters = len(self._encounter_timestamps)
        if number_of_encounters > 1:
            first_recorded_timestamp = self._encounter_timestamps[0]
            last_recorded_timestamp = self._encounter_timestamps[-1]
            timestamp_diff = last_recorded_timestamp - first_recorded_timestamp
            average_time_per_encounter = timestamp_diff / (number_of_encounters - 1)
            self.encounter_rate = int(3600 / average_time_per_encounter)

        number_of_encounters = len(self._encounter_frames)
        if number_of_encounters > 1:
            first_recorded_frame = self._encounter_frames[0]
            last_recorded_frame = self._encounter_frames[-1]
            frame_diff = last_recorded_frame - first_recorded_frame
            average_frames_per_encounter = frame_diff / (number_of_encounters - 1)
            average_seconds_per_encounter = average_frames_per_encounter / 59.727500569606
            self.encounter_rate_at_1x = round(3600 / average_seconds_per_encounter, 1)

    def _get_next_encounter_id(self) -> int:
        result = self._cursor.execute(
            "SELECT encounter_id FROM encounters ORDER BY encounter_id DESC LIMIT 1"
        ).fetchone()
        if result is None:
            return 1
        else:
            return int(result[0]) + 1

    def _get_current_shiny_phase(self) -> ShinyPhase | None:
        result = self._cursor.execute(
            "SELECT shiny_phase_id, start_time, end_time, shiny_encounter_id, encounters, highest_iv_sum, lowest_iv_sum, highest_sv, lowest_sv, longest_streak, longest_streak_species FROM shiny_phases WHERE end_time IS NULL ORDER BY shiny_phase_id DESC LIMIT 1"
        ).fetchone()
        return ShinyPhase.from_row_data(result) if result is not None else None

    def _get_shiny_phase_by_id(self, shiny_phase_id: int) -> ShinyPhase | None:
        result = self._cursor.execute(
            "SELECT shiny_phase_id, start_time, end_time, shiny_encounter_id, encounters, highest_iv_sum, lowest_iv_sum, highest_sv, lowest_sv, longest_streak, longest_streak_species FROM shiny_phases WHERE shiny_phase_id = ?",
            (shiny_phase_id,),
        ).fetchone()
        return ShinyPhase.from_row_data(result) if result is not None else None

    def _get_next_shiny_phase_id(self) -> int:
        result = self._cursor.execute(
            "SELECT shiny_phase_id FROM shiny_phases ORDER BY shiny_phase_id DESC LIMIT 1"
        ).fetchone()
        if result is None:
            return 1
        else:
            return int(result[0]) + 1

    def _get_encounter_summaries(self) -> dict[int, EncounterSummary]:
        result = self._cursor.execute(
            """
            SELECT
                species_id,
                species_name,
                total_encounters,
                shiny_encounters,
                catches,
                total_highest_iv_sum,
                total_lowest_iv_sum,
                total_highest_sv,
                total_lowest_sv,
                phase_encounters,
                phase_highest_iv_sum,
                phase_lowest_iv_sum,
                phase_highest_sv,
                phase_lowest_sv,
                last_encounter_time
            FROM encounter_summaries
            ORDER BY species_id
            """
        )

        encounter_summaries = {}
        for row in result:
            species_id = int(row[0])
            encounter_summaries[species_id] = EncounterSummary(
                species=get_species_by_index(species_id),
                total_encounters=int(row[2]),
                shiny_encounters=int(row[3]),
                catches=int(row[4]),
                total_highest_iv_sum=int(row[5]),
                total_lowest_iv_sum=int(row[6]),
                total_highest_sv=int(row[7]),
                total_lowest_sv=int(row[8]),
                phase_encounters=int(row[9]),
                phase_highest_iv_sum=int(row[10]) if row[10] is not None else None,
                phase_lowest_iv_sum=int(row[11]) if row[11] is not None else None,
                phase_highest_sv=int(row[12]) if row[12] is not None else None,
                phase_lowest_sv=int(row[13]) if row[13] is not None else None,
                last_encounter_time=datetime.fromisoformat(row[14]),
            )

        return encounter_summaries

    def _get_pickup_items(self) -> dict[int, PickupItem]:
        pickup_items = {}
        result = self._cursor.execute("SELECT item_id, item_name, times_picked_up FROM pickup_items ORDER BY item_id")
        for row in result:
            pickup_items[int(row[0])] = PickupItem(get_item_by_index(int(row[0])), int(row[2]))
        return pickup_items

    def _get_last_encounter(self) -> Encounter | None:
        result = list(self._query_encounters(limit=1))
        if len(result) == 0:
            return None
        else:
            return result[0]

    def _insert_encounter(self, encounter: Encounter) -> None:
        self._cursor.execute(
            """
            INSERT INTO encounters
                (encounter_id, species_id, personality_value, shiny_phase_id, is_shiny, matching_custom_catch_filters, encounter_time, map, coordinates, bot_mode, outcome, data)
            VALUES
                (?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter.encounter_id,
                encounter.species_id,
                encounter.pokemon.personality_value,
                encounter.shiny_phase_id,
                encounter.is_shiny,
                encounter.matching_custom_catch_filters,
                encounter.encounter_time,
                encounter.map,
                encounter.coordinates,
                encounter.bot_mode,
                None,
                encounter.data,
            ),
        )

    def _update_encounter_outcome(self, encounter: Encounter):
        self._cursor.execute(
            "UPDATE encounters SET outcome = ? WHERE encounter_id = ?",
            (encounter.outcome.value, encounter.encounter_id),
        )

    def _insert_shiny_phase(self, shiny_phase: ShinyPhase) -> None:
        self._cursor.execute(
            "INSERT INTO shiny_phases (shiny_phase_id, start_time) VALUES (?, ?)",
            (shiny_phase.shiny_phase_id, shiny_phase.start_time),
        )

    def _update_shiny_phase(self, shiny_phase: ShinyPhase) -> None:
        self._cursor.execute(
            """
            UPDATE shiny_phases
            SET encounters = ?,
                highest_iv_sum = ?,
                lowest_iv_sum = ?,
                highest_sv = ?,
                lowest_sv = ?,
                longest_streak = ?,
                longest_streak_species = ?,
                current_streak = ?,
                current_streak_species = ?
            WHERE shiny_phase_id = ?
            """,
            (
                shiny_phase.encounters,
                shiny_phase.highest_iv_sum,
                shiny_phase.lowest_iv_sum,
                shiny_phase.highest_sv,
                shiny_phase.lowest_sv,
                shiny_phase.shiny_phase_id,
                shiny_phase.longest_streak,
                shiny_phase.longest_streak_species,
                shiny_phase.current_streak,
                shiny_phase.current_streak_species,
            ),
        )

    def _reset_phase_in_database(self, encounter: Encounter) -> None:
        """
        Resets phase-specific information for `shiny_phases` and `encounter_summaries` table.
        :param encounter: Shiny encounter that ended the phase.
        """

        self._cursor.execute(
            "UPDATE shiny_phases SET end_time = ?, shiny_encounter_id = ? WHERE shiny_phase_id = ?",
            (encounter.encounter_time, encounter.encounter_id, self._current_shiny_phase.shiny_phase_id),
        )

        self._cursor.execute(
            """
            UPDATE encounter_summaries
               SET phase_encounters = 0,
                   phase_highest_iv_sum = NULL,
                   phase_lowest_iv_sum = NULL,
                   phase_highest_sv = NULL,
                   phase_lowest_sv = NULL
            """
        )

    def _insert_or_update_encounter_summary(self, encounter_summary: EncounterSummary) -> None:
        if encounter_summary.species is None:
            raise RuntimeError("Cannot save an encounter summary that is not associated to a species.")

        self._cursor.execute(
            """
            REPLACE INTO encounter_summaries
                (species_id, species_name, total_encounters, shiny_encounters, catches, total_highest_iv_sum, total_lowest_iv_sum, total_highest_sv, total_lowest_sv, phase_encounters, phase_highest_iv_sum, phase_lowest_iv_sum, phase_highest_sv, phase_lowest_sv, last_encounter_time)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                encounter_summary.species.index,
                encounter_summary.species.name,
                encounter_summary.total_encounters,
                encounter_summary.shiny_encounters,
                encounter_summary.catches,
                encounter_summary.total_highest_iv_sum,
                encounter_summary.total_lowest_iv_sum,
                encounter_summary.total_highest_sv,
                encounter_summary.total_lowest_sv,
                encounter_summary.phase_encounters,
                encounter_summary.phase_highest_iv_sum,
                encounter_summary.phase_lowest_iv_sum,
                encounter_summary.phase_highest_sv,
                encounter_summary.phase_lowest_sv,
                encounter_summary.last_encounter_time,
            ),
        )

    def _insert_or_update_pickup_item(self, pickup_item: PickupItem) -> None:
        self._cursor.execute(
            "REPLACE INTO pickup_items (item_id, item_name, times_picked_up) VALUES (?, ?, ?)",
            (pickup_item.item.index, pickup_item.item.name, pickup_item.times_picked_up),
        )

    def _migrate_old_stats(self, profile: "Profile") -> None:
        """
        Checks whether the profile has legacy stats files (`stats/totals.json` and `stats/shiny_log.json`)
        and migrates them to the new database schema as best it can.

        :param profile: Currently loaded profile
        """

        totals_file = profile.path / "stats" / "totals.json"
        if totals_file.exists():
            totals = json.load(totals_file.open("r"))
            for species_name in totals["pokemon"]:
                old_data = totals["pokemon"][species_name]
                encounter_summary = EncounterSummary(
                    species=get_species_by_name(species_name),
                    total_encounters=old_data["encounters"],
                    shiny_encounters=old_data["shiny_encounters"] if "shiny_encounters" in old_data else 0,
                    catches=old_data["shiny_encounters"] if "shiny_encounters" in old_data else 0,
                    total_highest_iv_sum=old_data["total_highest_iv_sum"],
                    total_lowest_iv_sum=old_data["total_lowest_iv_sum"],
                    total_highest_sv=(
                        old_data["total_highest_sv"] if "total_highest_sv" in old_data else old_data["total_lowest_sv"]
                    ),
                    total_lowest_sv=old_data["total_lowest_sv"],
                    phase_encounters=old_data["phase_encounters"],
                    phase_highest_iv_sum=old_data["phase_highest_iv_sum"],
                    phase_lowest_iv_sum=old_data["phase_lowest_iv_sum"],
                    phase_highest_sv=old_data["phase_highest_sv"],
                    phase_lowest_sv=old_data["phase_lowest_sv"],
                    last_encounter_time=datetime.fromtimestamp(old_data["last_encounter_time_unix"]),
                )
                self._insert_or_update_encounter_summary(encounter_summary)
                self._connection.commit()

        shiny_log_file = profile.path / "stats" / "shiny_log.json"
        if shiny_log_file.exists():
            shiny_log = json.load(shiny_log_file.open("r"))
            previous_phase_start = None
            for entry in shiny_log["shiny_log"]:
                pkm = entry["pokemon"]
                species = get_species_by_index(pkm["species"])

                language_byte = b"\x02"
                if pkm["language"] == "J":
                    language_byte = b"\x01"
                elif pkm["language"] == "F":
                    language_byte = b"\x03"
                elif pkm["language"] == "I":
                    language_byte = b"\x04"
                elif pkm["language"] == "G":
                    language_byte = b"\x05"
                elif pkm["language"] == "S":
                    language_byte = b"\x07"

                origin_game = 3
                if pkm["origins"]["game"] == "Ruby":
                    origin_game = 1
                elif pkm["origins"]["game"] == "Sapphire":
                    origin_game = 2
                elif pkm["origins"]["game"] == "FireRed":
                    origin_game = 4
                elif pkm["origins"]["game"] == "LeafGreen":
                    origin_game = 5

                origins_info = pkm["origins"]["metLevel"] | (origin_game << 7) | (4 << 11)
                if get_player().gender == "female":
                    origins_info |= 1 << 15

                iv_egg_ability = (
                    (pkm["IVs"]["hp"])
                    | (pkm["IVs"]["attack"] << 5)
                    | (pkm["IVs"]["defense"] << 10)
                    | (pkm["IVs"]["speed"] << 15)
                    | (pkm["IVs"]["spAttack"] << 20)
                    | (pkm["IVs"]["spDefense"] << 25)
                )
                if pkm["ability"] != species.abilities[0].name:
                    iv_egg_ability |= 1 << 31

                data_to_encrypt = (
                    species.index.to_bytes(2, byteorder="little")
                    + pkm["item"]["id"].to_bytes(2, byteorder="little")
                    + pkm["experience"].to_bytes(4, byteorder="little")
                    + b"\x00"
                    + pkm["friendship"].to_bytes(1)
                    + b"\x00\x00"
                    + pkm["moves"][0]["id"].to_bytes(2, byteorder="little")
                    + pkm["moves"][1]["id"].to_bytes(2, byteorder="little")
                    + pkm["moves"][2]["id"].to_bytes(2, byteorder="little")
                    + pkm["moves"][3]["id"].to_bytes(2, byteorder="little")
                    + pkm["moves"][0]["remaining_pp"].to_bytes(1)
                    + pkm["moves"][1]["remaining_pp"].to_bytes(1)
                    + pkm["moves"][2]["remaining_pp"].to_bytes(1)
                    + pkm["moves"][3]["remaining_pp"].to_bytes(1)
                    + pkm["EVs"]["hp"].to_bytes(1)
                    + pkm["EVs"]["attack"].to_bytes(1)
                    + pkm["EVs"]["defence"].to_bytes(1)
                    + pkm["EVs"]["speed"].to_bytes(1)
                    + pkm["EVs"]["spAttack"].to_bytes(1)
                    + pkm["EVs"]["spDefense"].to_bytes(1)
                    + pkm["condition"]["cool"].to_bytes(1)
                    + pkm["condition"]["beauty"].to_bytes(1)
                    + pkm["condition"]["cute"].to_bytes(1)
                    + pkm["condition"]["smart"].to_bytes(1)
                    + pkm["condition"]["tough"].to_bytes(1)
                    + pkm["condition"]["feel"].to_bytes(1)
                    + b"\x00"
                    + LOCATION_MAP.index(pkm["metLocation"]).to_bytes(1)
                    + origins_info.to_bytes(2, byteorder="little")
                    + iv_egg_ability.to_bytes(4, byteorder="little")
                    + b"\x00\x00\x00\x00"
                )

                data = (
                    pkm["pid"].to_bytes(length=4, byteorder="little")
                    + pkm["ot"]["tid"].to_bytes(length=2, byteorder="little")
                    + pkm["ot"]["sid"].to_bytes(length=2, byteorder="little")
                    + encode_string(species.name.upper()).ljust(10, b"\x00")
                    + language_byte
                    + b"\x01"
                    + encode_string(get_player().name).ljust(7, b"\x00")
                    + b"\x00"
                    + (sum(struct.unpack("<24H", data_to_encrypt)) & 0xFFFF).to_bytes(length=2, byteorder="little")
                    + b"\x00\x00"
                    + data_to_encrypt
                    + b"\x00\x00\x00\x00"
                    + pkm["level"].to_bytes(length=1, byteorder="little")
                    + b"\x00"
                    + pkm["stats"]["maxHP"].to_bytes(length=2, byteorder="little")
                    + pkm["stats"]["maxHP"].to_bytes(length=2, byteorder="little")
                    + pkm["stats"]["attack"].to_bytes(length=2, byteorder="little")
                    + pkm["stats"]["defense"].to_bytes(length=2, byteorder="little")
                    + pkm["stats"]["speed"].to_bytes(length=2, byteorder="little")
                    + pkm["stats"]["spAttack"].to_bytes(length=2, byteorder="little")
                    + pkm["stats"]["spDefense"].to_bytes(length=2, byteorder="little")
                )

                u32le = numpy.dtype("<u4")
                personality_value = numpy.frombuffer(data, count=1, dtype=u32le)
                original_trainer_id = numpy.frombuffer(data, count=1, offset=4, dtype=u32le)
                key = numpy.repeat(personality_value ^ original_trainer_id, 3)
                order = POKEMON_DATA_SUBSTRUCTS_ORDER[pkm["pid"] % 24]

                encrypted_data = numpy.concatenate(
                    [
                        numpy.frombuffer(data, count=3, offset=32 + (order.index(i) * 12), dtype=u32le) ^ key
                        for i in range(4)
                    ]
                )

                pokemon_data = data[:32] + encrypted_data.tobytes() + data[80:100]

                encounter_id = self._get_next_encounter_id()
                shiny_phase_id = self._get_next_shiny_phase_id()

                encounter = Encounter(
                    encounter_id=encounter_id,
                    shiny_phase_id=shiny_phase_id,
                    matching_custom_catch_filters="",
                    encounter_time=datetime.fromtimestamp(entry["time_encountered"]),
                    map="",
                    coordinates="",
                    bot_mode="",
                    outcome=None,
                    pokemon=Pokemon(pokemon_data),
                )
                self._insert_encounter(encounter)

                self._cursor.execute(
                    """
                    INSERT INTO shiny_phases
                        (shiny_phase_id, start_time, end_time, shiny_encounter_id, encounters)
                    VALUES
                        (?, ?, ?, ?, ?)
                    """,
                    (
                        shiny_phase_id,
                        (
                            previous_phase_start
                            if previous_phase_start is not None
                            else datetime.fromtimestamp(entry["time_encountered"])
                        ),
                        datetime.fromtimestamp(entry["time_encountered"]),
                        encounter_id,
                        entry["snapshot_stats"]["phase_encounters"],
                    ),
                )
                previous_phase_start = datetime.fromtimestamp(entry["time_encountered"])
                self._connection.commit()

    def _get_schema_version(self) -> int:
        """
        :return: The version number of the database schema, or 0 if this is a new database.
        """
        result = self._cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'")
        if result.fetchone() is None:
            return 0

        result = self._cursor.execute("SELECT version FROM schema_version").fetchone()
        if result is None:
            return 0

        return int(result[0])

    def _update_schema(self, from_schema_version: int) -> None:
        """
        Updates the database schema to the current version.

        This function should contain blocks like

        ```python
            if from_schema_version <= 3:
                self._cursor.execute(...)
        ```

        and these blocks should be sorted by the `from_schema_version` value they check
        for, with the smallest number first.

        This means that even from an empty/non-existent database or any older version,
        an up-to-date schema can be created.

        :param from_schema_version: Version number of the database schema as it
                                    currently exists in the database (0 means there is
                                    no database.)
        """

        if from_schema_version <= 0:
            self._cursor.execute("CREATE TABLE schema_version (version INT UNSIGNED)")

            self._cursor.execute(
                """
                CREATE TABLE encounter_summaries (
                    species_id INT UNSIGNED PRIMARY KEY,
                    species_name TEXT NOT NULL,
                    total_encounters INT UNSIGNED,
                    shiny_encounters INT UNSIGNED,
                    catches INT UNSIGNED,
                    total_highest_iv_sum INT UNSIGNED,
                    total_lowest_iv_sum INT UNSIGNED,
                    total_highest_sv INT UNSIGNED,
                    total_lowest_sv INT UNSIGNED,
                    phase_encounters INT UNSIGNED,
                    phase_highest_iv_sum INT UNSIGNED DEFAULT NULL,
                    phase_lowest_iv_sum INT UNSIGNED DEFAULT NULL,
                    phase_highest_sv INT UNSIGNED DEFAULT NULL,
                    phase_lowest_sv INT UNSIGNED DEFAULT NULL,
                    last_encounter_time DATETIME
                )
                """
            )

            self._cursor.execute(
                """
                CREATE TABLE shiny_phases (
                    shiny_phase_id INT UNSIGNED PRIMARY KEY,
                    start_time DATETIME NOT NULL,
                    end_time DATETIME DEFAULT NULL,
                    shiny_encounter_id INT UNSIGNED DEFAULT NULL,
                    encounters INT UNSIGNED DEFAULT 0,
                    highest_iv_sum INT UNSIGNED DEFAULT NULL,
                    lowest_iv_sum INT UNSIGNED DEFAULT NULL,
                    highest_sv INT UNSIGNED DEFAULT NULL,
                    lowest_sv INT UNSIGNED DEFAULT NULL,
                    longest_streak INT UNSIGNED DEFAULT 0,
                    longest_streak_species TEXT DEFAULT NULL,
                    current_streak INT UNSIGNED DEFAULT 0,
                    current_streak_species TEXT DEFAULT NULL
                )
                """
            )

            self._cursor.execute(
                """
                CREATE TABLE encounters (
                    encounter_id INT UNSIGNED PRIMARY KEY,
                    species_id INT UNSIGNED NOT NULL,
                    personality_value INT UNSIGNED NOT NULL,
                    shiny_phase_id INT UNSIGNED NOT NULL,
                    is_shiny INT UNSIGNED DEFAULT 0,
                    is_roamer INT UNSIGNED DEFAULT 0,
                    matching_custom_catch_filters TEXT DEFAULT NULL,
                    encounter_time DATETIME NOT NULL,
                    map TEXT,
                    coordinates TEXT,
                    bot_mode TEXT,
                    outcome INT UNSIGNED DEFAULT NULL,
                    data BLOB NOT NULL
                )
                """
            )

            self._cursor.execute(
                """
                CREATE TABLE pickup_items (
                    item_id INT UNSIGNED PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    times_picked_up INT NOT NULL DEFAULT 0
                )
                """
            )

        self._cursor.execute("DELETE FROM schema_version")
        self._cursor.execute("INSERT INTO schema_version VALUES (?)", (current_schema_version,))
