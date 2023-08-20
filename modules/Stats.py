import os
import copy
import json
import math
import time
import logging
import pandas as pd
import pydirectinput
from threading import Thread
from datetime import datetime
from modules.Config import config
from modules.Files import BackupFolder, ReadFile, WriteFile


log = logging.getLogger(__name__)
os.makedirs('stats', exist_ok=True)
files = {
    'encounter_log': 'stats/encounter_log.json',
    'shiny_log': 'stats/shiny_log.json',
    'totals': 'stats/totals.json'
}

def FlattenData(data: dict):
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

def GetStats():
    try:
        totals = ReadFile(files['totals'])
        if totals:
            return json.loads(totals)
        return None
    except Exception as e:
        log.exception(str(e))
        return None


def GetEncounterLog():
    default = {'encounter_log': []}
    try:
        encounter_log = ReadFile(files['encounter_log'])
        if encounter_log:
            return json.loads(encounter_log)
        return default
    except Exception as e:
        log.exception(str(e))
        return default


def GetShinyLog():
    default = {'shiny_log': []}
    try:
        shiny_log = ReadFile(files['shiny_log'])
        if shiny_log:
            return json.loads(shiny_log)
        return default
    except Exception as e:
        log.exception(str(e))
        return default


def GetRNGStateHistory(tid: str, pokemon_name: str):
    default = {'rngState': []}
    try:
        file = ReadFile(f'stats/{tid}/{pokemon_name.lower()}.json')
        data = json.loads(file) if file else default
        return data
    except Exception as e:
        log.exception(str(e))
        return default


session_encounters = 0
def GetEncounterRate():
    try:
        fmt = '%Y-%m-%d %H:%M:%S.%f'
        encounter_logs = GetEncounterLog()['encounter_log']
        if len(encounter_logs) > 1 and session_encounters > 1:
            encounter_rate = int(
                (3600 /
                 (datetime.strptime(encounter_logs[-1]['time_encountered'], fmt) -
                  datetime.strptime(encounter_logs[-min(session_encounters, 250)]['time_encountered'], fmt)
                  ).total_seconds()) * (min(session_encounters, 250)))
            return encounter_rate
        return 0
    except Exception as e:
        log.exception(str(e))
        return 0


