import copy
import json
import math
import sys
import time
import random
import importlib
from collections import deque
from threading import Thread
from datetime import datetime
from collections import Counter

from modules.console import console, print_stats
from modules.context import context
from modules.csv import log_encounter_to_csv
from modules.discord import discord_message
from modules.files import read_file, write_file
from modules.memory import get_game_state, GameState
from modules.pokemon import Pokemon
from modules.runtime import get_sprites_path
from modules.state_cache import state_cache


class TotalStats:
    def __init__(self):
        self.session_encounters: int = 0
        self.session_pokemon: set = set()
        self.discord_picked_up_items: dict = {}
        self.encounter_log: deque[dict] = deque(maxlen=10)
        self.encounter_timestamps: deque[float] = deque(maxlen=100)
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
            console.print_exception()
            sys.exit(1)

    def append_encounter_timestamps(self) -> None:
        self.encounter_timestamps.append(time.time())

    def append_encounter_log(self, pokemon: Pokemon) -> None:
        state_cache.last_encounter_log = self.encounter_log.pop() if self.encounter_log else None
        self.encounter_log.append(self.get_log_obj(pokemon))

    def append_shiny_log(self, pokemon: Pokemon) -> None:
        state_cache.last_shiny_log = self.shiny_log["shiny_log"].pop() if self.shiny_log["shiny_log"] else None
        self.shiny_log["shiny_log"].append(self.get_log_obj(pokemon))
        write_file(self.files["shiny_log"], json.dumps(self.shiny_log, indent=4, sort_keys=True))

    def get_session_encounters(self) -> int:
        return self.session_encounters

    def get_total_stats(self) -> dict:
        return self.total_stats

    def get_encounter_log(self) -> list:
        if state_cache.last_encounter_log.age_in_frames == 0:
            state_cache.last_encounter_log = self.encounter_log.pop() if self.encounter_log else None
        return list(self.encounter_log)

    def get_shiny_log(self) -> list:
        if state_cache.last_shiny_log.age_in_frames == 0:
            state_cache.last_shiny_log = self.shiny_log["shiny_log"].pop() if self.shiny_log["shiny_log"] else None
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
        self.session_pokemon.add(pokemon.species.name)
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
        self.session_pokemon.clear()
        self.total_stats["totals"]["phase_encounters"] = 0
        self.total_stats["totals"]["phase_highest_sv"] = None
        self.total_stats["totals"]["phase_highest_sv_pokemon"] = None
        self.total_stats["totals"]["phase_lowest_sv"] = None
        self.total_stats["totals"]["phase_lowest_sv_pokemon"] = None
        self.total_stats["totals"]["phase_highest_iv_sum"] = None
        self.total_stats["totals"]["phase_highest_iv_sum_pokemon"] = None
        self.total_stats["totals"]["phase_lowest_iv_sum"] = None
        self.total_stats["totals"]["phase_lowest_iv_sum_pokemon"] = None
        self.total_stats["totals"]["current_streak"] = 0
        self.total_stats["totals"]["phase_streak"] = 0
        self.total_stats["totals"]["phase_streak_pokemon"] = None

        # Reset Pokémon phase stats
        for n in self.total_stats["pokemon"]:
            self.total_stats["pokemon"][n]["phase_encounters"] = 0
            self.total_stats["pokemon"][n]["phase_highest_sv"] = None
            self.total_stats["pokemon"][n]["phase_lowest_sv"] = None
            self.total_stats["pokemon"][n]["phase_highest_iv_sum"] = None
            self.total_stats["pokemon"][n]["phase_lowest_iv_sum"] = None

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
        if (
            state_cache.last_encounter_log.value is not None
            and state_cache.last_encounter_log.value["pokemon"]["name"] == pokemon.species.name
        ):
            self.total_stats["totals"]["current_streak"] = self.total_stats["totals"].get("current_streak", 0) + 1
        else:
            self.total_stats["totals"]["current_streak"] = 1
        if self.total_stats["totals"].get("current_streak", 0) >= self.total_stats["totals"].get("phase_streak", 0):
            self.total_stats["totals"]["phase_streak"] = self.total_stats["totals"].get("current_streak", 0)
            self.total_stats["totals"]["phase_streak_pokemon"] = pokemon.species.name

    def get_log_obj(self, pokemon: Pokemon) -> dict:
        return {
            "time_encountered": time.time(),
            "pokemon": pokemon.to_legacy_dict(),
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
            self.total_stats["pokemon"][pokemon.species.name] = {}

        if self.total_stats["totals"].get("last_encounter_pid") == pokemon.personality_value:
            console.print(f"PID {str(hex(pokemon.personality_value)[2:]).upper()} was the last encounter logged, skipping...")
        else:
            self.total_stats["totals"]["last_encounter_pid"] = pokemon.personality_value
            self.update_incremental_stats(pokemon)
            self.update_sv_records(pokemon)
            self.update_iv_records(pokemon)

            if context.config.logging.log_encounters:
                log_encounter_to_csv(self.total_stats, pokemon.to_legacy_dict(), self.stats_dir_path)

            self.update_shiny_averages(pokemon)
            self.append_encounter_timestamps()
            self.append_encounter_log(pokemon)
            self.update_same_pokemon_streak_record(pokemon)

            if pokemon.is_shiny:
                self.append_shiny_log(pokemon)
                self.update_shiny_incremental_stats(pokemon)

                #  TODO fix all this OBS crap
                for i in range(context.config.obs.shiny_delay):
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

            # Run custom code/Discord webhooks in custom_hooks in a thread to not hold up bot
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

    def update_pickup_items(self, picked_up_items) -> None:
        self.total_stats["totals"]["pickup"] = self.total_stats["totals"].get("pickup", {})

        item_names = [i.name for i in picked_up_items]

        item_count = {}
        for item_name in item_names:
            item_count[item_name] = item_count.get(item_name, 0) + 1

        pickup_stats = {}
        for item, count in item_count.items():
            pickup_stats |= {f"{item}": count}

        self.total_stats["totals"]["pickup"] = Counter(self.total_stats["totals"]["pickup"]) + Counter(pickup_stats)

        # Save stats file
        write_file(self.files["totals"], json.dumps(self.total_stats, indent=4, sort_keys=True))

        if context.config.discord.pickup.enable:
            self.discord_picked_up_items = Counter(self.discord_picked_up_items) + Counter(item_count)

            if sum(self.discord_picked_up_items.values()) >= context.config.discord.pickup.interval:
                sprite_names = [i.sprite_name for i in picked_up_items]

                item_list = []
                for item, count in self.discord_picked_up_items.items():
                    item_list.append(f"{item} ({count})")

                self.discord_picked_up_items = {}

                def pickup_discord_webhook():
                    discord_ping = ""
                    match context.config.discord.pickup.ping_mode:
                        case "role":
                            discord_ping = f"📢 <@&{context.config.discord.pickup.ping_id}>"
                        case "user":
                            discord_ping = f"📢 <@{context.config.discord.pickup.ping_id}>"

                    discord_message(
                        webhook_url=context.config.discord.pickup.webhook_url,
                        content=discord_ping,
                        embed=True,
                        embed_title="🦝 Pickup notification",
                        embed_description="New items have been picked by your team!",
                        embed_fields={"Items:": "\n".join(item_list)},
                        embed_thumbnail=get_sprites_path() / "items" / f"{random.choice(sprite_names)}.png",
                        embed_color="fc6203",
                    )

                Thread(target=pickup_discord_webhook).start()


total_stats = TotalStats()
