import sqlite3
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import cached_property
from textwrap import dedent
from typing import TYPE_CHECKING, Iterable, Optional

from modules.battle_state import BattleOutcome, EncounterType, get_encounter_type
from modules.context import context
from modules.encounter import judge_encounter
from modules.fishing import FishingAttempt, FishingResult
from modules.items import Item, get_item_by_index
from modules.player import get_player_location
from modules.pokemon import Pokemon, get_species_by_index, Species

if TYPE_CHECKING:
    from modules.profiles import Profile


current_schema_version = 1


class StatsDatabaseSchemaTooNew(Exception):
    pass


class DataKey(Enum):
    TrainerID = 1
    SecretTrainerID = 2


class BaseData:
    key: DataKey
    value: str | None


@dataclass
class Encounter:
    encounter_id: int
    shiny_phase_id: int
    matching_custom_catch_filters: str | None
    encounter_time: datetime
    map: str | None
    coordinates: str | None
    bot_mode: str
    type: EncounterType | None
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
            type=EncounterType(row[11]) if row[11] else None,
            outcome=BattleOutcome(row[12]) if row[12] else None,
            pokemon=Pokemon(row[13]),
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
            "type": self.type.value if self.type else None,
            "outcome": self.outcome.name if self.outcome is not None else None,
            "pokemon": self.pokemon.to_dict(),
        }