stats = GetStats()  # Load stats
encounter_log = GetEncounterLog() # Load encounter log
def LogEncounter(pokemon: dict):
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
        stats['pokemon'][pokemon['name']]['phase_encounters'] = stats['pokemon'][pokemon['name']].get('phase_encounters', 0) + 1
        stats['pokemon'][pokemon['name']]['last_encounter_time_unix'] = time.time()
        stats['pokemon'][pokemon['name']]['last_encounter_time_str'] = str(datetime.now())

        # Pokémon phase highest shiny value
        if not stats['pokemon'][pokemon['name']].get('phase_highest_sv', None):
            stats['pokemon'][pokemon['name']]['phase_highest_sv'] = pokemon['shinyValue']
        else:
            stats['pokemon'][pokemon['name']]['phase_highest_sv'] = max(pokemon['shinyValue'], stats['pokemon'][pokemon['name']].get('phase_highest_sv', -1))

        # Pokémon phase lowest shiny value
        if not stats['pokemon'][pokemon['name']].get('phase_lowest_sv', None):
            stats['pokemon'][pokemon['name']]['phase_lowest_sv'] = pokemon['shinyValue']
        else:
            stats['pokemon'][pokemon['name']]['phase_lowest_sv'] = min(pokemon['shinyValue'], stats['pokemon'][pokemon['name']].get('phase_lowest_sv', 65536))

        # Pokémon total lowest shiny value
        if not stats['pokemon'][pokemon['name']].get('total_lowest_sv', None):
            stats['pokemon'][pokemon['name']]['total_lowest_sv'] = pokemon['shinyValue']
        else:
            stats['pokemon'][pokemon['name']]['total_lowest_sv'] = min(pokemon['shinyValue'], stats['pokemon'][pokemon['name']].get('total_lowest_sv', 65536))

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
        if not stats['pokemon'][pokemon['name']].get('phase_highest_iv_sum') or pokemon['IVSum'] >= stats['pokemon'][pokemon['name']].get('phase_highest_iv_sum', -1):
            stats['pokemon'][pokemon['name']]['phase_highest_iv_sum'] = pokemon['IVSum']

        # Pokémon highest total IV record
        if pokemon['IVSum'] >= stats['pokemon'][pokemon['name']].get('total_highest_iv_sum', -1):
            stats['pokemon'][pokemon['name']]['total_highest_iv_sum'] = pokemon['IVSum']

        # Pokémon lowest phase IV record
        if not stats['pokemon'][pokemon['name']].get('phase_lowest_iv_sum') or pokemon['IVSum'] <= stats['pokemon'][pokemon['name']].get('phase_lowest_iv_sum', 999):
            stats['pokemon'][pokemon['name']]['phase_lowest_iv_sum'] = pokemon['IVSum']

        # Pokémon lowest total IV record
        if pokemon['IVSum'] <= stats['pokemon'][pokemon['name']].get('total_lowest_iv_sum', 999):
            stats['pokemon'][pokemon['name']]['total_lowest_iv_sum'] = pokemon['IVSum']

        # Phase highest IV sum record
        if not stats['totals'].get('phase_highest_iv_sum') or pokemon['IVSum'] >= stats['totals'].get('phase_highest_iv_sum', -1):
            stats['totals']['phase_highest_iv_sum'] = pokemon['IVSum']
            stats['totals']['phase_highest_iv_sum_pokemon'] = pokemon['name']

        # Phase lowest IV sum record
        if not stats['totals'].get('phase_lowest_iv_sum') or pokemon['IVSum'] <= stats['totals'].get('phase_lowest_iv_sum', 999):
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

        if config['log_encounters']:
            # Log all encounters to a CSV file per phase
            csvpath = 'stats/encounters/'
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
            header = False if os.path.exists(f'{csvpath}{csvfile}') else True
            pd_pokemon.to_csv(f'{csvpath}{csvfile}', mode='a', encoding='utf-8', index=False, header=header)

        # Pokémon shiny average
        if stats['pokemon'][pokemon['name']].get('shiny_encounters'):
            avg = int(math.floor(stats['pokemon'][pokemon['name']]['encounters'] / stats['pokemon'][pokemon['name']]['shiny_encounters']))
            stats['pokemon'][pokemon['name']]['shiny_average'] = f'1/{avg:,}'

        # Total shiny average
        if stats['totals'].get('shiny_encounters'):
            avg = int(math.floor(stats['totals']['encounters'] / stats['totals']['shiny_encounters']))
            stats['totals']['shiny_average'] = f'1/{avg:,}'

        # Log encounter to encounter_log
        log_obj = {
            'time_encountered': str(datetime.now()),
            'pokemon_obj': pokemon,
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
            shiny_log = GetShinyLog()
            shiny_log['shiny_log'].append(log_obj)
            WriteFile(files['shiny_log'], json.dumps(shiny_log, indent=4, sort_keys=True))

        # Same Pokémon encounter streak records
        if len(encounter_log['encounter_log']) > 1 and \
                encounter_log['encounter_log'][-2]['pokemon_obj']['name'] == pokemon['name']:
            stats['totals']['current_streak'] = stats['totals'].get('current_streak', 0) + 1
        else:
            stats['totals']['current_streak'] = 1
        if stats['totals'].get('current_streak', 0) >= stats['totals'].get('phase_streak', 0):
            stats['totals']['phase_streak'] = stats['totals'].get('current_streak', 0)
            stats['totals']['phase_streak_pokemon'] = pokemon['name']

        if pokemon['shiny']:
            stats['pokemon'][pokemon['name']]['shiny_encounters'] = stats['pokemon'][pokemon['name']].get('shiny_encounters', 0) + 1
            stats['totals']['shiny_encounters'] = stats['totals'].get('shiny_encounters', 0) + 1

        log.info(f'------------------ {pokemon["name"]} ------------------')
        log.info('{} encountered at {}'.format(
            pokemon['name'],
            pokemon['metLocation']))
        log.info('HP: {} | ATK: {} | DEF: {} | SPATK: {} | SPDEF: {} | SPE: {}'.format(
            pokemon['IVs']['hp'],
            pokemon['IVs']['attack'],
            pokemon['IVs']['defense'],
            pokemon['IVs']['spAttack'],
            pokemon['IVs']['spDefense'],
            pokemon['IVs']['speed']))
        log.info('Shiny Value (SV): {:,} (is {:,} < 8 = {})'.format(
            pokemon['shinyValue'],
            pokemon['shinyValue'],
            pokemon['shiny']))
        log.info('Phase encounters: {:,} | {} Phase Encounters: {:,}'.format(
            stats['totals']['phase_encounters'],
            pokemon['name'],
            stats['pokemon'][pokemon['name']]['phase_encounters']))
        log.info('{} Encounters: {:,} | Lowest {} SV seen this phase: {:,}'.format(
            pokemon['name'],
            stats['pokemon'][pokemon['name']]['encounters'],
            pokemon['name'],
            stats['pokemon'][pokemon['name']]['phase_lowest_sv']))
        log.info('Shiny {} Encounters: {:,} | {} Shiny Average: {}'.format(
            pokemon['name'],
            stats['pokemon'][pokemon['name']].get('shiny_encounters', 0),
            pokemon['name'],
            stats['pokemon'][pokemon['name']].get('shiny_average', 0)))
        log.info('Total Encounters: {:,} | Total Shiny Encounters: {:,} | Total Shiny Average: {}'.format(
            stats['totals']['encounters'],
            stats['totals'].get('shiny_encounters', 0),
            stats['totals'].get('shiny_average', 0)))
        log.info('Encounter rate: {:,}/h'.format(
            GetEncounterRate()))
        log.info(f'--------------------------------------------------')

        # TODO
        #if pokemon['shiny']:
        #    time.sleep(config['misc'].get('shiny_delay', 0))
        #if config['misc']['obs'].get('enable_screenshot', None) and \
        #pokemon['shiny']:
        #    # Throw out Pokemon for screenshot
        #    while GetTrainer()['state'] != GameState.BATTLE:
        #        PressButton('B')
        #    WaitFrames(180)
        #    for key in config['misc']['obs']['hotkey_screenshot']:
        #        pydirectinput.keyDown(key)
        #    for key in reversed(config['misc']['obs']['hotkey_screenshot']):
        #        pydirectinput.keyUp(key)

        # Run custom code in CustomHooks in a thread
        #hook = (copy.deepcopy(pokemon), copy.deepcopy(stats))
        #Thread(target=CustomHooks, args=(hook,)).start()

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
            for pokemon['name'] in stats['pokemon']:
                stats['pokemon'][pokemon['name']].pop('phase_encounters', None)
                stats['pokemon'][pokemon['name']].pop('phase_highest_sv', None)
                stats['pokemon'][pokemon['name']].pop('phase_lowest_sv', None)
                stats['pokemon'][pokemon['name']].pop('phase_highest_iv_sum', None)
                stats['pokemon'][pokemon['name']].pop('phase_lowest_iv_sum', None)

        # Save stats file
        WriteFile(files['totals'], json.dumps(stats, indent=4, sort_keys=True))
        session_encounters += 1

        # Backup stats folder every n encounters
        if config['backup_stats'] > 0 and \
        stats['totals'].get('encounters', None) and \
        stats['totals']['encounters'] % config['backup_stats'] == 0:
            BackupFolder('./stats/', './backups/stats-{}.zip'.format(time.strftime('%Y%m%d-%H%M%S')))

    except Exception as e:
        log.exception(str(e))
        return False


#def EncounterPokemon():
#    """
#    Call when a Pokémon is encountered, decides whether or not to battle, flee or catch.
#    :return: returns once the encounter is over
#    """
#    legendary_hunt = config['bot_mode'] in ['manual', 'rayquaza', 'kyogre', 'groudon', 'southern island', 'regis',
#                                            'deoxys resets', 'deoxys runaways', 'mew']
#
#    log.info('Identifying Pokemon...')
#    ReleaseAllInputs()
#
#    if starter:
#        WaitFrames(30)
#
#    if GetTrainer()['state'] == GameState.OVERWORLD:
#        return False
#
#    pokemon = GetParty()[0] if starter else GetOpponent()
#    LogEncounter(pokemon)
#
#    replace_battler = False
#
#    if pokemon['shiny']:
#        if not starter and not legendary_hunt and config['catch_shinies']:
#            blocked = GetBlockList()
#            opponent = GetOpponent()
#            if opponent['name'] in blocked['block_list']:
#                log.info('---- Pokemon is in list of non-catpures. Fleeing battle ----')
#                if config['discord']['messages']:
#                    try:
#                        content = f'Encountered shiny {opponent['name']}... but catching this species is disabled. Fleeing battle!'
#                        webhook = DiscordWebhook(url=config['discord']['webhook_url'], content=content)
#                        webhook.execute()
#                    except Exception as e:
#                        log.exception(str(e))
#                        pass
#                FleeBattle()
#            else:
#                CatchPokemon()
#        elif legendary_hunt:
#            input('Pausing bot for manual intervention. (Don't forget to pause the pokebot.lua script so you can '
#                  'provide inputs). Press Enter to continue...')
#        elif not config['catch_shinies']:
#            FleeBattle()
#        return True
#    else:
#        if config['bot_mode'] == 'manual':
#            while GetTrainer()['state'] != GameState.OVERWORLD:
#                WaitFrames(100)
#        elif starter:
#            return False
#
#        if CustomCatchConfig(pokemon):
#            CatchPokemon()
#
#        if not legendary_hunt:
#            if config['battle']:
#                battle_won = BattleOpponent()
#                replace_battler = not battle_won
#            else:
#                FleeBattle()
#        elif config['bot_mode'] == 'deoxys resets':
#            if not config['mem_hacks']:
#                # Wait until sprite has appeared in battle before reset
#                WaitFrames(240)
#            ResetGame()
#            return False
#        else:
#            FleeBattle()
#
#        if config['pickup'] and not legendary_hunt:
#            PickupItems()
#
#        # If total encounters modulo config['save_every_x_encounters'] is 0, save the game
#        # Save every x encounters to prevent data loss (pickup, levels etc)
#        stats = GetStats()
#        if config['autosave_encounters'] > 0 and stats['totals']['encounters'] > 0 and \
#                stats['totals']['encounters'] % config['autosave_encounters'] == 0:
#            SaveGame()
#
#        if replace_battler:
#            if not config['cycle_lead_pokemon']:
#                log.info('Lead Pokemon can no longer battle. Ending the script!')
#                FleeBattle()
#                return False
#            else:
#                StartMenu('pokemon')
#
#                # Find another healthy battler
#                party_pp = [0, 0, 0, 0, 0, 0]
#                for i, mon in enumerate(GetParty()):
#                    if mon is None:
#                        continue
#
#                    if mon['hp'] > 0 and i != 0:
#                        for j, move in enumerate(mon['enrichedMoves']):
#                            if IsValidMove(move) and mon['pp'][j] > 0:
#                                party_pp[i] += move['pp']
#
#                highest_pp = max(party_pp)
#                lead_idx = party_pp.index(highest_pp)
#
#                if highest_pp == 0:
#                    log.info('Ran out of Pokemon to battle with. Ending the script!')
#                    os._exit(1)
#
#                lead = GetParty()[lead_idx]
#                if lead is not None:
#                    log.info(f'Replacing lead battler with {lead['name']} (Party slot {lead_idx})')
#
#                PressButton('A')
#                WaitFrames(60)
#                PressButton('A')
#                WaitFrames(15)
#
#                for _ in range(3):
#                    PressButton('Up')
#                    WaitFrames(15)
#
#                PressButton('A')
#                WaitFrames(15)
#
#                for _ in range(lead_idx):
#                    PressButton('Down')
#                    WaitFrames(15)
#
#                # Select target Pokémon and close out menu
#                PressButton('A')
#                WaitFrames(60)
#
#                log.info('Replaced lead Pokemon!')
#
#                for _ in range(5):
#                    PressButton('B')
#                    WaitFrames(15)
#        return False
