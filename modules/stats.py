import copy
import json
import math
import sys
import time
import importlib
from threading import Thread
from datetime import datetime

from modules.console import print_stats
from modules.context import context
from modules.csv import log_encounter_to_csv
from modules.files import read_file, write_file
from modules.memory import get_game_state, GameState
from modules.pokemon import Pokemon


class TotalStats:
    def __init__(self):
        self.session_encounters: int = 0
        self.session_pokemon: list = []
        self.encounter_log: list[dict] = []
        self.encounter_timestamps: list = []
        self.cached_timestamp: str = ""
        self.cached_encounter_rate: int = 0

        try:
            self.config_dir_path = context.profile.path
            self.stats_dir_path = context.profile.path / "stats"
            if not self.stats_dir_path.exists():
                self.stats_dir_path.mkdir()

            self.files = {
                "shiny_log": self.stats_dir_path / "shiny_log.json",
                "totals": self.stats_dir_path / "totals.json",
            }

            if (self.config_dir_path / "customcatchfilters.py").is_file():
                self.custom_catch_filters = importlib.import_module(
                    ".customcatchfilters", f"profiles.{context.profile.path.name}"
                ).custom_catch_filters
            else:
                from profiles.customcatchfilters import custom_catch_filters

                self.custom_catch_filters = custom_catch_filters

            if (self.config_dir_path / "customhooks.py").is_file():
                self.custom_hooks = importlib.import_module(
                    ".customhooks", f"profiles.{context.profile.path.name}"
                ).custom_hooks
            else:
                from profiles.customhooks import custom_hooks

                self.custom_hooks = custom_hooks

            f_total_stats = read_file(self.files["totals"])
            self.total_stats = json.loads(f_total_stats) if f_total_stats else {}

            f_shiny_log = read_file(self.files["shiny_log"])
            self.shiny_log = json.loads(f_shiny_log) if f_shiny_log else {"shiny_log": []}
        except SystemExit:
            raise
        except:
            sys.exit(1)

    def append_encounter_timestamps(self) -> None:
        self.encounter_timestamps.append(time.time())
        if len(self.encounter_timestamps) > 100:
            self.encounter_timestamps = self.encounter_timestamps[-100:]

    def append_encounter_log(self, pokemon: Pokemon) -> None:
        self.encounter_log.append(self.get_log_obj(pokemon))
        if len(self.encounter_log) > 10:
            self.encounter_log = self.encounter_log[-10:]

    def append_shiny_log(self, pokemon: Pokemon) -> None:
        self.shiny_log["shiny_log"].append(self.get_log_obj(pokemon))
        write_file(self.files["shiny_log"], json.dumps(self.shiny_log, indent=4, sort_keys=True))

    def get_total_stats(self) -> dict:
        return self.total_stats

    def get_encounter_log(self) -> list:
        return self.encounter_log

    def get_shiny_log(self) -> list:
        return self.shiny_log["shiny_log"]

    def get_encounter_rate(self) -> int:
        if len(self.encounter_timestamps) > 1 and self.session_encounters > 1:
            if self.cached_timestamp != self.encounter_timestamps[-1]:
                self.cached_timestamp = self.encounter_timestamps[-1]
                encounter_rate = int(
                    (
                        3600000
                        / (
                            (
                                self.encounter_timestamps[-1]
                                - self.encounter_timestamps[
                                    -min(self.session_encounters, len(self.encounter_timestamps))
                                ]
                            )
                            * 1000
                        )
                    )
                    * (min(self.session_encounters, len(self.encounter_timestamps)))
                )
                self.cached_encounter_rate = encounter_rate
                return encounter_rate
            else:
                return self.cached_encounter_rate
        return 0

    def update_incremental_stats(self, pokemon: Pokemon) -> None:
        self.session_encounters += 1
        self.session_pokemon.append(pokemon.species.name)
        self.session_pokemon = list(set(self.session_pokemon))
        self.total_stats["totals"]["encounters"] = self.total_stats["totals"].get("encounters", 0) + 1
        self.total_stats["totals"]["phase_encounters"] = self.total_stats["totals"].get("phase_encounters", 0) + 1
        self.total_stats["pokemon"][pokemon.species.name]["encounters"] = (
            self.total_stats["pokemon"][pokemon.species.name].get("encounters", 0) + 1
        )
        self.total_stats["pokemon"][pokemon.species.name]["phase_encounters"] = (
            self.total_stats["pokemon"][pokemon.species.name].get("phase_encounters", 0) + 1
        )
        self.total_stats["pokemon"][pokemon.species.name]["last_encounter_time_unix"] = time.time()
        self.total_stats["pokemon"][pokemon.species.name]["last_encounter_time_str"] = str(datetime.now())

    def update_shiny_incremental_stats(self, pokemon: Pokemon) -> None:
        self.total_stats["pokemon"][pokemon.species.name]["shiny_encounters"] = (
            self.total_stats["pokemon"][pokemon.species.name].get("shiny_encounters", 0) + 1
        )
        self.total_stats["totals"]["shiny_encounters"] = self.total_stats["totals"].get("shiny_encounters", 0) + 1

    def update_phase_records(self, pokemon: Pokemon) -> None:
        # Total longest phase
        if self.total_stats["totals"]["phase_encounters"] > self.total_stats["totals"].get(
            "longest_phase_encounters", 0
        ):
            self.total_stats["totals"]["longest_phase_encounters"] = self.total_stats["totals"]["phase_encounters"]
            self.total_stats["totals"]["longest_phase_pokemon"] = pokemon.species.name

        # Total shortest phase
        if (
            not self.total_stats["totals"].get("shortest_phase_encounters", None)
            or self.total_stats["totals"]["phase_encounters"] <= self.total_stats["totals"]["shortest_phase_encounters"]
        ):
            self.total_stats["totals"]["shortest_phase_encounters"] = self.total_stats["totals"]["phase_encounters"]
            self.total_stats["totals"]["shortest_phase_pokemon"] = pokemon.species.name

    def reset_phase_stats(self) -> None:
        # Reset phase stats
        self.session_pokemon = []
        self.total_stats["totals"].pop("phase_encounters", None)
        self.total_stats["totals"].pop("phase_highest_sv", None)
        self.total_stats["totals"].pop("phase_highest_sv_pokemon", None)
        self.total_stats["totals"].pop("phase_lowest_sv", None)
        self.total_stats["totals"].pop("phase_lowest_sv_pokemon", None)
        self.total_stats["totals"].pop("phase_highest_iv_sum", None)
        self.total_stats["totals"].pop("phase_highest_iv_sum_pokemon", None)
        self.total_stats["totals"].pop("phase_lowest_iv_sum", None)
        self.total_stats["totals"].pop("phase_lowest_iv_sum_pokemon", None)
        self.total_stats["totals"].pop("current_streak", None)
        self.total_stats["totals"].pop("phase_streak", None)
        self.total_stats["totals"].pop("phase_streak_pokemon", None)

        # Reset Pokémon phase stats
        for n in self.total_stats["pokemon"]:
            self.total_stats["pokemon"][n].pop("phase_encounters", None)
            self.total_stats["pokemon"][n].pop("phase_highest_sv", None)
            self.total_stats["pokemon"][n].pop("phase_lowest_sv", None)
            self.total_stats["pokemon"][n].pop("phase_highest_iv_sum", None)
            self.total_stats["pokemon"][n].pop("phase_lowest_iv_sum", None)

    def update_sv_records(self, pokemon: Pokemon) -> None:
        # Pokémon phase highest shiny value
        if not self.total_stats["pokemon"][pokemon.species.name].get("phase_highest_sv", None):
            self.total_stats["pokemon"][pokemon.species.name]["phase_highest_sv"] = pokemon.shiny_value
        else:
            self.total_stats["pokemon"][pokemon.species.name]["phase_highest_sv"] = max(
                pokemon.shiny_value, self.total_stats["pokemon"][pokemon.species.name].get("phase_highest_sv", -1)
            )

        # Pokémon phase lowest shiny value
        if not self.total_stats["pokemon"][pokemon.species.name].get("phase_lowest_sv", None):
            self.total_stats["pokemon"][pokemon.species.name]["phase_lowest_sv"] = pokemon.shiny_value
        else:
            self.total_stats["pokemon"][pokemon.species.name]["phase_lowest_sv"] = min(
                pokemon.shiny_value, self.total_stats["pokemon"][pokemon.species.name].get("phase_lowest_sv", 65536)
            )

        # Pokémon total lowest shiny value
        if not self.total_stats["pokemon"][pokemon.species.name].get("total_lowest_sv", None):
            self.total_stats["pokemon"][pokemon.species.name]["total_lowest_sv"] = pokemon.shiny_value
        else:
            self.total_stats["pokemon"][pokemon.species.name]["total_lowest_sv"] = min(
                pokemon.shiny_value, self.total_stats["pokemon"][pokemon.species.name].get("total_lowest_sv", 65536)
            )

        # Phase highest shiny value
        if not self.total_stats["totals"].get("phase_highest_sv", None):
            self.total_stats["totals"]["phase_highest_sv"] = pokemon.shiny_value
            self.total_stats["totals"]["phase_highest_sv_pokemon"] = pokemon.species.name
        elif pokemon.shiny_value >= self.total_stats["totals"].get("phase_highest_sv", -1):
            self.total_stats["totals"]["phase_highest_sv"] = pokemon.shiny_value
            self.total_stats["totals"]["phase_highest_sv_pokemon"] = pokemon.species.name

        # Phase lowest shiny value
        if not self.total_stats["totals"].get("phase_lowest_sv", None):
            self.total_stats["totals"]["phase_lowest_sv"] = pokemon.shiny_value
            self.total_stats["totals"]["phase_lowest_sv_pokemon"] = pokemon.species.name
        elif pokemon.shiny_value <= self.total_stats["totals"].get("phase_lowest_sv", 65536):
            self.total_stats["totals"]["phase_lowest_sv"] = pokemon.shiny_value
            self.total_stats["totals"]["phase_lowest_sv_pokemon"] = pokemon.species.name

    def update_iv_records(self, pokemon: Pokemon) -> None:
        # Pokémon highest phase IV record
        if not self.total_stats["pokemon"][pokemon.species.name].get(
            "phase_highest_iv_sum"
        ) or pokemon.ivs.sum() >= self.total_stats["pokemon"][pokemon.species.name].get("phase_highest_iv_sum", -1):
            self.total_stats["pokemon"][pokemon.species.name]["phase_highest_iv_sum"] = pokemon.ivs.sum()

        # Pokémon highest total IV record
        if pokemon.ivs.sum() >= self.total_stats["pokemon"][pokemon.species.name].get("total_highest_iv_sum", -1):
            self.total_stats["pokemon"][pokemon.species.name]["total_highest_iv_sum"] = pokemon.ivs.sum()

        # Pokémon lowest phase IV record
        if not self.total_stats["pokemon"][pokemon.species.name].get(
            "phase_lowest_iv_sum"
        ) or pokemon.ivs.sum() <= self.total_stats["pokemon"][pokemon.species.name].get("phase_lowest_iv_sum", 999):
            self.total_stats["pokemon"][pokemon.species.name]["phase_lowest_iv_sum"] = pokemon.ivs.sum()

        # Pokémon lowest total IV record
        if pokemon.ivs.sum() <= self.total_stats["pokemon"][pokemon.species.name].get("total_lowest_iv_sum", 999):
            self.total_stats["pokemon"][pokemon.species.name]["total_lowest_iv_sum"] = pokemon.ivs.sum()

        # Phase highest IV sum record
        if not self.total_stats["totals"].get("phase_highest_iv_sum") or pokemon.ivs.sum() >= self.total_stats[
            "totals"
        ].get("phase_highest_iv_sum", -1):
            self.total_stats["totals"]["phase_highest_iv_sum"] = pokemon.ivs.sum()
            self.total_stats["totals"]["phase_highest_iv_sum_pokemon"] = pokemon.species.name

        # Phase lowest IV sum record
        if not self.total_stats["totals"].get("phase_lowest_iv_sum") or pokemon.ivs.sum() <= self.total_stats[
            "totals"
        ].get("phase_lowest_iv_sum", 999):
            self.total_stats["totals"]["phase_lowest_iv_sum"] = pokemon.ivs.sum()
            self.total_stats["totals"]["phase_lowest_iv_sum_pokemon"] = pokemon.species.name

        # Total highest IV sum record
        if pokemon.ivs.sum() >= self.total_stats["totals"].get("highest_iv_sum", -1):
            self.total_stats["totals"]["highest_iv_sum"] = pokemon.ivs.sum()
            self.total_stats["totals"]["highest_iv_sum_pokemon"] = pokemon.species.name

        # Total lowest IV sum record
        if pokemon.ivs.sum() <= self.total_stats["totals"].get("lowest_iv_sum", 999):
            self.total_stats["totals"]["lowest_iv_sum"] = pokemon.ivs.sum()
            self.total_stats["totals"]["lowest_iv_sum_pokemon"] = pokemon.species.name

    def update_shiny_averages(self, pokemon: Pokemon) -> None:
        # Pokémon shiny average
        if self.total_stats["pokemon"][pokemon.species.name].get("shiny_encounters"):
            avg = int(
                math.floor(
                    self.total_stats["pokemon"][pokemon.species.name]["encounters"]
                    / self.total_stats["pokemon"][pokemon.species.name]["shiny_encounters"]
                )
            )
            self.total_stats["pokemon"][pokemon.species.name]["shiny_average"] = f"1/{avg:,}"

        # Total shiny average
        if self.total_stats["totals"].get("shiny_encounters"):
            avg = int(
                math.floor(self.total_stats["totals"]["encounters"] / self.total_stats["totals"]["shiny_encounters"])
            )
            self.total_stats["totals"]["shiny_average"] = f"1/{avg:,}"

    def update_same_pokemon_streak_record(self, pokemon: Pokemon) -> None:
        # Same Pokémon encounter streak records
        if len(self.encounter_log) > 1 and self.encounter_log[-2]["pokemon"]["name"] == pokemon.species.name:
            self.total_stats["totals"]["current_streak"] = self.total_stats["totals"].get("current_streak", 0) + 1
        else:
            self.total_stats["totals"]["current_streak"] = 1
        if self.total_stats["totals"].get("current_streak", 0) >= self.total_stats["totals"].get("phase_streak", 0):
            self.total_stats["totals"]["phase_streak"] = self.total_stats["totals"].get("current_streak", 0)
            self.total_stats["totals"]["phase_streak_pokemon"] = pokemon.species.name

    def get_log_obj(self, pokemon: Pokemon) -> dict:
        return {
            "time_encountered": time.time(),
            "pokemon": pokemon.to_dict(),
            "snapshot_stats": {
                "phase_encounters": self.total_stats["totals"]["phase_encounters"],
                "species_encounters": self.total_stats["pokemon"][pokemon.species.name]["encounters"],
                "species_shiny_encounters": self.total_stats["pokemon"][pokemon.species.name].get(
                    "shiny_encounters", 0
                ),
                "total_encounters": self.total_stats["totals"]["encounters"],
                "total_shiny_encounters": self.total_stats["totals"].get("shiny_encounters", 0),
            },
        }

    def log_encounter(self, pokemon: Pokemon, block_list: list, custom_filter_result: str | bool) -> None:
        if "pokemon" not in self.total_stats:
            self.total_stats["pokemon"] = {}
        if "totals" not in self.total_stats:
            self.total_stats["totals"] = {}

        if pokemon.species.name not in self.total_stats["pokemon"]:  # Set up a Pokémon stats if first encounter
            self.total_stats["pokemon"].update({pokemon.species.name: {}})

        self.update_incremental_stats(pokemon)
        self.update_sv_records(pokemon)
        self.update_iv_records(pokemon)

        if context.config.logging.log_encounters:
            log_encounter_to_csv(self.total_stats, pokemon.to_dict(), self.stats_dir_path)

        self.update_shiny_averages(pokemon)
        self.append_encounter_timestamps()
        self.append_encounter_log(pokemon)
        self.update_same_pokemon_streak_record(pokemon)

        if pokemon.is_shiny:
            self.append_shiny_log(pokemon)
            self.update_shiny_incremental_stats(pokemon)

            #  TODO fix all this OBS crap
            for i in range(context.config.obs.get("shiny_delay", 1)):
                context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)

            if context.config.obs.screenshot:
                from modules.obs import obs_hot_key

                while get_game_state() != GameState.BATTLE:
                    context.emulator.press_button("B")  # Throw out Pokémon for screenshot
                    context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
                for i in range(180):
                    context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
                obs_hot_key("OBS_KEY_F11", pressCtrl=True)

        print_stats(self.total_stats, pokemon, self.session_pokemon, self.get_encounter_rate())

        # Run custom code in custom_hooks in a thread
        hook = (
            Pokemon(pokemon.data),
            copy.deepcopy(self.total_stats),
            copy.deepcopy(block_list),
            copy.deepcopy(custom_filter_result),
        )
        Thread(target=self.custom_hooks, args=(hook,)).start()

        if pokemon.is_shiny:
            self.update_phase_records(pokemon)
            self.reset_phase_stats()

        # Save stats file
        write_file(self.files["totals"], json.dumps(self.total_stats, indent=4, sort_keys=True))


total_stats = TotalStats()