@dataclass
class ShinyPhase:
    shiny_phase_id: int
    start_time: datetime
    end_time: datetime | None = None
    shiny_encounter: Encounter | None = None
    encounters: int = 0
    highest_iv_sum: int | None = None
    highest_iv_sum_species: "Species | None" = None
    lowest_iv_sum: int | None = None
    lowest_iv_sum_species: "Species | None" = None
    highest_sv: int | None = None
    highest_sv_species: "Species | None" = None
    lowest_sv: int | None = None
    lowest_sv_species: "Species | None" = None
    longest_streak: int = 0
    longest_streak_species: "Species | None" = None
    current_streak: int = 0
    current_streak_species: "Species | None" = None
    fishing_attempts: int = 0
    successful_fishing_attempts: int = 0
    longest_unsuccessful_fishing_streak: int = 0
    current_unsuccessful_fishing_streak: int = 0

    snapshot_total_encounters: int | None = None
    snapshot_total_shiny_encounters: int | None = None
    snapshot_species_encounters: int | None = None
    snapshot_species_shiny_encounters: int | None = None

    @classmethod
    def from_row_data(cls, row: list | tuple, shiny_encounter: Encounter | None) -> "ShinyPhase":
        return ShinyPhase(
            row[0],
            datetime.fromisoformat(row[1]),
            datetime.fromisoformat(row[2]) if row[2] is not None else None,
            shiny_encounter,
            row[4],
            row[5],
            get_species_by_index(row[6]) if row[6] is not None else None,
            row[7],
            get_species_by_index(row[8]) if row[8] is not None else None,
            row[9],
            get_species_by_index(row[10]) if row[10] is not None else None,
            row[11],
            get_species_by_index(row[12]) if row[12] is not None else None,
            row[13],
            get_species_by_index(row[14]) if row[14] is not None else None,
            row[15],
            get_species_by_index(row[16]) if row[16] is not None else None,
            row[17],
            row[18],
            row[19],
            row[20],
            row[21],
            row[22],
            row[23],
            row[24],
        )

    @classmethod
    def create(cls, shiny_phase_id: int, start_time: datetime) -> "ShinyPhase":
        return cls(shiny_phase_id=shiny_phase_id, start_time=start_time)

    def update(self, encounter: Encounter):
        self.encounters += 1

        if self.highest_iv_sum is None or self.highest_iv_sum < encounter.iv_sum:
            self.highest_iv_sum = encounter.iv_sum
            self.highest_iv_sum_species = encounter.pokemon.species

        if self.lowest_iv_sum is None or self.lowest_iv_sum > encounter.iv_sum:
            self.lowest_iv_sum = encounter.iv_sum
            self.lowest_iv_sum_species = encounter.pokemon.species

        if not encounter.is_shiny:
            if self.highest_sv is None or self.highest_sv < encounter.shiny_value:
                self.highest_sv = encounter.shiny_value
                self.highest_sv_species = encounter.pokemon.species

            if self.lowest_sv is None or self.lowest_sv > encounter.shiny_value:
                self.lowest_sv = encounter.shiny_value
                self.lowest_sv_species = encounter.pokemon.species

        if self.current_streak_species != encounter.pokemon.species:
            self.current_streak = 1
            self.current_streak_species = encounter.pokemon.species
        else:
            self.current_streak += 1
            if self.current_streak > self.longest_streak:
                self.longest_streak = self.current_streak
                self.longest_streak_species = self.current_streak_species

        if encounter.is_shiny:
            self.shiny_encounter = encounter
            self.end_time = encounter.encounter_time

    def update_fishing_attempt(self, attempt: FishingAttempt):
        self.fishing_attempts += 1
        if attempt.result is not FishingResult.Encounter:
            self.current_unsuccessful_fishing_streak += 1
            if self.current_unsuccessful_fishing_streak > self.longest_unsuccessful_fishing_streak:
                self.longest_unsuccessful_fishing_streak = self.current_unsuccessful_fishing_streak
        else:
            self.successful_fishing_attempts += 1
            self.current_unsuccessful_fishing_streak = 0

    def update_snapshot(self, encounter_summaries: dict[int, "EncounterSummary"]):
        self.snapshot_total_encounters = 0
        self.snapshot_total_shiny_encounters = 0
        for species_id in encounter_summaries:
            encounter_summary = encounter_summaries[species_id]
            self.snapshot_total_encounters += encounter_summary.total_encounters
            self.snapshot_total_shiny_encounters += encounter_summary.shiny_encounters
            if species_id == self.shiny_encounter.species_id:
                self.snapshot_species_encounters = encounter_summary.total_encounters
                self.snapshot_species_shiny_encounters = encounter_summary.shiny_encounters

    def to_dict(self) -> dict:
        def species_name(species: Species | None) -> str | None:
            return species.name if species is not None else None

        return {
            "phase": {
                "shiny_phase_id": self.shiny_phase_id,
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat() if self.end_time is not None else None,
                "encounters": self.encounters,
                "highest_iv_sum": {
                    "value": self.highest_iv_sum,
                    "species_name": species_name(self.highest_iv_sum_species),
                },
                "lowest_iv_sum": {
                    "value": self.lowest_iv_sum,
                    "species_name": species_name(self.lowest_iv_sum_species),
                },
                "highest_sv": {
                    "value": self.highest_sv,
                    "species_name": species_name(self.highest_sv_species),
                },
                "lowest_sv": {
                    "value": self.lowest_sv,
                    "species_name": species_name(self.lowest_sv_species),
                },
                "longest_streak": {
                    "value": self.longest_streak,
                    "species_name": species_name(self.longest_streak_species),
                },
                "current_streak": {
                    "value": self.current_streak,
                    "species_name": species_name(self.current_streak_species),
                },
                "fishing_attempts": self.fishing_attempts,
                "successful_fishing_attempts": self.successful_fishing_attempts,
                "longest_unsuccessful_fishing_streak": self.longest_unsuccessful_fishing_streak,
                "current_unsuccessful_fishing_streak": self.current_unsuccessful_fishing_streak,
            },
            "snapshot": {
                "total_encounters": self.snapshot_total_encounters,
                "total_shiny_encounters": self.snapshot_total_shiny_encounters,
                "species_encounters": self.snapshot_species_encounters,
                "species_shiny_encounters": self.snapshot_species_shiny_encounters,
            },
            "shiny_encounter": self.shiny_encounter.to_dict() if self.shiny_encounter is not None else None,
        }


