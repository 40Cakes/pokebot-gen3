import sys
from pathlib import Path

from jsonschema import validate
from ruamel.yaml import YAML

from modules.console import console

yaml = YAML()

available_bot_modes = ["Manual", "Spin", "Starters", "Fishing", "Bunny Hop", "Rayquaza"]

general_schema = f"""
type: object
properties:
    starter:
        type: string
        enum:
            - Treecko
            - Torchic
            - Mudkip
            - Bulbasaur
            - Charmander
            - Squirtle
            - Chikorita
            - Totodile
            - Cyndaquil
"""

logging_schema = """
    log_encounters:
        type: boolean
    console:
        type: object
        properties:
            encounter_data:
                type: string
                enum:
                    - verbose
                    - basic
                    - disable
            encounter_ivs:
                type: string
                enum:
                    - verbose
                    - basic
                    - disable
            encounter_moves:
                type: string
                enum:
                    - verbose
                    - basic
                    - disable
            statistics:
                type: string
                enum:
                    - verbose
                    - basic
                    - disable
"""

battle_schema = """
type: object
properties:
    battle:
        type: boolean
    battle_method:
        type: string
        enum:
            - strongest
    pickup:
        type: boolean
    pickup_threshold:
        type: integer
        minimum: 1
        maximum: 6
    pickup_check_frequency:
        type: integer
        minimum: 1
    faint_action:
        type: string
        enum:
            - stop
            - flee
            - rotate
    new_move:
        type: string
        enum:
            - stop
            - cancel
            - learn_best
    stop_evolution:
        type: boolean
    replace_lead_battler:
        type: boolean
    switch_strategy:
        type: string
        enum:
            - first_available
    banned_moves:
        type: array
        uniqueItems: true
        items:
            type: string
"""

discord_schema = """
type: object
properties:
    rich_presence:
        type: boolean
    iv_format:
        type: string
        enum:
            - basic
            - formatted
    bot_id:
        type: string
    shiny_pokemon_encounter:
        type: object
        properties:
            enable:
                type: boolean
            ping_mode:
                enum:
                    - ~
                    - user
                    - role
    pokemon_encounter_milestones:
        type: object
        properties:
            enable:
                type: boolean
            interval:
                type: integer
                minimum: 0
            ping_mode:
                enum:
                    - ~
                    - user
                    - role
    total_encounter_milestones:
        type: object
        properties:
            enable:
                type: boolean
            interval:
                type: integer
                minimum: 0
            ping_mode:
                enum:
                    - ~
                    - user
                    - role
    phase_summary:
        type: object
        properties:
            enable:
                type: boolean
            first_interval:
                type: integer
                minimum: 0
            consequent_interval:
                type: integer
                minimum: 0
            ping_mode:
                enum:
                    - ~
                    - user
                    - role
    anti_shiny_pokemon_encounter:
        type: object
        properties:
            enable:
                type: boolean
            ping_mode:
                enum:
                    - ~
                    - user
                    - role
"""

obs_schema = """
type: object
properties:
    obs_websocket:
        type: object
        properties:
            host:
                type: string
            port: 
                type: integer
            password:
                type: string
    shiny_delay:
        type: integer
        minimum: 0
    discord_delay:
        type: integer
        minimum: 0
    screenshot:
        type: boolean
    replay_buffer:
        type: boolean
    replay_buffer_delay:
        type: integer
        minimum: 0
    replay_dir:
        type: string
    http_server:
        type: object
        properties:
            enable:
                type: boolean
            ip: 
                type: string
            port:
                type: integer
"""

cheats_schema = """
type: object
properties:
    starters:
        type: boolean
    starters_rng:
        type: boolean
    pickup:
        type: boolean
"""

catch_block_schema = """
type: object
properties:
    block_list:
        type: array
"""

keys_schema = """
type: object
properties:
    gba:
        type: object
        properties:
            Up: {type: string}
            Down: {type: string}
            Left: {type: string}
            Right: {type: string}
            A: {type: string}
            B: {type: string}
            L: {type: string}
            R: {type: string}
            Start: {type: string}
            Select: {type: string}

    emulator:
        type: object
        properties:
            zoom_in: {type: string}
            zoom_out: {type: string}
            toggle_manual: {type: string}
            toggle_video: {type: string}
            toggle_audio: {type: string}
            set_speed_1x: {type: string}
            set_speed_2x: {type: string}
            set_speed_3x: {type: string}
            set_speed_4x: {type: string}
            toggle_unthrottled: {type: string}
            reset: {type: string}
            exit: {type: string}
            save_state: {type: string}
            toggle_stepping_mode: {type: string}
"""

schemas = {
    "general": general_schema,
    "logging": logging_schema,
    "battle": battle_schema,
    "discord": discord_schema,
    "obs": obs_schema,
    "cheats": cheats_schema,
}

config = {"general": {}, "logging": {}, "battle": {}, "discord": {}, "obs": {}, "cheats": {}}

# Keeps a list of all configuration directories that should be searched whenever we are looking
# for a particular config file.
# In practice, this will contain the global `profiles/` directory, and the profile-specific config
# directory (`profiles/<profile name>/config/`) once a profile has been selected by the user.
config_dir_stack: list[Path] = []


def load_config(file_name: str, schema: str) -> dict:
    """
    Looks for and loads a single config file and returns its parsed contents.

    If the config file cannot be found, it stops the bot.

    :param file_name: File name (without path) of the config file
    :param schema: JSON Schema string to validate the configuration dict against
    :return: Parsed and validated contents of the configuration file
    """
    result = None
    for config_dir in config_dir_stack:
        file_path = config_dir / file_name
        if file_path.is_file():
            result = load_config_file(file_path, schema)

    if result is None:
        console.print(f"[bold red]Could not find any config file named {file_name}.[/]")
        sys.exit(1)

    return result


def load_config_file(file_path: Path, schema: str) -> dict:
    """
    Loads and validates a single config file. This requires an exact path and therefore will not
    fall back to the global config directory if the file could not be found.

    It will stop the bot if the file does not exist or contains invalid data.

    :param file_path: Path to the config file
    :param schema: JSON Schema string to validate the configuration dict against
    :return: Parsed and validated contents of the configuration file
    """
    try:
        with open(file_path, mode="r", encoding="utf-8") as f:
            config = yaml.load(f)
            validate(config, yaml.load(schema))
            return config
    except:
        console.print(f"[bold red]Config file {str(file_path)} is invalid![/]")
        sys.exit(1)


def load_config_from_directory(path: Path, allow_missing_files=False) -> None:
    """
    Loads all the 'default' configuration files into the `config` variable that can be accessed by other modules.

    :param path: Path to the config directory.
    :param allow_missing_files: If this is False, the function will stop the bot if it cannot find a config file.
                                This should be used when loading the global configuration directory, but not when
                                loading the profile-specific config directory (so that we use the profile-specific
                                config if it exists, but keep using the global one if it doesn't.)
    """
    global config_dir_stack, config

    config_dir_stack.append(path)

    for key in config:
        file_path = path / (key + ".yml")
        if file_path.is_file():
            config[key] = load_config_file(file_path, schemas[key])
        elif not allow_missing_files:
            console.print(f"[bold red]Expected a config file {str(file_path)} could not be found.[/]")
            sys.exit(1)
