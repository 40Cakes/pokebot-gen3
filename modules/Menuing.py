import os
from typing import NoReturn

from modules.Config import config_battle, config_cheats
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import ReadSymbol, GetGameState, GetParty, DecodeString, \
    GetPartyMenuCursorPos, ParseStartMenu, ParseMenu, mGBA, ParseTasks,  GetTaskFunc, \
    ParsePartyMenuInternal, GetCursorOptions
from modules.Console import console
from modules.Enums import GameState, TaskFunc


def CheckForPickup(encounter_total: int) -> NoReturn:
    """
    Function that handles pickup farming.
    """
    pokemon_with_pickup = 0
    pokemon_with_pickup_and_item = []
    party = GetParty()
    for i in range(len(party)):
        if party[i]['ability'] == 'Pickup':
            pokemon_with_pickup += 1
            if party[i]['item']['name'] != 'None':
                pokemon_with_pickup_and_item.append(i)
    if not config_cheats['pickup']:
        encounter_threshold_met = encounter_total % config_battle['pickup_check_frequency'] == 0
        if encounter_threshold_met and pokemon_with_pickup > 0:
            NavigateStartMenu("POKEMON")
            while not PartyMenuIsOpen():
                PressButton(['A'])
    else:
        encounter_threshold_met = True
    try:
        pickup_threshold = config_battle['pickup_threshold']
    except:
        pickup_threshold = 1

    if pickup_threshold > pokemon_with_pickup > 0:
        pickup_threshold = pokemon_with_pickup
    if len(pokemon_with_pickup_and_item) >= pickup_threshold and encounter_threshold_met:
        console.print('Pickup threshold is met! Gathering items.')
        if not PartyMenuIsOpen():
            NavigateStartMenu("POKEMON")
            while not PartyMenuIsOpen():
                PressButton(['A'])
        TakePickupItems(pokemon_with_pickup_and_item)
    else:
        ExitToOverworldFromPartyMenu()


def TakePickupItems(pokemon_indices: list):
    """
    Function that takes items from Pokémon that have the Pickup ability.

    :param pokemon_indices: The list of indices representing the Pokémon to take items from.
    """
    for idx in pokemon_indices:
        while GetPartyMenuCursorPos()['slot_id'] != idx:
            if GetPartyMenuCursorPos()['slot_id'] > idx:
                PressButton(['Up'])
            else:
                PressButton(["Down"])
        if mGBA.game in ['Pokémon Emerald', 'Pokémon FireRed', 'Pokémon LeafGreen']:
            while 'Choose a' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                PressButton(['A'])
            while 'Do what with' in DecodeString(ReadSymbol('gStringVar4')) and 'an item?' not in \
                    DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                NavigateMenu("ITEM")
            while 'Do what with an' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                NavigateMenu("TAKE_ITEM")
            while 'Received the' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                PressButton(['B'])
        else:
            while 'SUB_8089D94' not in [task['func'] for task in ParseTasks()]:
                PressButton(['A'])
                WaitFrames(1)
            while 'SUB_8089D94' in [task['func'] for task in ParseTasks()] and \
                    'SUB_808A060' not in [task['func'] for task in ParseTasks()]:
                NavigateMenu("ITEM")
                WaitFrames(1)
            while 'SUB_808A060' in [task['func'] for task in ParseTasks()]:
                NavigateMenuByIndex(1)
                WaitFrames(1)
            while TaskFunc.PARTY_MENU not in [GetTaskFunc(task['func']) for task in ParseTasks()]:
                PressButton(['B'])
                WaitFrames(1)
    ExitToOverworldFromPartyMenu()


def ExitToOverworldFromPartyMenu():
    """
    helper func to leave party menu and return to overworld
    """
    while GetGameState() != GameState.OVERWORLD or ParseStartMenu()['open']:
        PressButton(['B'])
    for i in range(30):
        if GetGameState() != GameState.OVERWORLD or ParseStartMenu()['open']:
            break
        PressButton(['B'])
    while GetGameState() != GameState.OVERWORLD or ParseStartMenu()['open']:
        PressButton(['B'])


def NavigateStartMenu(desired_option: str) -> NoReturn:
    """
    Opens the start menu and moves to the option with the desired index from the menu.

    :param desired_option: The option to select from the menu.
    """
    while not ParseStartMenu()['open']:
        PressButton(['Start'])
    current_cursor_position = ParseStartMenu()['cursor_pos']
    desired_index = ParseStartMenu()['actions'].index(desired_option)
    num_actions = len(ParseStartMenu()['actions'])
    while current_cursor_position != desired_index:

        if current_cursor_position < desired_index:
            up_presses = current_cursor_position + num_actions - desired_index
            down_presses = desired_index - current_cursor_position
        else:
            up_presses = current_cursor_position - desired_index
            down_presses = desired_index - current_cursor_position + num_actions
        if down_presses > up_presses:
            PressButton(['Up'])
        else:
            PressButton(['Down'])
        current_cursor_position = ParseStartMenu()['cursor_pos']