@dataclass
class EncounterSummary:
    species: "Species"
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
            "species_id": self.species.index if self.species is not None else None,
            "species_name": self.species.name if self.species is not None else None,
            "total_encounters": self.total_encounters,
            "shiny_encounters": self.shiny_encounters,
            "catches": self.catches,
            "total_highest_iv_sum": self.total_highest_iv_sum,
            "total_lowest_iv_sum": self.total_lowest_iv_sum,
            "total_highest_sv": self.total_highest_sv,
            "total_lowest_sv": self.total_lowest_sv,
            "phase_encounters": self.phase_encounters,
            "phase_highest_iv_sum": self.phase_highest_iv_sum,
            "phase_lowest_iv_sum": self.phase_lowest_iv_sum,
            "phase_highest_sv": self.phase_highest_sv,
            "phase_lowest_sv": self.phase_lowest_sv,
            "last_encounter_time": self.last_encounter_time.isoformat(),
        }


@dataclass
class EncounterTotals:
    total_encounters: int = 0
    shiny_encounters: int = 0
    catches: int = 0
    total_highest_iv_sum: int = 0
    total_highest_iv_sum_species: Species | None = None
    total_lowest_iv_sum: int = 31 * 6
    total_lowest_iv_sum_species: Species | None = None
    total_highest_sv: int = 0
    total_highest_sv_species: Species | None = None
    total_lowest_sv: int = 0xFFFF
    total_lowest_sv_species: Species | None = None
    phase_encounters: int = 0
    phase_highest_iv_sum: int | None = None
    phase_highest_iv_sum_species: "Species | None" = None
    phase_lowest_iv_sum: int | None = None
    phase_lowest_iv_sum_species: "Species | None" = None
    phase_highest_sv: int | None = None
    phase_highest_sv_species: "Species | None" = None
    phase_lowest_sv: int | None = None
    phase_lowest_sv_species: "Species | None" = None

    @classmethod
    def from_summaries(cls, encounter_summaries: dict[int, "EncounterSummary"]) -> "EncounterTotals":
        totals = cls()
        for species_id in encounter_summaries:
            encounter_summary = encounter_summaries[species_id]

            totals.total_encounters += encounter_summary.total_encounters
            totals.shiny_encounters += encounter_summary.shiny_encounters
            totals.catches += encounter_summary.catches
            totals.phase_encounters += encounter_summary.phase_encounters

            values_to_total = [
                ("total_highest_iv_sum", max),
                ("total_lowest_iv_sum", min),
                ("total_highest_sv", max),
                ("total_lowest_sv", min),
                ("phase_highest_iv_sum", max),
                ("phase_lowest_iv_sum", min),
                ("phase_highest_sv", max),
                ("phase_lowest_sv", min),
            ]
            for property_name, comparison in values_to_total:
                total_value = getattr(totals, property_name)
                summary_value = getattr(encounter_summary, property_name)
                if (total_value is None and summary_value is not None) or (
                    total_value is not None
                    and summary_value is not None
                    and comparison(total_value, summary_value) != total_value
                ):
                    setattr(totals, property_name, summary_value)
                    setattr(totals, f"{property_name}_species", encounter_summary.species)

        return totals

    def to_dict(self) -> dict:
        def species_name(species: Species | None) -> str | None:
            return species.name if species is not None else None

        return {
            "total_encounters": self.total_encounters,
            "shiny_encounters": self.shiny_encounters,
            "catches": self.catches,
            "total_highest_iv_sum": {
                "value": self.total_highest_iv_sum,
                "species_name": species_name(self.total_highest_iv_sum_species),
            },
            "total_lowest_iv_sum": {
                "value": self.total_lowest_iv_sum,
                "species_name": species_name(self.total_lowest_iv_sum_species),
            },
            "total_highest_sv": {
                "value": self.total_highest_sv,
                "species_name": species_name(self.total_highest_sv_species),
            },
            "total_lowest_sv": {
                "value": self.total_lowest_sv,
                "species_name": species_name(self.total_lowest_sv_species),
            },
            "phase_encounters": self.phase_encounters,
            "phase_highest_iv_sum": {
                "value": self.phase_highest_iv_sum,
                "species_name": species_name(self.phase_highest_iv_sum_species),
            },
            "phase_lowest_iv_sum": {
                "value": self.phase_lowest_iv_sum,
                "species_name": species_name(self.phase_lowest_iv_sum_species),
            },
            "phase_highest_sv": {
                "value": self.phase_highest_sv,
                "species_name": species_name(self.phase_highest_sv_species),
            },
            "phase_lowest_sv": {
                "value": self.phase_lowest_sv,
                "species_name": species_name(self.phase_lowest_sv_species),
            },
        }


