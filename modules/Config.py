import os
from jsonschema import validate
from ruamel.yaml import YAML
from modules.Console import console

yaml = YAML()

config_schema = """
type: object
properties:
    bot_mode:
        type: string
        enum:
            - spin
            - starters
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
    fossil:
        type: string
        enum:
            - anorith
            - lileep
    autosave_encounters:
        type: integer
        minimum: 0
    backup_stats:
        type: integer
        minimum: 0
    auto_catch:
        type: boolean
    use_spore:
        type: boolean
    catch_shinies:
        type: boolean
    battle:
        type: boolean
    deoxys_puzzle_solved:
        type: boolean
    auto_stop:
        type: boolean
    save_game_after_catch:
        type: boolean
    pickup:
        type: boolean
    pickup_threshold:
        type: integer
        minimum: 1
        maximum: 6
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
    discord:
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
    banned_moves:
        type: array
        uniqueItems: true
        items:
            type: string
    mem_hacks:
        type: object
        properties:
            starters:
                type: boolean
"""

file = 'config.yml'
try:
    if os.path.exists(file):
        with open(file, mode='r', encoding='utf-8') as f:
            config_yml = yaml.load(f)
            validate(config_yml, yaml.load(config_schema))
            config = config_yml
            console.print('\nConfig file is valid!')
except Exception:
    console.print_exception()
    console.print('[bold red]Config file is invalid![/]')
    input('Press enter to exit...')
    os._exit(1)
