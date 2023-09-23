import os
import glob
import time
import random
import pydirectinput
from typing import NoReturn
from threading import Thread
from modules.Config import config_discord, config_obs
from modules.Console import console
from modules.Discord import DiscordMessage
from modules.Inputs import WaitFrames
from modules.Memory import mGBA


def CustomHooks(hook) -> NoReturn:
    """
    This function is called every time an encounter is logged, but before phase stats are reset (if shiny)
    this file is useful for custom webhooks or logging to external databases if you understand Python

    Note: this function runs in a thread and will not hold up the bot if you need to run any slow hooks
    """
    try:
        # Deep copy of Pokémon and stats dictionaries when the thread was called to avoid main thread overwriting vars
        pokemon = hook[0]
        stats = hook[1]

        ### Your custom code goes here ###

        # Discord messages
        if config_discord['webhooks']:
            from modules.Stats import GetEncounterRate

            def IVField() -> str:
                # Formatted IV table
                if config_discord['iv_format'] == 'formatted':
                    iv_field = '```' \
                               '╔═══╤═══╤═══╤═══╤═══╤═══╗\n' \
                               '║HP │ATK│DEF│SPA│SPD│SPE║\n' \
                               '╠═══╪═══╪═══╪═══╪═══╪═══╣\n' \
                               '║{:^3}│{:^3}│{:^3}│{:^3}│{:^3}│{:^3}║\n' \
                               '╚═══╧═══╧═══╧═══╧═══╧═══╝' \
                               '```'.format(
                        pokemon['IVs']['hp'],
                        pokemon['IVs']['attack'],
                        pokemon['IVs']['defense'],
                        pokemon['IVs']['spAttack'],
                        pokemon['IVs']['spDefense'],
                        pokemon['IVs']['speed'])
                else:
                    # Default to basic IV formatting
                    iv_field = 'HP: {} | ATK: {} | DEF: {} | SPATK: {} | SPDEF: {} | SPE: {}'.format(
                        pokemon['IVs']['hp'],
                        pokemon['IVs']['attack'],
                        pokemon['IVs']['defense'],
                        pokemon['IVs']['spAttack'],
                        pokemon['IVs']['spDefense'],
                        pokemon['IVs']['speed'])
                return iv_field

            try:
                # Discord shiny Pokémon encountered
                if config_discord['shiny_pokemon_encounter']['enable'] and pokemon['shiny']:
                    # Discord pings
                    discord_ping = ''
                    match config_discord['shiny_pokemon_encounter']['ping_mode']:
                        case 'role':
                            discord_ping = '📢 <@&{}>'.format(config_discord['shiny_pokemon_encounter']['ping_id'])
                        case 'user':
                            discord_ping = '📢 <@{}>'.format(config_discord['shiny_pokemon_encounter']['ping_id'])

                    # Load catch block config
                    from modules.Config import config_dir, catch_block_schema, LoadConfig
                    if os.path.isfile('{}/catch_block.yml'.format(config_dir)):
                        config_catch_block = LoadConfig('{}/catch_block.yml'.format(config_dir), catch_block_schema)
                    else:
                        config_catch_block = LoadConfig('config/catch_block.yml', catch_block_schema)

                    block = '\n❌Skipping catching shiny (on catch block list)!' \
                        if pokemon['name'] in config_catch_block['block_list'] else ''

                    DiscordMessage(
                        webhook_url=config_discord['shiny_pokemon_encounter'].get('webhook_url', None),
                        content='Encountered a shiny ✨ {} ✨! {}\n{}'.format(
                                pokemon['name'],
                                block,
                                discord_ping
                        ),
                        embed=True,
                        embed_title='Shiny encountered!',
                        embed_description='{} {} (Lv. {:,}) at {}!'.format(
                                        pokemon['nature'],
                                        pokemon['name'],
                                        pokemon['level'],
                                        pokemon['metLocation']),
                        embed_fields={
                            'Shiny Value': '{:,}'.format(pokemon['shinyValue']),
                            'IVs': IVField(),
                            '{} Encounters'.format(
                                            pokemon['name']): '{:,} ({:,}✨)'.format(
                                            stats['pokemon'][pokemon['name']].get('encounters', 0),
                                            stats['pokemon'][pokemon['name']].get('shiny_encounters', 0)),
                            '{} Phase Encounters'.format(
                                            pokemon['name']): '{:,}'.format(
                                            stats['pokemon'][pokemon['name']].get('phase_encounters', 0)),
                            'Phase Encounters': '{:,} ({:,}/h)'.format(
                                            stats['totals'].get('phase_encounters', 0),
                                            GetEncounterRate()),
                            'Phase IV Sum Records': ':arrow_up: `{:,}` IV {}\n:arrow_down: `{:,}` IV {}'.format(
                                            stats['totals'].get('phase_highest_iv_sum', 0),
                                            stats['totals'].get('phase_highest_iv_sum_pokemon', 'N/A'),
                                            stats['totals'].get('phase_lowest_iv_sum', 0),
                                            stats['totals'].get('phase_lowest_iv_sum_pokemon', 'N/A')),
                            'Phase SV Records': ':arrow_up: `{:,}` SV {}\n:arrow_down: `{:,}` SV ✨ {} ✨'.format(
                                            stats['totals'].get('phase_highest_sv', 0),
                                            stats['totals'].get('phase_highest_sv_pokemon', 'N/A'),
                                            stats['totals'].get('phase_lowest_sv', 0),
                                            stats['totals'].get('phase_lowest_sv_pokemon', 'N/A')),
                            'Phase Same Pokémon Streak': '{:,} {} were encountered in a row!'.format(
                                            stats['totals'].get('phase_streak', 0),
                                            stats['totals'].get('phase_streak_pokemon', 'N/A')),
                            'Total Encounters': '{:,} ({:,}✨)'.format(
                                            stats['totals'].get('encounters', 0),
                                            stats['totals'].get('shiny_encounters', 0))},
                        embed_thumbnail='./sprites/pokemon/shiny/{}.png'.format(
                                            pokemon['name']),
                        embed_footer='PokéBot ID: {} | {}'.format(
                            config_discord['bot_id'],
                            mGBA.game),
                        embed_color='ffd242')
            except:
                console.print_exception(show_locals=True)

            try:
                # Discord Pokémon encounter milestones
                if config_discord['pokemon_encounter_milestones']['enable'] and \
                stats['pokemon'][pokemon['name']].get('encounters', -1) % config_discord['pokemon_encounter_milestones'].get('interval', 0) == 0:
                    # Discord pings
                    discord_ping = ''
                    match config_discord['pokemon_encounter_milestones']['ping_mode']:
                        case 'role':
                            discord_ping = '📢 <@&{}>'.format(config_discord['pokemon_encounter_milestones']['ping_id'])
                        case 'user':
                            discord_ping = '📢 <@{}>'.format(config_discord['pokemon_encounter_milestones']['ping_id'])
                    DiscordMessage(
                        webhook_url=config_discord['pokemon_encounter_milestones'].get('webhook_url', None),
                        content='🎉 New milestone achieved!\n{}'.format(discord_ping),
                        embed=True,
                        embed_description='{:,} {} encounters!'.format(
                                        stats['pokemon'][pokemon['name']].get('encounters', 0),
                                        pokemon['name']),
                        embed_thumbnail='./sprites/pokemon/normal/{}.png'.format(
                                        pokemon['name']),
                        embed_footer='PokéBot ID: {} | {}'.format(
                            config_discord['bot_id'],
                            mGBA.game),
                        embed_color='50C878')
            except:
                console.print_exception(show_locals=True)

            try:
                # Discord shiny Pokémon encounter milestones
                if config_discord['shiny_pokemon_encounter_milestones']['enable'] and \
                pokemon['shiny'] and \
                stats['pokemon'][pokemon['name']].get('shiny_encounters', -1) % config_discord['shiny_pokemon_encounter_milestones'].get('interval', 0) == 0:
                    # Discord pings
                    discord_ping = ''
                    match config_discord['shiny_pokemon_encounter_milestones']['ping_mode']:
                        case 'role':
                            discord_ping = '📢 <@&{}>'.format(config_discord['shiny_pokemon_encounter_milestones']['ping_id'])
                        case 'user':
                            discord_ping = '📢 <@{}>'.format(config_discord['shiny_pokemon_encounter_milestones']['ping_id'])
                    DiscordMessage(
                        webhook_url=config_discord['shiny_pokemon_encounter_milestones'].get('webhook_url', None),
                        content='🎉 New milestone achieved!\n{}'.format(discord_ping),
                        embed=True,
                        embed_description='{:,} shiny ✨ {} ✨ encounters!'.format(
                                            stats['pokemon'][pokemon['name']].get('shiny_encounters', 0),
                                            pokemon['name']),
                        embed_thumbnail='./sprites/pokemon/shiny/{}.png'.format(
                                            pokemon['name']),
                        embed_footer='PokéBot ID: {} | {}'.format(
                            config_discord['bot_id'],
                            mGBA.game),
                        embed_color='ffd242')
            except:
                console.print_exception(show_locals=True)

            try:
                # Discord total encounter milestones
                if config_discord['total_encounter_milestones']['enable'] and \
                stats['totals'].get('encounters', -1) % config_discord['total_encounter_milestones'].get('interval', 0) == 0:
                    # Discord pings
                    discord_ping = ''
                    match config_discord['total_encounter_milestones']['ping_mode']:
                        case 'role':
                            discord_ping = '📢 <@&{}>'.format(config_discord['total_encounter_milestones']['ping_id'])
                        case 'user':
                            discord_ping = '📢 <@{}>'.format(config_discord['total_encounter_milestones']['ping_id'])
                    DiscordMessage(
                        webhook_url=config_discord['total_encounter_milestones'].get('webhook_url', None),
                        content='🎉 New milestone achieved!\n{}'.format(discord_ping),
                        embed=True,
                        embed_description='{:,} total encounters!'.format(
                                          stats['totals'].get('encounters', 0)),
                        embed_thumbnail='./sprites/items/{}.png'.format(
                            random.choice([
                                'Dive Ball',
                                'Great Ball',
                                'Light Ball',
                                'Luxury Ball',
                                'Master Ball',
                                'Nest Ball',
                                'Net Ball',
                                'Poké Ball',
                                'Premier Ball',
                                'Repeat Ball',
                                'Safari Ball',
                                'Smoke Ball',
                                'Timer Ball',
                                'Ultra Ball'])),
                        embed_footer='PokéBot ID: {} | {}'.format(
                            config_discord['bot_id'],
                            mGBA.game),
                        embed_color='50C878')
            except:
                console.print_exception(show_locals=True)

            try:
                # Discord phase encounter notifications
                if config_discord['phase_summary']['enable'] and \
                not pokemon['shiny'] and \
                (stats['totals'].get('phase_encounters', -1) == config_discord['phase_summary'].get('first_interval', 0) or
                (stats['totals'].get('phase_encounters', -1) > config_discord['phase_summary'].get('first_interval', 0) and
                stats['totals'].get('phase_encounters', -1) % config_discord['phase_summary'].get('consequent_interval', 0) == 0)):
                    # Discord pings
                    discord_ping = ''
                    match config_discord['phase_summary']['ping_mode']:
                        case 'role':
                            discord_ping = '📢 <@&{}>'.format(config_discord['phase_summary']['ping_id'])
                        case 'user':
                            discord_ping = '📢 <@{}>'.format(config_discord['phase_summary']['ping_id'])
                    DiscordMessage(
                        webhook_url=config_discord['phase_summary'].get('webhook_url', None),
                        content='💀 The current phase has reached {:,} encounters!\n{}'.format(
                                stats['totals'].get('phase_encounters', 0),
                                discord_ping),
                        embed=True,
                        embed_fields={
                            'Phase Encounters': '{:,} ({:,}/h)'.format(
                                                    stats['totals'].get('phase_encounters', 0),
                                                    GetEncounterRate()),
                            'Phase IV Sum Records': ':arrow_up: IV `{:,}` {}\n:arrow_down: IV `{:,}` {}'.format(
                                                    stats['totals'].get('phase_highest_iv_sum', 0),
                                                    stats['totals'].get('phase_highest_iv_sum_pokemon', 'N/A'),
                                                    stats['totals'].get('phase_lowest_iv_sum', 0),
                                                    stats['totals'].get('phase_lowest_iv_sum_pokemon', 'N/A')),
                            'Phase SV Records': ':arrow_up: SV `{:,}` {}\n:arrow_down: SV `{:,}` {}'.format(
                                                    stats['totals'].get('phase_highest_sv', 0),
                                                    stats['totals'].get('phase_highest_sv_pokemon', 'N/A'),
                                                    stats['totals'].get('phase_lowest_sv', 0),
                                                    stats['totals'].get('phase_lowest_sv_pokemon', 'N/A')),
                            'Phase Same Pokémon Streak': '{:,} {} were encountered in a row!'.format(
                                                    stats['totals'].get('phase_streak', 0),
                                                    stats['totals'].get('phase_streak_pokemon', 'N/A')),
                            'Total Encounters': '{:,} ({:,}✨)'.format(
                                                    stats['totals'].get('encounters', 0),
                                                    stats['totals'].get('shiny_encounters', 0))},
                        embed_footer='PokéBot ID: {} | {}'.format(
                            config_discord['bot_id'],
                            mGBA.game),
                        embed_color='D70040')
            except:
                console.print_exception(show_locals=True)

            try:
                # Discord anti-shiny Pokémon encountered
                if config_discord['anti_shiny_pokemon_encounter']['enable'] and (65528 <= pokemon['shinyValue'] <= 65535):
                    # Discord pings
                    discord_ping = ''
                    match config_discord['anti_shiny_pokemon_encounter']['ping_mode']:
                        case 'role':
                            discord_ping = '📢 <@&{}>'.format(config_discord['anti_shiny_pokemon_encounter']['ping_id'])
                        case 'user':
                            discord_ping = '📢 <@{}>'.format(config_discord['anti_shiny_pokemon_encounter']['ping_id'])
                    DiscordMessage(
                        webhook_url=config_discord['anti_shiny_pokemon_encounter'].get('webhook_url', None),
                        content='Encountered an anti-shiny 💀 {} 💀!\n{}'.format(
                                pokemon['name'],
                                discord_ping
                        ),
                        embed=True,
                        embed_title='Anti-Shiny encountered!',
                        embed_description='{} {} (Lv. {:,}) at {}!'.format(
                                        pokemon['nature'],
                                        pokemon['name'],
                                        pokemon['level'],
                                        pokemon['metLocation']),
                        embed_fields={
                            'Shiny Value': '{:,}'.format(pokemon['shinyValue']),
                            'IVs': IVField(),
                            '{} Encounters'.format(
                                            pokemon['name']): '{:,} ({:,}✨)'.format(
                                            stats['pokemon'][pokemon['name']].get('encounters', 0),
                                            stats['pokemon'][pokemon['name']].get('shiny_encounters', 0)),
                            '{} Phase Encounters'.format(
                                            pokemon['name']): '{:,}'.format(
                                            stats['pokemon'][pokemon['name']].get('phase_encounters', 0)),
                            'Phase Encounters': '{:,} ({:,}/h)'.format(
                                            stats['totals'].get('phase_encounters', 0),
                                            GetEncounterRate()),
                            'Phase IV Sum Records': ':arrow_up: `{:,}` IV {}\n:arrow_down: `{:,}` IV {}'.format(
                                            stats['totals'].get('phase_highest_iv_sum', 0),
                                            stats['totals'].get('phase_highest_iv_sum_pokemon', 'N/A'),
                                            stats['totals'].get('phase_lowest_iv_sum', 0),
                                            stats['totals'].get('phase_lowest_iv_sum_pokemon', 'N/A')),
                            'Phase SV Records': ':arrow_up: `{:,}` SV {}\n:arrow_down: `{:,}` SV {}'.format(
                                            stats['totals'].get('phase_highest_sv', 0),
                                            stats['totals'].get('phase_highest_sv_pokemon', 'N/A'),
                                            stats['totals'].get('phase_lowest_sv', 0),
                                            stats['totals'].get('phase_lowest_sv_pokemon', 'N/A')),
                            'Phase Same Pokémon Streak': '{:,} {} were encountered in a row!'.format(
                                            stats['totals'].get('phase_streak', 0),
                                            stats['totals'].get('phase_streak_pokemon', 'N/A')),
                            'Total Encounters': '{:,} ({:,}✨)'.format(
                                            stats['totals'].get('encounters', 0),
                                            stats['totals'].get('shiny_encounters', 0))},
                        embed_thumbnail='./sprites/pokemon/anti-shiny/{}.png'.format(
                                            pokemon['name']),
                        embed_footer='PokéBot ID: {} | {}'.format(
                            config_discord['bot_id'],
                            mGBA.game),
                        embed_color='000000')
            except:
                console.print_exception(show_locals=True)

    except:
        console.print_exception(show_locals=True)

    try:
        # Post the most recent OBS stream screenshot to Discord
        # (screenshot is taken in Stats.py before phase resets)
        if config_obs.get('webhook_url', None) and pokemon['shiny']:
            def DiscordScreenshot():
                time.sleep(3) # Give the screenshot some time to save to disk
                images = glob.glob('{}*.png'.format(config_obs['replay_dir']))
                image = max(images, key=os.path.getctime)
                DiscordMessage(
                    webhook_url=config_obs.get('webhook_url', None),
                    image=image)
            # Run in a thread to not hold up other hooks
            Thread(target=DiscordScreenshot).start()
    except:
        console.print_exception(show_locals=True)

    try:
        # Save OBS replay buffer n seconds after encountering a shiny
        if config_obs.get('enable_replay_buffer', None) and pokemon['shiny']:
            def ReplayBuffer():
                WaitFrames(config_obs.get('replay_buffer_delay', 0))
                for key in config_obs['hotkey_replay_buffer']:
                    pydirectinput.keyDown(key)
                for key in reversed(config_obs['hotkey_replay_buffer']):
                    pydirectinput.keyUp(key)
            # Run in a thread to not hold up other hooks
            Thread(target=ReplayBuffer).start()
    except:
        console.print_exception(show_locals=True)