@dataclass
class PickupItem:
    item: "Item"
    times_picked_up: int = 0


@dataclass
class GlobalStats:
    encounter_summaries: dict[int, EncounterSummary]
    pickup_items: dict[int, PickupItem]
    current_shiny_phase: ShinyPhase | None
    longest_shiny_phase: ShinyPhase | None
    shortest_shiny_phase: ShinyPhase | None

    @cached_property
    def totals(self) -> EncounterTotals:
        return EncounterTotals.from_summaries(self.encounter_summaries)

    def species(self, species: Species) -> EncounterSummary:
        if species.index in self.encounter_summaries:
            return self.encounter_summaries[species.index]
        else:
            return EncounterSummary(
                species=species,
                total_encounters=0,
                shiny_encounters=0,
                catches=0,
                total_highest_iv_sum=0,
                total_lowest_iv_sum=0,
                total_highest_sv=0,
                total_lowest_sv=0,
                phase_encounters=0,
                phase_highest_iv_sum=0,
                phase_lowest_iv_sum=0,
                phase_highest_sv=0,
                phase_lowest_sv=0,
                last_encounter_time=datetime.now(),
            )

    def to_dict(self):
        current_shiny_phase = (
            ShinyPhase(0, datetime.now(timezone.utc)) if self.current_shiny_phase is None else self.current_shiny_phase
        )

        longest_shiny_phase = current_shiny_phase if self.longest_shiny_phase is None else self.longest_shiny_phase
        shortest_shiny_phase = current_shiny_phase if self.shortest_shiny_phase is None else self.shortest_shiny_phase

        def species_name(species: Species | None) -> str | None:
            return species.name if species is not None else None

        return {
            "pokemon": {summary.species.name: summary.to_dict() for summary in self.encounter_summaries.values()},
            "totals": self.totals.to_dict(),
            "current_phase": {
                "start_time": current_shiny_phase.start_time.isoformat(),
                "encounters": current_shiny_phase.encounters,
                "highest_iv_sum": {
                    "value": current_shiny_phase.highest_iv_sum,
                    "species_name": species_name(current_shiny_phase.highest_iv_sum_species),
                },
                "lowest_iv_sum": {
                    "value": current_shiny_phase.lowest_iv_sum,
                    "species_name": species_name(current_shiny_phase.lowest_iv_sum_species),
                },
                "highest_sv": {
                    "value": current_shiny_phase.highest_sv,
                    "species_name": species_name(current_shiny_phase.highest_sv_species),
                },
                "lowest_sv": {
                    "value": current_shiny_phase.lowest_sv,
                    "species_name": species_name(current_shiny_phase.lowest_sv_species),
                },
                "longest_streak": {
                    "value": current_shiny_phase.longest_streak,
                    "species_name": species_name(current_shiny_phase.longest_streak_species),
                },
                "current_streak": {
                    "value": current_shiny_phase.current_streak,
                    "species_name": species_name(current_shiny_phase.current_streak_species),
                },
                "fishing_attempts": current_shiny_phase.fishing_attempts,
                "successful_fishing_attempts": current_shiny_phase.successful_fishing_attempts,
                "longest_unsuccessful_fishing_streak": current_shiny_phase.longest_unsuccessful_fishing_streak,
                "current_unsuccessful_fishing_streak": current_shiny_phase.current_unsuccessful_fishing_streak,
            },
            "longest_phase": {
                "value": longest_shiny_phase.encounters,
                "species_name": (
                    longest_shiny_phase.shiny_encounter.species_name
                    if longest_shiny_phase.shiny_encounter is not None
                    else None
                ),
            },
            "shortest_phase": {
                "value": shortest_shiny_phase.encounters,
                "species_name": (
                    shortest_shiny_phase.shiny_encounter.species_name
                    if shortest_shiny_phase.shiny_encounter is not None
                    else None
                ),
            },
            "pickup_items": {entry.item.name: entry.times_picked_up for entry in self.pickup_items.values()},
        }


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

        self.last_encounter: Encounter | None = self._get_last_encounter()
        self.last_fishing_attempt: Optional[FishingAttempt] = None

        self.current_shiny_phase: ShinyPhase | None = self._get_current_shiny_phase()
        self._shortest_shiny_phase: ShinyPhase | None = self._get_shortest_shiny_phase()
        self._longest_shiny_phase: ShinyPhase | None = self._get_longest_shiny_phase()
        self._next_encounter_id: int = self._get_next_encounter_id()
        self._encounter_summaries: dict[int, EncounterSummary] = self._get_encounter_summaries()
        self._pickup_items: dict[int, PickupItem] = self._get_pickup_items()
        self._base_data: dict[DataKey, str | None] = self._get_base_data()

        self._encounter_timestamps: deque[float] = deque(maxlen=100)
        self._encounter_frames: deque[int] = deque(maxlen=100)

    def set_data(self, key: DataKey, value: str | None):
        self._cursor.execute("REPLACE INTO base_data (data_key, value) VALUES (?, ?)", (key.value, value))

    def get_data(self, key: DataKey) -> str | None:
        return self._base_data[key] if key in self._base_data else None

    def log_encounter(self, pokemon: "Pokemon", custom_filter_result: str | bool):
        now_in_utc = datetime.now(timezone.utc)
        map_enum, local_coordinates = get_player_location()

        self._update_encounter_rates()

        if custom_filter_result is True:
            custom_filter_result = "True"

        if self.current_shiny_phase is None:
            shiny_phase_id = self._get_next_shiny_phase_id()
            self.current_shiny_phase = ShinyPhase.create(shiny_phase_id, now_in_utc)
            self._insert_shiny_phase(self.current_shiny_phase)

        encounter = Encounter(
            encounter_id=self._next_encounter_id,
            shiny_phase_id=self.current_shiny_phase.shiny_phase_id,
            matching_custom_catch_filters=custom_filter_result,
            encounter_time=now_in_utc,
            map=map_enum.name,
            coordinates=f"{local_coordinates[0]}:{local_coordinates[1]}",
            bot_mode=context.bot_mode,
            type=get_encounter_type(),
            outcome=None,
            pokemon=pokemon,
        )

        self.last_encounter = encounter
        if context.config.logging.log_encounters or judge_encounter(pokemon).is_of_interest:
            self._insert_encounter(encounter)
        self.current_shiny_phase.update(encounter)
        if pokemon.is_shiny:
            self.current_shiny_phase.update_snapshot(self._encounter_summaries)
        self._update_shiny_phase(self.current_shiny_phase)

        if pokemon.is_shiny:
            self._reset_phase_in_database(encounter)
            if self.current_shiny_phase.encounters < self._shortest_shiny_phase.encounters:
                self._shortest_shiny_phase = self.current_shiny_phase
            if self.current_shiny_phase.encounters > self._longest_shiny_phase.encounters:
                self._longest_shiny_phase = self.current_shiny_phase
            self.current_shiny_phase = None
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

    def log_end_of_battle(self, battle_outcome: "BattleOutcome"):
        if self.last_encounter is not None:
            self.last_encounter.outcome = battle_outcome
            self._update_encounter_outcome(self.last_encounter)

    def log_pickup_items(self, picked_up_items: list["Item"]) -> None:
        need_updating: set[PickupItem] = set()
        for item in picked_up_items:
            if item.index not in self._pickup_items:
                self._pickup_items[item.index] = PickupItem(item)
            self._pickup_items[item.index].times_picked_up += 1
            need_updating.add(self._pickup_items[item.index])
        for pickup_item in need_updating:
            self._insert_or_update_pickup_item(pickup_item)

    def log_fishing_attempt(self, attempt: FishingAttempt):
        self.last_fishing_attempt = attempt
        if self.current_shiny_phase is not None:
            self.current_shiny_phase.update_fishing_attempt(attempt)
            if attempt.result is not FishingResult.Encounter:
                self._update_shiny_phase(self.current_shiny_phase)
        context.message = f"Fishing attempt with {attempt.rod.name} and result {attempt.result.name}"

    def get_global_stats(self) -> GlobalStats:
        return GlobalStats(
            self._encounter_summaries,
            self._pickup_items,
            self.current_shiny_phase,
            self._longest_shiny_phase,
            self._shortest_shiny_phase,
        )

    def get_encounter_log(self) -> list[Encounter]:
        return list(self._query_encounters())

    def get_shiny_phase_by_shiny(self, shiny_pokemon: Pokemon) -> ShinyPhase | None:
        return self._query_single_shiny_phase("encounters.personality_value = ?", (shiny_pokemon.personality_value,))

    def get_shiny_log(self) -> list[ShinyPhase]:
        return list(self._query_shiny_phases("end_time IS NOT NULL ORDER BY end_time DESC"))

    def _query_encounters(
        self,
        where_clause: str | None = None,
        parameters: tuple | list | None = None,
        limit: int | None = 10,
        offset: int = 0,
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
                type,
                outcome,
                data
            FROM encounters
            {f'WHERE {where_clause}' if where_clause is not None else ''}
            ORDER BY encounter_id DESC
            {f'LIMIT {limit} OFFSET {offset}' if limit is not None else ''}
            """,
            [] if parameters is None else parameters,
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
        return self._query_single_shiny_phase("end_time IS NULL ORDER BY shiny_phases.shiny_phase_id DESC")

    def _get_shiny_phase_by_id(self, shiny_phase_id: int) -> ShinyPhase | None:
        return self._query_single_shiny_phase("shiny_phases.shiny_phase_id = ?", (shiny_phase_id,))

    def _get_shortest_shiny_phase(self) -> ShinyPhase | None:
        return self._query_single_shiny_phase("end_time IS NOT NULL ORDER BY encounters ASC")

    def _get_longest_shiny_phase(self) -> ShinyPhase | None:
        return self._query_single_shiny_phase("end_time IS NOT NULL ORDER BY encounters DESC")

    def _query_shiny_phases(
        self, where_clause: str, parameters: tuple | list | None = None, limit: int | None = 10, offset: int = 0
    ) -> Iterable[ShinyPhase]:
        result = self._cursor.execute(
            f"""
            SELECT
                shiny_phases.shiny_phase_id,
                shiny_phases.start_time,
                shiny_phases.end_time,
                shiny_phases.shiny_encounter_id,
                shiny_phases.encounters,
                shiny_phases.highest_iv_sum,
                shiny_phases.highest_iv_sum_species,
                shiny_phases.lowest_iv_sum,
                shiny_phases.lowest_iv_sum_species,
                shiny_phases.highest_sv,
                shiny_phases.highest_sv_species,
                shiny_phases.lowest_sv,
                shiny_phases.lowest_sv_species,
                shiny_phases.longest_streak,
                shiny_phases.longest_streak_species,
                shiny_phases.current_streak,
                shiny_phases.current_streak_species,
                shiny_phases.fishing_attempts,
                shiny_phases.successful_fishing_attempts,
                shiny_phases.longest_unsuccessful_fishing_streak,
                shiny_phases.current_unsuccessful_fishing_streak,
                shiny_phases.snapshot_total_encounters,
                shiny_phases.snapshot_total_shiny_encounters,
                shiny_phases.snapshot_species_encounters,
                shiny_phases.snapshot_species_shiny_encounters,
                
                encounters.encounter_id,
                encounters.species_id,
                encounters.personality_value,
                encounters.shiny_phase_id,
                encounters.is_shiny,
                encounters.is_roamer,
                encounters.matching_custom_catch_filters,
                encounters.encounter_time,
                encounters.map,
                encounters.coordinates,
                encounters.bot_mode,
                encounters.type,
                encounters.outcome,
                encounters.data
            FROM shiny_phases
            LEFT JOIN encounters ON encounters.encounter_id = shiny_phases.shiny_encounter_id
            {f'WHERE {where_clause}' if where_clause is not None else ''}
            {f'LIMIT {limit} OFFSET {offset}' if limit is not None else ''}
            """,
            [] if parameters is None else parameters,
        )

        for row in result:
            if row[25] is not None:
                encounter = Encounter.from_row_data(row[25:])
            else:
                encounter = None

            yield ShinyPhase.from_row_data(row[:25], encounter)

    def _query_single_shiny_phase(self, where_clause: str, parameters: tuple | None = None) -> ShinyPhase | None:
        result = list(self._query_shiny_phases(where_clause, parameters, limit=1))
        return result[0] if len(result) > 0 else None

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

    def _get_base_data(self) -> dict[DataKey, str | None]:
        data_list = {}
        result = self._cursor.execute("SELECT data_key, value FROM base_data ORDER BY data_key")
        for row in result:
            data_list[DataKey(row[0])] = row[1]
        return data_list

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
                (encounter_id, species_id, personality_value, shiny_phase_id, is_shiny, matching_custom_catch_filters, encounter_time, map, coordinates, bot_mode, type, outcome, data)
            VALUES
                (?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?, ?)
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
                encounter.type.value if encounter.type else None,
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
                highest_iv_sum_species = ?,
                lowest_iv_sum = ?,
                lowest_iv_sum_species = ?,
                highest_sv = ?,
                highest_sv_species = ?,
                lowest_sv = ?,
                lowest_sv_species = ?,
                longest_streak = ?,
                longest_streak_species = ?,
                current_streak = ?,
                current_streak_species = ?,
                fishing_attempts = ?,
                successful_fishing_attempts = ?,
                longest_unsuccessful_fishing_streak = ?,
                current_unsuccessful_fishing_streak = ?,
                snapshot_total_encounters = ?,
                snapshot_total_shiny_encounters = ?,
                snapshot_species_encounters = ?,
                snapshot_species_shiny_encounters = ?
            WHERE shiny_phase_id = ?
            """,
            (
                shiny_phase.encounters,
                shiny_phase.highest_iv_sum,
                shiny_phase.highest_iv_sum_species.index if shiny_phase.highest_iv_sum_species is not None else None,
                shiny_phase.lowest_iv_sum,
                shiny_phase.lowest_iv_sum_species.index if shiny_phase.lowest_iv_sum_species is not None else None,
                shiny_phase.highest_sv,
                shiny_phase.highest_sv_species.index if shiny_phase.highest_sv_species is not None else None,
                shiny_phase.lowest_sv,
                shiny_phase.lowest_sv_species.index if shiny_phase.lowest_sv_species is not None else None,
                shiny_phase.longest_streak,
                shiny_phase.longest_streak_species.index if shiny_phase.longest_streak_species is not None else None,
                shiny_phase.current_streak,
                shiny_phase.current_streak_species.index if shiny_phase.current_streak_species is not None else None,
                shiny_phase.fishing_attempts,
                shiny_phase.successful_fishing_attempts,
                shiny_phase.longest_unsuccessful_fishing_streak,
                shiny_phase.current_unsuccessful_fishing_streak,
                shiny_phase.snapshot_total_encounters,
                shiny_phase.snapshot_total_shiny_encounters,
                shiny_phase.snapshot_species_encounters,
                shiny_phase.snapshot_species_shiny_encounters,
                shiny_phase.shiny_phase_id,
            ),
        )

    def _reset_phase_in_database(self, encounter: Encounter) -> None:
        """
        Resets phase-specific information for `shiny_phases` and `encounter_summaries` table.
        :param encounter: Shiny encounter that ended the phase.
        """

        self._cursor.execute(
            "UPDATE shiny_phases SET end_time = ?, shiny_encounter_id = ? WHERE shiny_phase_id = ?",
            (encounter.encounter_time, encounter.encounter_id, self.current_shiny_phase.shiny_phase_id),
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

        from modules.stats_migrate import migrate_file_based_stats_to_sqlite

        migrate_file_based_stats_to_sqlite(
            profile,
            self._insert_encounter,
            self._insert_shiny_phase,
            self._update_shiny_phase,
            self._insert_or_update_encounter_summary,
            self._get_encounter_summaries,
            self._query_encounters,
            self._query_shiny_phases,
            self._cursor.execute,
            self._connection.commit,
        )

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
                dedent(
                    """
                    CREATE TABLE base_data (
                        data_key INT UNSIGNED PRIMARY KEY,
                        value TEXT DEFAULT NULL
                    )
                    """
                )
            )

            self._cursor.execute(
                dedent(
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
            )

            self._cursor.execute(
                dedent(
                    """
                    CREATE TABLE shiny_phases (
                        shiny_phase_id INT UNSIGNED PRIMARY KEY,
                        start_time DATETIME NOT NULL,
                        end_time DATETIME DEFAULT NULL,
                        shiny_encounter_id INT UNSIGNED DEFAULT NULL,
                        encounters INT UNSIGNED DEFAULT 0,
                        highest_iv_sum INT UNSIGNED DEFAULT NULL,
                        highest_iv_sum_species INT UNSIGNED DEFAULT NULL,
                        lowest_iv_sum INT UNSIGNED DEFAULT NULL,
                        lowest_iv_sum_species INT UNSIGNED DEFAULT NULL,
                        highest_sv INT UNSIGNED DEFAULT NULL,
                        highest_sv_species INT UNSIGNED DEFAULT NULL,
                        lowest_sv INT UNSIGNED DEFAULT NULL,
                        lowest_sv_species INT UNSIGNED DEFAULT NULL,
                        longest_streak INT UNSIGNED DEFAULT 0,
                        longest_streak_species INT UNSIGNED DEFAULT NULL,
                        current_streak INT UNSIGNED DEFAULT 0,
                        current_streak_species INT UNSIGNED DEFAULT NULL,
                        fishing_attempts INT UNSIGNED DEFAULT 0,
                        successful_fishing_attempts INT UNSIGNED DEFAULT 0,
                        longest_unsuccessful_fishing_streak INT UNSIGNED DEFAULT 0,
                        current_unsuccessful_fishing_streak INT UNSIGNED DEFAULT 0,
                        snapshot_total_encounters INT UNSIGNED DEFAULT NULL,
                        snapshot_total_shiny_encounters INT UNSIGNED DEFAULT NULL,
                        snapshot_species_encounters INT UNSIGNED DEFAULT NULL,
                        snapshot_species_shiny_encounters INT UNSIGNED DEFAULT NULL
                    )
                    """
                )
            )

            self._cursor.execute(
                dedent(
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
                        type TEXT DEFAULT NULL,
                        outcome INT UNSIGNED DEFAULT NULL,
                        data BLOB NOT NULL
                    )
                    """
                )
            )

            self._cursor.execute(
                dedent(
                    """
                    CREATE TABLE pickup_items (
                        item_id INT UNSIGNED PRIMARY KEY,
                        item_name TEXT NOT NULL,
                        times_picked_up INT NOT NULL DEFAULT 0
                    )
                    """
                )
            )

        self._cursor.execute("DELETE FROM schema_version")
        self._cursor.execute("INSERT INTO schema_version VALUES (?)", (current_schema_version,))