def NavigateMenu(desired_option: str) -> NoReturn:
    """
    Given a menu choice, attempts to navigate to the choice and press A.
    """
    party_menu_internal = ParsePartyMenuInternal()
    for i in range(30):
        if party_menu_internal['numActions'] <= 8:
            break
        WaitFrames(1)
        party_menu_internal = ParsePartyMenuInternal()
    if party_menu_internal['numActions'] > 8:
        console.print("Error navigating menu.")
        os._exit(-1)
    desired_index = -1
    for i in range(party_menu_internal['numActions']):
        if GetCursorOptions(party_menu_internal['actions'][i]) == desired_option:
            desired_index = i
            break
    if desired_index == -1:
        console.print("Desired option not found.")
        os._exit(-1)
    if ParseMenu()['cursorPos'] > ParseMenu()['maxCursorPos'] or desired_index < ParseMenu()['minCursorPos']:
        console.print('Can\'t select this option.')
        return
    while ParseMenu()['cursorPos'] != desired_index:

        if ParseMenu()['cursorPos'] > desired_index:
            PressButton(['Up'])
        else:
            PressButton(['Down'])

    while ParseMenu()['cursorPos'] != desired_index:
        if ParseMenu()['cursorPos'] < desired_index:
            up_presses = ParseMenu()['cursorPos'] + party_menu_internal['numActions'] - desired_index
            down_presses = desired_index - ParseMenu()['cursorPos']
        else:
            up_presses = ParseMenu()['cursorPos'] - desired_index
            down_presses = desired_index - ParseMenu()['cursorPos'] + party_menu_internal['numActions']
        if down_presses > up_presses:
            PressButton(['Up'])
        else:
            PressButton(['Down'])

    PressButton(['A'])


def NavigateMenuByIndex(desired_index: int) -> NoReturn:
    """
    Given an index, attempts to navigate to the index and press A.

    :param desired_index: the index to navigate to
    """
    if desired_index == -1:
        console.print("Desired option not found.")
        os._exit(-1)
    if ParseMenu()['cursorPos'] > ParseMenu()['maxCursorPos'] or desired_index < ParseMenu()['minCursorPos']:
        console.print('Can\'t select this option.')
        return
    num_options = ParseMenu()['maxCursorPos'] + 1
    while ParseMenu()['cursorPos'] != desired_index:
        if ParseMenu()['cursorPos'] < desired_index:
            up_presses = ParseMenu()['cursorPos'] + num_options - desired_index
            down_presses = desired_index - ParseMenu()['cursorPos']
        else:
            up_presses = ParseMenu()['cursorPos'] - desired_index
            down_presses = desired_index - ParseMenu()['cursorPos'] + num_options
        if down_presses > up_presses:
            PressButton(['Up'])
        else:
            PressButton(['Down'])
    PressButton(['A'])


def PartyMenuIsOpen() -> bool:
    if mGBA.game in ['Pokémon Emerald', 'Pokémon FireRed', 'Pokémon LeafGreen']:
        return GetGameState() == GameState.PARTY_MENU
    else:
        return TaskFunc.PARTY_MENU in [GetTaskFunc(task['func']) for task in ParseTasks()]


def RotatePokemon():
    """
    function to swap out lead battler if PP or HP get too low
    """
    NavigateStartMenu("POKEMON")
    while not PartyMenuIsOpen():
        PressButton(['A'])
    party = GetParty()
    new_lead_idx = 0
    for i in range(len(party)):
        if party[i]['stats']['hp'] > 0:
            console.print('Pokémon {} has hp!'.format(party[i]['name']))
            for move in party[i]['moves']:
                if move['power'] > 0 and move['remaining_pp'] > 0 and move['name'] not in config_battle['banned_moves']:
                    console.print('Pokémon {} has usable moves!'.format(party[i]['name']))
                    new_lead_idx = i
                    break
            if new_lead_idx > 0:
                break
    if new_lead_idx > 0:

        while GetPartyMenuCursorPos()['slot_id'] != new_lead_idx:
            if GetPartyMenuCursorPos()['slot_id'] > new_lead_idx:
                PressButton(['Up'])
            else:
                PressButton(['Down'])

        if mGBA.game in ['Pokémon Emerald', 'Pokémon FireRed', 'Pokémon LeafGreen']:
            while 'Choose' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                PressButton(['A'])
            while 'Do what with' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                NavigateMenu("SWITCH")
            while 'Move to' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                if GetPartyMenuCursorPos()['slot_id_2'] != 0:
                    PressButton(['Up'])
                else:
                    PressButton(['A'])
            while 'Choose' in DecodeString(ReadSymbol('gStringVar4')):  # TODO English only
                PressButton(['B'])
        else:
            while 'SUB_8089D94' not in [task['func'] for task in ParseTasks()]:
                PressButton(['A'])
                WaitFrames(1)
            while (
                    'SUB_8089D94' in [task['func'] for task in ParseTasks()]
            ) and not (
                    'SUB_808A060' in [task['func'] for task in ParseTasks()] or
                    'HANDLEPARTYMENUSWITCHPOKEMONINPUT' in [task['func'] for task in ParseTasks()]
            ):
                NavigateMenu("SWITCH")
                WaitFrames(1)
            while SwitchPokemonActive():
                if GetPartyMenuCursorPos()['slot_id_2'] != 0:
                    PressButton(['Up'])
                else:
                    PressButton(['A'])
                WaitFrames(1)
            while TaskFunc.PARTY_MENU not in [GetTaskFunc(task['func']) for task in ParseTasks()]:
                PressButton(['B'])
                WaitFrames(1)

        while GetGameState() != GameState.OVERWORLD or ParseStartMenu()['open']:
            PressButton(['B'])
        for i in range(30):
            if GetGameState() != GameState.OVERWORLD or ParseStartMenu()['open']:
                break
            PressButton(['B'])
        while GetGameState() != GameState.OVERWORLD or ParseStartMenu()['open']:
            PressButton(['B'])
    else:
        console.print('No Pokémon are fit for battle.')
        os._exit(0)


def SwitchPokemonActive() -> bool:
    """
    helper function to determine if the switch Pokémon menu is active
    """
    tasks = ParseTasks()
    for task in tasks:
        if task['func'] == 'HANDLEPARTYMENUSWITCHPOKEMONINPUT' and task['isActive']:
            return True
    return False
