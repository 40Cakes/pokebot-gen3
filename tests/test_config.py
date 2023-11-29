"""Unit tests to ensure config files are loaded properly."""

from pathlib import Path

import pytest

import pokebot as _  # We need this import here to ensure all modules are loaded in the right order.

from modules import config
from modules import exceptions

WEBHOOK_DEFAULTS = {
    "consequent_interval": 5000,
    "enable": False,
    "first_interval": 8192,
    "interval": 5,
    "ping_id": None,
    "ping_mode": None,
}
DEFAULT_CONFIG = {
    "catch_block": {"block_list": []},
    "cheats": {"starters": False, "starters_rng": False},
    "discord": {
        "anti_shiny_pokemon_encounter": WEBHOOK_DEFAULTS,
        "bot_id": "PokéBot",
        "global_webhook_url": "",
        "iv_format": "formatted",
        "phase_summary": WEBHOOK_DEFAULTS,
        "pokemon_encounter_milestones": {
            "consequent_interval": 5000,
            "enable": False,
            "first_interval": 8192,
            "interval": 10000,
            "ping_id": None,
            "ping_mode": None,
        },
        "rich_presence": False,
        "shiny_pokemon_encounter": WEBHOOK_DEFAULTS,
        "shiny_pokemon_encounter_milestones": WEBHOOK_DEFAULTS,
        "custom_filter_pokemon_encounter": WEBHOOK_DEFAULTS,
        "total_encounter_milestones": {
            "consequent_interval": 5000,
            "enable": False,
            "first_interval": 8192,
            "interval": 25000,
            "ping_id": None,
            "ping_mode": None,
        },
    },
    "general": {"starter": config.schemas_v1.Starters.MUDKIP},
    "keys": {
        "gba": {
            "Up": "Up",
            "Down": "Down",
            "Left": "Left",
            "Right": "Right",
            "A": "x",
            "B": "z",
            "L": "a",
            "R": "s",
            "Start": "Return",
            "Select": "BackSpace",
        },
        "emulator": {
            "zoom_in": "plus",
            "zoom_out": "minus",
            "toggle_manual": "Tab",
            "toggle_video": "v",
            "toggle_audio": "b",
            "set_speed_1x": "1",
            "set_speed_2x": "2",
            "set_speed_3x": "3",
            "set_speed_4x": "4",
            "set_speed_unthrottled": "0",
            "reload_config": "Ctrl+C",
            "reset": "Ctrl+R",
            "exit": "Ctrl+Q",
            "save_state": "Ctrl+S",
            "toggle_stepping_mode": "Ctrl+L",
        },
    },
    "logging": {
        "console": {
            "encounter_data": "verbose",
            "encounter_ivs": "verbose",
            "encounter_moves": "disable",
            "statistics": "verbose",
        },
        "import_pk3": False,
        "log_encounters": False,
        "save_pk3": {"all": False, "custom": False, "shiny": False},
    },
    "obs": {
        "discord_delay": 0,
        "discord_webhook_url": None,
        "http_server": {"enable": False, "ip": "127.0.0.1", "port": 8888},
        "obs_websocket": {"password": "password", "host": "127.0.0.1", "port": 4455},
        "replay_buffer": False,
        "replay_buffer_delay": 0,
        "replay_dir": "./stream/replays/",
        "screenshot": False,
        "shiny_delay": 0,
    },
}

CONFIG_TESTS = {
    "config_load": {
        "defaults load correctly": {"kwargs": {"config_dir": Path("tests")}, "expected": DEFAULT_CONFIG},
        "folder loads correctly": {
            "kwargs": {"config_dir": Path("tests") / "config"},
            "expected": DEFAULT_CONFIG.copy() | {"cheats": {"starters": True, "starters_rng": True}},
        },
        "profile loads correctly": {
            "kwargs": {"config_dir": (Path("tests") / "config") / "profile", "is_profile": True},
            "expected": DEFAULT_CONFIG.copy()
            | {
                "metadata": {
                    "rom": {
                        "file_name": "Pokemon - Emerald Version (U).gba",
                        "game_code": "BPE",
                        "language": "E",
                        "revision": 0,
                    },
                    "version": 1,
                }
            },
        },
        "is_profile but missing metadata": {
            "kwargs": {"config_dir": Path("tests") / "config", "is_profile": True},
            "raises": exceptions.CriticalFileMissing,
        },
        "missing file with strict = True": {
            "kwargs": {"config_dir": Path("tests") / "config", "strict": True},
            "raises": exceptions.CriticalFileMissing,
        },
    }
}


@pytest.mark.parametrize("tests", CONFIG_TESTS["config_load"].values(), ids=CONFIG_TESTS["config_load"].keys())
def test_config(test: dict) -> None:
    """Ensures the main config can be instanced and loads all children objects."""
    exception = test.get("raises")
    if exception:
        with pytest.raises(exception):
            _ = config.Config(**test["kwargs"])
    else:
        loaded_config = config.Config(**test["kwargs"])
        msg = "Attribute {} does not match the expected result: {}"
        for attribute, expected in test["expected"].items():
            assert getattr(loaded_config, attribute).model_dump() == expected, msg.format(attribute, expected)
