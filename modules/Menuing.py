from typing import NoReturn

from modules.Config import config, ForceManualMode
from modules.Gui import GetROM
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import GetGameState, GetCursorOptions, ParseTasks, GetTaskFunc, \
    GetTask
from modules.Console import console
from modules.Enums import GameState, TaskFunc
from modules.MenuParsers import GetPartyMenuCursorPos, ParseStartMenu, ParsePartyMenuInternal, ParseMenu
from modules.Pokemon import GetParty


def CheckForPickup(encounter_total: int) -> NoReturn:
    """
    Function that handles pickup farming.
    """
    n = 0
    pokemon_with_pickup = 0
    pokemon_with_pickup_and_item = []
    party = GetParty()
    for mon in party:
        if mon['ability'] == 'Pickup':
            pokemon_with_pickup += 1
            if mon['item']['name'] != 'None':
                pokemon_with_pickup_and_item.append(n)
        n += 1
    if not config['cheats']['pickup']:
        encounter_threshold_met = encounter_total % config['battle']['pickup_check_frequency'] == 0
        if encounter_threshold_met and pokemon_with_pickup > 0:
            NavigateStartMenu("POKEMON")
            while not PartyMenuIsOpen():
                PressButton(['A'])
    else:
        encounter_threshold_met = True
    try:
        pickup_threshold = config['battle']['pickup_threshold']
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
        if GetROM().game_title in ['POKEMON EMER', 'POKEMON FIRE', 'POKEMON LEAF']:
            while GetTask('TASK_HANDLESELECTIONMENUINPUT') == {}:
                PressButton(['A'])
            while ParsePartyMenuInternal()['numActions'] > 3:
                NavigateMenu("ITEM")
            while GetParty()[idx]['item']['name'] != 'None':
                NavigateMenu("TAKE_ITEM")
            while GetTask('TASK_PRINTANDWAITFORTEXT') != {} and GetTask("TASK_PRINTANDWAITFORTEXT")['isActive']:
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


def NavigateStartMenu(desired_option: str) -> None:
    """
    Opens the start menu and moves to the option with the desired index from the menu.

    :param desired_option: The option to select from the menu.
    """
    while not ParseStartMenu()['open'] and not config['general']['bot_mode'] == 'manual':
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
        console.print("Error navigating menu. Switching to manual mode...")
        ForceManualMode()
    desired_index = -1
    for i in range(party_menu_internal['numActions']):
        if GetCursorOptions(party_menu_internal['actions'][i]) == desired_option or (
                desired_option == "SHIFT" and GetCursorOptions(party_menu_internal['actions'][i]) == "SEND_OUT"
        ):
            desired_index = i
            break
    if desired_index == -1:
        console.print(f"Desired option {desired_option} not found in {[GetCursorOptions(party_menu_internal['actions'][i]) for i in range(party_menu_internal['numActions'])]}.")
        console.print("Switching to manual mode...")
        ForceManualMode()
    if ParseMenu()['cursorPos'] > ParseMenu()['maxCursorPos'] or desired_index < ParseMenu()['minCursorPos']:
        console.print('Can\'t select this option.')
        return

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
        console.print("Desired option not found. Switching to manual mode...")
        ForceManualMode()
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
    if GetROM().game_title in ['POKEMON EMER', 'POKEMON FIRE', 'POKEMON LEAF']:
        return GetGameState() == GameState.PARTY_MENU
    else:
        return TaskFunc.PARTY_MENU in [GetTaskFunc(task['func']) for task in ParseTasks()]


def SwitchPokemonActive() -> bool:
    """
    helper function to determine if the switch Pokémon menu is active
    """
    tasks = ParseTasks()
    for task in tasks:
        if task['func'] == 'HANDLEPARTYMENUSWITCHPOKEMONINPUT' and task['isActive']:
            return True
    return False
