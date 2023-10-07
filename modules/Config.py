import sys
from pathlib import Path

from jsonschema import validate
from ruamel.yaml import YAML

from modules.Console import console

yaml = YAML()

general_schema = """
type: object
properties:
    bot_mode:
        type: string
        enum:
            - manual
            - spin
            - starters
            - fishing
    coords:
        type: object
        properties:
            pos1:
                type: object
                properties:
                    x:
                        type: integer
                        minimum: 0
                    y:
                        type: integer
                        minimum: 0
            pos2:
                type: object
                properties:
                    x:
                        type: integer
                        minimum: 0
                    y:
                        type: integer
                        minimum: 0
    bonk_direction:
        type: string
        enum:
            - horizontal
            - vertical
    starter:
        type: string
        enum:
            - treecko
            - torchic
            - mudkip
            - bulbasaur
            - charmander
            - squirtle
            - chikorita
            - totodile
            - cyndaquil
    fossil:
        type: string
        enum:
            - anorith
            - lileep
    autosave_encounters:
        type: integer
        minimum: 0
    auto_catch:
        type: boolean
    use_spore:
        type: boolean
    catch_shinies:
        type: boolean
    deoxys_puzzle_solved:
        type: boolean
    auto_stop:
        type: boolean
    save_game_after_catch:
        type: boolean
    ball_priority:
        type: array
        uniqueItems: true
        items:
            type: string
            enum:
                - Dive Ball
                - Great Ball
                - Luxury Ball
                - Master Ball
                - Nest Ball
                - Poké Ball
                - Premier Ball
                - Repeat Ball
                - Timer Ball
                - Ultra Ball
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
    backup_stats:
        type: integer
        minimum: 0

"""

battle_schema = """
    battle:
        type: boolean
    pickup:
        type: boolean
    pickup_threshold:
        type: integer
        minimum: 1
        maximum: 6
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
"""

schemas = {
    'general': general_schema,
    'logging': logging_schema,
    'battle': battle_schema,
    'discord': discord_schema,
    'obs': obs_schema,
    'cheats': cheats_schema
}

config = {
    'general': {},
    'logging': {},
    'battle': {},
    'discord': {},
    'obs': {},
    'cheats': {}
}

# Keeps a list of all configuration directories that should be searched whenever we are looking
# for a particular config file.
# In practice, this will contain the global `config/` directory, and the profile-specific config
# directory (`config/<profile name>/config/`) once a profile has been selected by the user.
config_dir_stack: list[Path] = []


def LoadConfig(file_name: str, schema: str) -> dict:
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
            result = LoadConfigFile(file_path, schema)

    if result is None:
        console.print('[bold red]Could not find any config file named {}.[/]'.format(file_name))
        sys.exit(1)

    return result


def LoadConfigFile(file_path: Path, schema: str) -> dict:
    """
    Loads and validates a single config file. This requires an exact path and therefore will not
    fall back to the global config directory if the file could not be found.

    It will stop the bot if the file does not exist or contains invalid data.

    :param file_path: Path to the config file
    :param schema: JSON Schema string to validate the configuration dict against
    :return: Parsed and validated contents of the configuration file
    """
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            config = yaml.load(f)
            validate(config, yaml.load(schema))
            return config
    except:
        console.print_exception(show_locals=True)
        console.print('[bold red]Config file {} is invalid![/]'.format(str(file_path)))
        sys.exit(1)


def LoadConfigFromDirectory(path: Path, allow_missing_files=False) -> None:
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
        file_path = path / (key + '.yml')
        if file_path.is_file():
            config[key] = LoadConfigFile(file_path, schemas[key])
        elif not allow_missing_files:
            console.print('[bold red]Expected a config file {} could not be found.[/]'.format(str(file_path)))
            sys.exit(1)


previous_bot_mode: str = ''

def ToggleManualMode() -> None:
    """
    Toggles between manual mode and the bot mode configured in `general.yml`.
    If the configured bot mode is already `manual`, this has no effect.
    """
    global previous_bot_mode

    if config['general']['bot_mode'] == 'manual' and previous_bot_mode != '':
        config['general']['bot_mode'] = previous_bot_mode
        previous_bot_mode = ''
    else:
        previous_bot_mode = config['general']['bot_mode']
        config['general']['bot_mode'] = 'manual'


def ForceManualMode() -> None:
    """
    Ensures that the bot is running in manual mode, to give control back to
    the user. If the bot is already in manual mode, this has no effect.
    """
    global previous_bot_mode

    if config['general']['bot_mode'] != 'manual':
        previous_bot_mode = config['general']['bot_mode']

    config['general']['bot_mode'] = 'manual'
