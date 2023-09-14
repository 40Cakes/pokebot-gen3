import os
from jsonschema import validate
from ruamel.yaml import YAML
from modules.Console import console
from modules.Memory import mGBA, GetTrainer

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
            - mudkip
            - treecko
            - torchic
            - bulbasaur
            - charmander
            - squirtle
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
    webhooks:
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
    hotkey_screenshot:
        type: array
    hotkey_replay_buffer:
        type: array
    replay_dir:
        type: string
    phase_summary:
        type: object
        properties:
            server:
                type: string
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
        input('Press enter to exit...')
        os._exit(1)


safe_trainer_name = ''.join([c for c in GetTrainer()['name'] if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
trainer_dir = '{}/{}-{}'.format(
    mGBA.game_code,
    GetTrainer()['tid'],
    safe_trainer_name
)
config_dir = './config/{}'.format(trainer_dir)

if not os.path.exists(config_dir):
    os.makedirs(config_dir)

# Load general config
if os.path.isfile('{}/general.yml'.format(config_dir)):
    config_general = LoadConfig('{}/general.yml'.format(config_dir), general_schema)
else:
    config_general = LoadConfig('config/general.yml', general_schema)

# Load logging config
if os.path.isfile('{}/logging.yml'.format(config_dir)):
    config_logging = LoadConfig('{}/logging.yml'.format(config_dir), logging_schema)
else:
    config_logging = LoadConfig('config/logging.yml', logging_schema)

# Load battle config
if os.path.isfile('{}/battle.yml'.format(config_dir)):
    config_battle = LoadConfig('{}/battle.yml'.format(config_dir), battle_schema)
else:
    config_battle = LoadConfig('config/battle.yml', battle_schema)

# Load Discord config
if os.path.isfile('{}/discord.yml'.format(config_dir)):
    config_discord = LoadConfig('{}/discord.yml'.format(config_dir), discord_schema)
else:
    config_discord = LoadConfig('config/discord.yml', discord_schema)

# Load OBS config
if os.path.isfile('{}/obs.yml'.format(config_dir)):
    config_obs = LoadConfig('{}/obs.yml'.format(config_dir), obs_schema)
else:
    config_obs = LoadConfig('config/obs.yml', obs_schema)

# Load cheat config
if os.path.isfile('{}/cheats.yml'.format(config_dir)):
    config_cheats = LoadConfig('{}/cheats.yml'.format(config_dir), cheats_schema)
else:
    config_cheats = LoadConfig('config/cheats.yml', cheats_schema)
