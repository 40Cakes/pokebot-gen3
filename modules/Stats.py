import os
import copy
import json
import math
import sys
import time
import importlib
import pandas as pd
from typing import NoReturn
from threading import Thread
from datetime import datetime

from rich.table import Table
from modules.Colours import IVColour, IVSumColour, SVColour
from modules.Config import config
from modules.Console import console
from modules.Files import BackupFolder, ReadFile, WriteFile
from modules.Gui import GetROM
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import GetGameState, GameState
from modules.Trainer import GetTrainer

CustomCatchFilters = None
CustomHooks = None
session_encounters = None
stats = None
encounter_log = None
shiny_log = None
stats_dir = None
files = None

def InitStats():
    global CustomCatchFilters, CustomHooks, session_encounters, stats, encounter_log, shiny_log, stats_dir, files

    safe_trainer_name = ''.join([c for c in GetTrainer()['name'] if c.isalpha() or c.isdigit() or c == ' ']).rstrip()
    trainer_dir = '{}/{}-{}'.format(
        GetROM().game_code,
        GetTrainer()['tid'],
        safe_trainer_name
    )
    stats_dir = './stats/{}'.format(trainer_dir)
    os.makedirs(stats_dir, exist_ok=True)
    files = {
        'encounter_log': '{}/encounter_log.json'.format(stats_dir),
        'shiny_log': '{}/shiny_log.json'.format(stats_dir),
        'totals': '{}/totals.json'.format(stats_dir)
    }

    try:
        if os.path.isfile('./config/{}/CustomCatchFilters.py'.format(trainer_dir)):
            CustomCatchFilters = importlib.import_module('.CustomCatchFilters', 'config.{}.{}-{}'.format(
                GetROM().game_code,
                GetTrainer()['tid'],
                safe_trainer_name)).CustomCatchFilters
        else:
            from config.CustomCatchFilters import CustomCatchFilters

        if os.path.isfile('./config/{}/CustomHooks.py'.format(trainer_dir)):
            CustomHooks = importlib.import_module('.CustomHooks', 'config.{}.{}-{}'.format(
                GetROM().game_code,
                GetTrainer()['tid'],
                safe_trainer_name)).CustomHooks
        else:
            from config.CustomHooks import CustomHooks

        session_encounters = 0
        f_stats = ReadFile(files['totals'])
        stats = json.loads(f_stats) if f_stats else None
        f_encounter_log = ReadFile(files['encounter_log'])
        encounter_log = json.loads(f_encounter_log) if f_encounter_log else {'encounter_log': []}
        f_shiny_log = ReadFile(files['shiny_log'])
        shiny_log = json.loads(f_shiny_log) if f_shiny_log else {'shiny_log': []}
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        sys.exit(1)


def GetRNGStateHistory(pokemon_name: str) -> dict:
    try:
        default = {'rng': []}
        file = ReadFile('{}/rng/{}.json'.format(
            stats_dir,
            pokemon_name.lower()))
        data = json.loads(file) if file else default
        return data
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return default


def SaveRNGStateHistory(pokemon_name: str, data: dict) -> NoReturn:
    try:
        WriteFile('{}/rng/{}.json'.format(
            stats_dir,
            pokemon_name.lower()), json.dumps(data))
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def GetEncounterRate() -> int:
    try:
        encounter_logs = encounter_log['encounter_log']
        if len(encounter_logs) > 1 and session_encounters > 1:
            encounter_rate = int(
                (3600000 / ((encounter_logs[-1]['time_encountered'] -
                             encounter_logs[-min(session_encounters, 250)]['time_encountered'])
                            * 1000)) * (min(session_encounters, 250)))
            return encounter_rate
        return 0
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return 0


def FlattenData(data: dict) -> dict:
    out = {}

    def flatten(x, name=''):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + '_')
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + '_')
                i += 1
        else:
            out[name[:-1]] = x

    flatten(data)
    return out


