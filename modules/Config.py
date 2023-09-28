import os
import sys

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


def LoadConfig(file: str, schema: str) -> dict:
    try:
        if os.path.exists(file):
            with open(file, mode='r', encoding='utf-8') as f:
                config = yaml.load(f)
                validate(config, yaml.load(schema))
                return config
    except:
        console.print_exception(show_locals=True)
        console.print('[bold red]Config file {} is invalid![/]'.format(file))
        sys.exit(1)

# Load general config
config_general = LoadConfig('config/general.yml', general_schema)

# Load logging config
config_logging = LoadConfig('config/logging.yml', logging_schema)

# Load battle config
config_battle = LoadConfig('config/battle.yml', battle_schema)

# Load Discord config
config_discord = LoadConfig('config/discord.yml', discord_schema)

# Load OBS config
config_obs = LoadConfig('config/obs.yml', obs_schema)

# Load cheat config
config_cheats = LoadConfig('config/cheats.yml', cheats_schema)