def PrintStats(pokemon: dict) -> NoReturn:
    try:
        console.print('\n')
        console.rule('[{}]{}[/] encountered at {}'.format(
            pokemon['type'][0].lower(),
            pokemon['name'],
            pokemon['metLocation']
        ), style=pokemon['type'][0].lower())

        match config['logging']['console']['encounter_data']:
            case 'verbose':
                pokemon_table = Table()
                pokemon_table.add_column('PID', justify='center', width=10)
                pokemon_table.add_column('Level', justify='center')
                pokemon_table.add_column('Item', justify='center', width=10)
                pokemon_table.add_column('Nature', justify='center', width=10)
                pokemon_table.add_column('Ability', justify='center', width=15)
                pokemon_table.add_column('Hidden Power', justify='center', width=15,
                                         style=pokemon['hiddenPower'].lower())
                pokemon_table.add_column('Shiny Value', justify='center', style=SVColour(pokemon['shinyValue']),
                                         width=10)
                pokemon_table.add_row(
                    str(hex(pokemon['pid'])[2:]).upper(),
                    str(pokemon['level']),
                    pokemon['item']['name'],
                    pokemon['nature'],
                    pokemon['ability'],
                    pokemon['hiddenPower'],
                    '{:,}'.format(pokemon['shinyValue'])
                )
                console.print(pokemon_table)
            case 'basic':
                console.print(
                    '[{}]{}[/]: PID: {} | Lv.: {:,} | Item: {} | Nature: {} | Ability: {} | Shiny Value: {:,}'.format(
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        str(hex(pokemon['pid'])[2:]).upper(),
                        pokemon['level'],
                        pokemon['item']['name'],
                        pokemon['nature'],
                        pokemon['ability'],
                        pokemon['shinyValue']))

        match config['logging']['console']['encounter_ivs']:
            case 'verbose':
                iv_table = Table(title='{} IVs'.format(pokemon['name']))
                iv_table.add_column('HP', justify='center', style=IVColour(pokemon['IVs']['hp']))
                iv_table.add_column('ATK', justify='center', style=IVColour(pokemon['IVs']['attack']))
                iv_table.add_column('DEF', justify='center', style=IVColour(pokemon['IVs']['defense']))
                iv_table.add_column('SPATK', justify='center', style=IVColour(pokemon['IVs']['spAttack']))
                iv_table.add_column('SPDEF', justify='center', style=IVColour(pokemon['IVs']['spDefense']))
                iv_table.add_column('SPD', justify='center', style=IVColour(pokemon['IVs']['speed']))
                iv_table.add_column('Total', justify='right', style=IVSumColour(pokemon['IVSum']))
                iv_table.add_row(
                    '{}'.format(pokemon['IVs']['hp']),
                    '{}'.format(pokemon['IVs']['attack']),
                    '{}'.format(pokemon['IVs']['defense']),
                    '{}'.format(pokemon['IVs']['spAttack']),
                    '{}'.format(pokemon['IVs']['spDefense']),
                    '{}'.format(pokemon['IVs']['speed']),
                    '{}'.format(pokemon['IVSum'])
                )
                console.print(iv_table)
            case 'basic':
                console.print(
                    'IVs: HP: [{}]{}[/] | ATK: [{}]{}[/] | DEF: [{}]{}[/] | SPATK: [{}]{}[/] | SPDEF: [{}]{}[/] | SPD: [{}]{}[/] | Sum: [{}]{}[/]'.format(
                        IVColour(pokemon['IVs']['hp']),
                        pokemon['IVs']['hp'],
                        IVColour(pokemon['IVs']['attack']),
                        pokemon['IVs']['attack'],
                        IVColour(pokemon['IVs']['defense']),
                        pokemon['IVs']['defense'],
                        IVColour(pokemon['IVs']['spAttack']),
                        pokemon['IVs']['spAttack'],
                        IVColour(pokemon['IVs']['spDefense']),
                        pokemon['IVs']['spDefense'],
                        IVColour(pokemon['IVs']['speed']),
                        pokemon['IVs']['speed'],
                        IVSumColour(pokemon['IVSum']),
                        pokemon['IVSum']))

        match config['logging']['console']['encounter_moves']:
            case 'verbose':
                move_table = Table(title='{} Moves'.format(pokemon['name']))
                move_table.add_column('Name', justify='left', width=20)
                move_table.add_column('Kind', justify='center', width=10)
                move_table.add_column('Type', justify='center', width=10)
                move_table.add_column('Power', justify='center', width=10)
                move_table.add_column('Accuracy', justify='center', width=10)
                move_table.add_column('PP', justify='center', width=5)
                for i in range(4):
                    if pokemon['moves'][i]['name'] != 'None':
                        move_table.add_row(
                            pokemon['moves'][i]['name'],
                            pokemon['moves'][i]['kind'],
                            pokemon['moves'][i]['type'],
                            str(pokemon['moves'][i]['power']),
                            str(pokemon['moves'][i]['accuracy']),
                            str(pokemon['moves'][i]['remaining_pp'])
                        )
                console.print(move_table)
            case 'basic':
                for i in range(4):
                    if pokemon['moves'][i]['name'] != 'None':
                        console.print('[{}]Move {}[/]: {} | {} | [{}]{}[/] | Pwr: {} | Acc: {} | PP: {}'.format(
                            pokemon['type'][0].lower(),
                            i + 1,
                            pokemon['moves'][i]['name'],
                            pokemon['moves'][i]['kind'],
                            pokemon['moves'][i]['type'].lower(),
                            pokemon['moves'][i]['type'],
                            pokemon['moves'][i]['power'],
                            pokemon['moves'][i]['accuracy'],
                            pokemon['moves'][i]['remaining_pp']
                        ))

        match config['logging']['console']['statistics']:
            case 'verbose':
                stats_table = Table(title='Statistics')
                stats_table.add_column('', justify='left', width=10)
                stats_table.add_column('Phase IV Records', justify='center', width=10)
                stats_table.add_column('Phase SV Records', justify='center', width=15)
                stats_table.add_column('Phase Encounters', justify='right', width=10)
                stats_table.add_column('Phase %', justify='right', width=10)
                stats_table.add_column('Shiny Encounters', justify='right', width=10)
                stats_table.add_column('Total Encounters', justify='right', width=10)
                stats_table.add_column('Shiny Average', justify='right', width=10)

                recent_pokemon = []
                for p in encounter_log['encounter_log']:
                    if stats['pokemon'][p['pokemon']['name']].get('phase_encounters', 0) > 0:
                        recent_pokemon.append(p['pokemon']['name'])

                for p in sorted(set(recent_pokemon)):
                    stats_table.add_row(
                        p,
                        '[red]{}[/] / [green]{}'.format(
                            stats['pokemon'][p].get('phase_lowest_iv_sum', -1),
                            stats['pokemon'][p].get('phase_highest_iv_sum', -1)),
                        '[green]{:,}[/] / [{}]{:,}'.format(
                            stats['pokemon'][p].get('phase_lowest_sv', -1),
                            SVColour(stats['pokemon'][p].get('phase_highest_sv', -1)),
                            stats['pokemon'][p].get('phase_highest_sv', -1)),
                        '{:,}'.format(stats['pokemon'][p].get('phase_encounters', 0)),
                        '{:0.2f}%'.format(
                            (stats['pokemon'][p].get('phase_encounters', 0) /
                             stats['totals'].get('phase_encounters', 0)) * 100),
                        '{:,}'.format(stats['pokemon'][p].get('shiny_encounters', 0)),
                        '{:,}'.format(stats['pokemon'][p].get('encounters', 0)),
                        '{}'.format(stats['pokemon'][p].get('shiny_average', 'N/A'))
                    )
                stats_table.add_row(
                    '[bold yellow]Total',
                    '[red]{}[/] / [green]{}'.format(
                        stats['totals'].get('phase_lowest_iv_sum', -1),
                        stats['totals'].get('phase_highest_iv_sum', -1)),
                    '[green]{:,}[/] / [{}]{:,}'.format(
                        stats['totals'].get('phase_lowest_sv', -1),
                        SVColour(stats['totals'].get('phase_highest_sv', -1)),
                        stats['totals'].get('phase_highest_sv', -1)),
                    '[bold yellow]{:,}'.format(stats['totals'].get('phase_encounters', 0)),
                    '[bold yellow]100%',
                    '[bold yellow]{:,}'.format(stats['totals'].get('shiny_encounters', 0)),
                    '[bold yellow]{:,}'.format(stats['totals'].get('encounters', 0)),
                    '[bold yellow]{}'.format(stats['totals'].get('shiny_average', 'N/A'))
                )
                console.print(stats_table)
            case 'basic':
                console.print(
                    '[{}]{}[/] Phase Encounters: {:,} | [{}]{}[/] Total Encounters: {:,} | [{}]{}[/] Shiny Encounters: {:,}'.format(
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        stats['pokemon'][pokemon['name']].get('phase_encounters', 0),
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        stats['pokemon'][pokemon['name']].get('encounters', 0),
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        stats['pokemon'][pokemon['name']].get('shiny_encounters', 0),
                    ))
                console.print(
                    '[{}]{}[/] Phase IV Records [red]{}[/]/[green]{}[/] | [{}]{}[/] Phase SV Records [green]{:,}[/]/[{}]{:,}[/] | [{}]{}[/] Shiny Average: {}'.format(
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        stats['pokemon'][pokemon['name']].get('phase_lowest_iv_sum', -1),
                        stats['pokemon'][pokemon['name']].get('phase_highest_iv_sum', -1),
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        stats['pokemon'][pokemon['name']].get('phase_lowest_sv', -1),
                        SVColour(stats['pokemon'][pokemon['name']].get('phase_highest_sv', -1)),
                        stats['pokemon'][pokemon['name']].get('phase_highest_sv', -1),
                        pokemon['type'][0].lower(),
                        pokemon['name'],
                        stats['pokemon'][pokemon['name']].get('shiny_average', 'N/A')
                    ))
                console.print(
                    'Phase Encounters: {:,} | Phase IV Records [red]{}[/]/[green]{}[/] | Phase SV Records [green]{:,}[/]/[{}]{:,}[/]'.format(
                        stats['totals'].get('phase_encounters', 0),
                        stats['totals'].get('phase_lowest_iv_sum', -1),
                        stats['totals'].get('phase_highest_iv_sum', -1),
                        stats['totals'].get('phase_lowest_sv', -1),
                        SVColour(stats['totals'].get('phase_highest_sv', -1)),
                        stats['totals'].get('phase_highest_sv', -1)
                    ))
                console.print('Total Shinies: {:,} | Total Encounters: {:,} | Total Shiny Average: {}'.format(
                    stats['totals'].get('encounters', 0),
                    stats['totals'].get('shiny_encounters', 0),
                    stats['totals'].get('shiny_average', 'N/A')
                ))

        console.print('[yellow]Encounter rate[/]: ~{:,}/h'.format(GetEncounterRate()))
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def LogEncounter(pokemon: dict) -> NoReturn:
    global stats
    global encounter_log
    global session_encounters

    try:
        if not stats:  # Set up stats file if it doesn't exist
            stats = {}
        if not 'pokemon' in stats:
            stats['pokemon'] = {}
        if not 'totals' in stats:
            stats['totals'] = {}

        if not pokemon['name'] in stats['pokemon']:  # Set up a Pokémon stats if first encounter
            stats['pokemon'].update({pokemon['name']: {}})

        # Increment encounters stats
        stats['totals']['encounters'] = stats['totals'].get('encounters', 0) + 1
        stats['totals']['phase_encounters'] = stats['totals'].get('phase_encounters', 0) + 1

        # Update Pokémon stats
        stats['pokemon'][pokemon['name']]['encounters'] = stats['pokemon'][pokemon['name']].get('encounters', 0) + 1
        stats['pokemon'][pokemon['name']]['phase_encounters'] = stats['pokemon'][pokemon['name']].get(
            'phase_encounters', 0) + 1
        stats['pokemon'][pokemon['name']]['last_encounter_time_unix'] = time.time()
        stats['pokemon'][pokemon['name']]['last_encounter_time_str'] = str(datetime.now())

        # Pokémon phase highest shiny value
        if not stats['pokemon'][pokemon['name']].get('phase_highest_sv', None):
            stats['pokemon'][pokemon['name']]['phase_highest_sv'] = pokemon['shinyValue']
        else:
            stats['pokemon'][pokemon['name']]['phase_highest_sv'] = max(pokemon['shinyValue'],
                                                                        stats['pokemon'][pokemon['name']].get(
                                                                            'phase_highest_sv', -1))

        # Pokémon phase lowest shiny value
        if not stats['pokemon'][pokemon['name']].get('phase_lowest_sv', None):
            stats['pokemon'][pokemon['name']]['phase_lowest_sv'] = pokemon['shinyValue']
        else:
            stats['pokemon'][pokemon['name']]['phase_lowest_sv'] = min(pokemon['shinyValue'],
                                                                       stats['pokemon'][pokemon['name']].get(
                                                                           'phase_lowest_sv', 65536))

        # Pokémon total lowest shiny value
        if not stats['pokemon'][pokemon['name']].get('total_lowest_sv', None):
            stats['pokemon'][pokemon['name']]['total_lowest_sv'] = pokemon['shinyValue']
        else:
            stats['pokemon'][pokemon['name']]['total_lowest_sv'] = min(pokemon['shinyValue'],
                                                                       stats['pokemon'][pokemon['name']].get(
                                                                           'total_lowest_sv', 65536))

        # Phase highest shiny value
        if not stats['totals'].get('phase_highest_sv', None):
            stats['totals']['phase_highest_sv'] = pokemon['shinyValue']
            stats['totals']['phase_highest_sv_pokemon'] = pokemon['name']
        elif pokemon['shinyValue'] >= stats['totals'].get('phase_highest_sv', -1):
            stats['totals']['phase_highest_sv'] = pokemon['shinyValue']
            stats['totals']['phase_highest_sv_pokemon'] = pokemon['name']

        # Phase lowest shiny value
        if not stats['totals'].get('phase_lowest_sv', None):
            stats['totals']['phase_lowest_sv'] = pokemon['shinyValue']
            stats['totals']['phase_lowest_sv_pokemon'] = pokemon['name']
        elif pokemon['shinyValue'] <= stats['totals'].get('phase_lowest_sv', 65536):
            stats['totals']['phase_lowest_sv'] = pokemon['shinyValue']
            stats['totals']['phase_lowest_sv_pokemon'] = pokemon['name']

        # Pokémon highest phase IV record
        if not stats['pokemon'][pokemon['name']].get('phase_highest_iv_sum') or pokemon['IVSum'] >= stats['pokemon'][
            pokemon['name']].get('phase_highest_iv_sum', -1):
            stats['pokemon'][pokemon['name']]['phase_highest_iv_sum'] = pokemon['IVSum']

        # Pokémon highest total IV record
        if pokemon['IVSum'] >= stats['pokemon'][pokemon['name']].get('total_highest_iv_sum', -1):
            stats['pokemon'][pokemon['name']]['total_highest_iv_sum'] = pokemon['IVSum']

        # Pokémon lowest phase IV record
        if not stats['pokemon'][pokemon['name']].get('phase_lowest_iv_sum') or pokemon['IVSum'] <= stats['pokemon'][
            pokemon['name']].get('phase_lowest_iv_sum', 999):
            stats['pokemon'][pokemon['name']]['phase_lowest_iv_sum'] = pokemon['IVSum']

        # Pokémon lowest total IV record
        if pokemon['IVSum'] <= stats['pokemon'][pokemon['name']].get('total_lowest_iv_sum', 999):
            stats['pokemon'][pokemon['name']]['total_lowest_iv_sum'] = pokemon['IVSum']

        # Phase highest IV sum record
        if not stats['totals'].get('phase_highest_iv_sum') or pokemon['IVSum'] >= stats['totals'].get(
                'phase_highest_iv_sum', -1):
            stats['totals']['phase_highest_iv_sum'] = pokemon['IVSum']
            stats['totals']['phase_highest_iv_sum_pokemon'] = pokemon['name']

        # Phase lowest IV sum record
        if not stats['totals'].get('phase_lowest_iv_sum') or pokemon['IVSum'] <= stats['totals'].get(
                'phase_lowest_iv_sum', 999):
            stats['totals']['phase_lowest_iv_sum'] = pokemon['IVSum']
            stats['totals']['phase_lowest_iv_sum_pokemon'] = pokemon['name']

        # Total highest IV sum record
        if pokemon['IVSum'] >= stats['totals'].get('highest_iv_sum', -1):
            stats['totals']['highest_iv_sum'] = pokemon['IVSum']
            stats['totals']['highest_iv_sum_pokemon'] = pokemon['name']

        # Total lowest IV sum record
        if pokemon['IVSum'] <= stats['totals'].get('lowest_iv_sum', 999):
            stats['totals']['lowest_iv_sum'] = pokemon['IVSum']
            stats['totals']['lowest_iv_sum_pokemon'] = pokemon['name']

        if config['logging']['log_encounters']:
            # Log all encounters to a CSV file per phase
            csvpath = '{}/encounters/'.format(stats_dir)
            csvfile = 'Phase {} Encounters.csv'.format(stats['totals'].get('shiny_encounters', 0))
            pd_pokemon = pd.DataFrame.from_dict(FlattenData(pokemon), orient='index').drop([
                'EVs_attack',
                'EVs_defence',
                'EVs_hp',
                'EVs_spAttack',
                'EVs_spDefense',
                'EVs_speed',
                'markings_circle',
                'markings_heart',
                'markings_square',
                'markings_triangle',
                'moves_0_effect',
                'moves_1_effect',
                'moves_2_effect',
                'moves_3_effect',
                'pokerus_days',
                'pokerus_strain'
                'status_badPoison',
                'status_burn',
                'status_freeze',
                'status_paralysis',
                'status_poison',
                'status_sleep',
                'condition_beauty',
                'condition_cool',
                'condition_cute',
                'condition_feel',
                'condition_smart'
                'condition_tough'],
                errors='ignore').sort_index().transpose()
            os.makedirs(csvpath, exist_ok=True)
            header = False if os.path.exists('{}{}'.format(
                csvpath,
                csvfile
            )) else True
            pd_pokemon.to_csv('{}{}'.format(
                csvpath,
                csvfile
            ), mode='a', encoding='utf-8', index=False, header=header)

        # Pokémon shiny average
        if stats['pokemon'][pokemon['name']].get('shiny_encounters'):
            avg = int(math.floor(stats['pokemon'][pokemon['name']]['encounters'] / stats['pokemon'][pokemon['name']][
                'shiny_encounters']))
            stats['pokemon'][pokemon['name']]['shiny_average'] = '1/{:,}'.format(avg)

        # Total shiny average
        if stats['totals'].get('shiny_encounters'):
            avg = int(math.floor(stats['totals']['encounters'] / stats['totals']['shiny_encounters']))
            stats['totals']['shiny_average'] = '1/{:,}'.format(avg)

        # Log encounter to encounter_log
        log_obj = {
            'time_encountered': time.time(),
            'pokemon': pokemon,
            'snapshot_stats': {
                'phase_encounters': stats['totals']['phase_encounters'],
                'species_encounters': stats['pokemon'][pokemon['name']]['encounters'],
                'species_shiny_encounters': stats['pokemon'][pokemon['name']].get('shiny_encounters', 0),
                'total_encounters': stats['totals']['encounters'],
                'total_shiny_encounters': stats['totals'].get('shiny_encounters', 0),
            }
        }
        encounter_log['encounter_log'].append(log_obj)
        encounter_log['encounter_log'] = encounter_log['encounter_log'][-250:]
        WriteFile(files['encounter_log'], json.dumps(encounter_log, indent=4, sort_keys=True))
        if pokemon['shiny']:
            shiny_log['shiny_log'].append(log_obj)
            WriteFile(files['shiny_log'], json.dumps(shiny_log, indent=4, sort_keys=True))

        # Same Pokémon encounter streak records
        if len(encounter_log['encounter_log']) > 1 and \
                encounter_log['encounter_log'][-2]['pokemon']['name'] == pokemon['name']:
            stats['totals']['current_streak'] = stats['totals'].get('current_streak', 0) + 1
        else:
            stats['totals']['current_streak'] = 1
        if stats['totals'].get('current_streak', 0) >= stats['totals'].get('phase_streak', 0):
            stats['totals']['phase_streak'] = stats['totals'].get('current_streak', 0)
            stats['totals']['phase_streak_pokemon'] = pokemon['name']

        if pokemon['shiny']:
            stats['pokemon'][pokemon['name']]['shiny_encounters'] = stats['pokemon'][pokemon['name']].get(
                'shiny_encounters', 0) + 1
            stats['totals']['shiny_encounters'] = stats['totals'].get('shiny_encounters', 0) + 1

        PrintStats(pokemon)

        if pokemon['shiny']:
            WaitFrames(config['obs'].get('shiny_delay', 1))

        if config['obs']['screenshot'] and pokemon['shiny']:
            from modules.OBS import OBSHotKey
            while GetGameState() != GameState.BATTLE:
                PressButton(['B'])  # Throw out Pokémon for screenshot
            WaitFrames(180)
            OBSHotKey('OBS_KEY_F11', pressCtrl=True)

        # Run custom code in CustomHooks in a thread
        hook = (copy.deepcopy(pokemon), copy.deepcopy(stats))
        Thread(target=CustomHooks, args=(hook,)).start()

        if pokemon['shiny']:
            # Total longest phase
            if stats['totals']['phase_encounters'] > stats['totals'].get('longest_phase_encounters', 0):
                stats['totals']['longest_phase_encounters'] = stats['totals']['phase_encounters']
                stats['totals']['longest_phase_pokemon'] = pokemon['name']

            # Total shortest phase
            if not stats['totals'].get('shortest_phase_encounters', None) or \
                    stats['totals']['phase_encounters'] <= stats['totals']['shortest_phase_encounters']:
                stats['totals']['shortest_phase_encounters'] = stats['totals']['phase_encounters']
                stats['totals']['shortest_phase_pokemon'] = pokemon['name']

            # Reset phase stats
            stats['totals'].pop('phase_encounters', None)
            stats['totals'].pop('phase_highest_sv', None)
            stats['totals'].pop('phase_highest_sv_pokemon', None)
            stats['totals'].pop('phase_lowest_sv', None)
            stats['totals'].pop('phase_lowest_sv_pokemon', None)
            stats['totals'].pop('phase_highest_iv_sum', None)
            stats['totals'].pop('phase_highest_iv_sum_pokemon', None)
            stats['totals'].pop('phase_lowest_iv_sum', None)
            stats['totals'].pop('phase_lowest_iv_sum_pokemon', None)
            stats['totals'].pop('current_streak', None)
            stats['totals'].pop('phase_streak', None)
            stats['totals'].pop('phase_streak_pokemon', None)

            # Reset Pokémon phase stats
            for n in stats['pokemon']:
                stats['pokemon'][n].pop('phase_encounters', None)
                stats['pokemon'][n].pop('phase_highest_sv', None)
                stats['pokemon'][n].pop('phase_lowest_sv', None)
                stats['pokemon'][n].pop('phase_highest_iv_sum', None)
                stats['pokemon'][n].pop('phase_lowest_iv_sum', None)

        # Save stats file
        WriteFile(files['totals'], json.dumps(stats, indent=4, sort_keys=True))
        session_encounters += 1

        # Backup stats folder every n encounters
        if config['logging']['backup_stats'] > 0 and \
                stats['totals'].get('encounters', None) and \
                stats['totals']['encounters'] % config['logging']['backup_stats'] == 0:
            BackupFolder('./{}/'.format(stats_dir), './backups/{}/{}.zip'.format(
                stats_dir,
                time.strftime('%Y%m%d-%H%M%S')))

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def EncounterPokemon(pokemon: dict) -> NoReturn:
    """
    Call when a Pokémon is encountered, decides whether to battle, flee or catch.
    Expects the trainer's state to be MISC_MENU (battle started, no longer in the overworld).

    :return:
    """

    LogEncounter(pokemon)

    # TODO temporary until auto-catch is ready
    if pokemon['shiny']:
        console.print('[bold yellow]Shiny found!')

        # Load catch block config
        from modules.Config import catch_block_schema, LoadConfig
        config_catch_block = LoadConfig('catch_block.yml', catch_block_schema)

        if pokemon['name'] in config_catch_block['block_list']:
            console.print('[bold yellow]' + pokemon['name'] + ' is on the catch block list, skipping encounter...')
        else:
            sys.exit()

    if CustomCatchFilters(pokemon):
        console.print('[bold green]Custom filter Pokemon found!')
        sys.exit()
