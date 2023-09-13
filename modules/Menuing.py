import random
from typing import NoReturn
import os

from modules.Config import config_battle
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import ReadSymbol, GetTrainer, pokemon_list, type_list, GetParty, GetOpponent, DecodeString, \
    GetPartyMenuCursorPos, ParseStartMenu, ParseMenu, ParseBattleCursor, mGBA, ParseTasks, ReadAddress, \
    moves_list, ParseMain
from modules.data.GameState import GameState
from modules.Console import console
from modules.data.TaskFunc import TaskFunc

if mGBA.game in ['Pokémon Ruby', 'Pokémon Sapphire']:
    battle_text = "What should"
else:
    battle_text = "What will"


def SelectBattleOption(desired_option: int, cursor_type: str = 'gActionSelectionCursor') -> NoReturn:
    """
    Takes a desired battle menu option, navigates to it, and presses it.

    :param desired_option: The desired index for the selection. For the base battle menu, 0 will be FIGHT, 1 will be
    BAG, 2 will be PKMN, and 3 will be RUN.
    :param cursor_type: The symbol to use for the cursor. This is different between selecting moves and selecting battle
     options.
    """
    while ParseBattleCursor(cursor_type) != desired_option:
        match (ParseBattleCursor(cursor_type) % 2) - (desired_option % 2):
            case - 1:
                PressButton(['Right'])
            case 1:
                PressButton(['Left'])
        match (ParseBattleCursor(cursor_type) // 2) - (desired_option // 2):
            case - 1:
                PressButton(['Down'])
            case 1:
                PressButton(['Up'])
            case 0:
                pass
    if ParseBattleCursor(cursor_type) == desired_option:
        # get current displayed string
        current_string = DecodeString(ReadSymbol('gDisplayedStringBattle'))
        # mash A until the string changes
        while DecodeString(ReadSymbol('gDisplayedStringBattle')) == current_string:
            PressButton(['A'])


def FleeBattle() -> NoReturn:
    """
    Readable function to select and execute the Run option from the battle menu.
    """
    while GetTrainer()['state'] != GameState.OVERWORLD:
        if "Use next" in DecodeString(ReadSymbol('gDisplayedStringBattle')):
            PressButton(["B"])
        elif battle_text in DecodeString(ReadSymbol('gDisplayedStringBattle')):
            SelectBattleOption(3, cursor_type='gActionSelectionCursor')
        else:
            PressButton(['B'])


def getMovePower(move, ally_types, foe_types, ally_attacks, foe_defenses) -> float:
    """
    function to calculate effective power of a move

    """
    power = move['power']

    # Ignore banned moves and those with 0 PP
    if (not isValidMove(move)) or (move['remaining_pp'] == 0):
        return 0

    matchups = type_list[move["type"]]
    category = matchups["category"]

    for foe_type in foe_types:
        if foe_type in matchups['immunes']:
            return 0
        elif foe_type in matchups['weaknesses']:
            power *= 0.5
        elif foe_type in matchups['strengths']:
            power *= 2

    # STAB (same-type attack bonus)
    if move['type'] in ally_types:
        power *= 1.5

    # calculating attack/defense effect
    stat_calc = ally_attacks[category] / foe_defenses[category]
    # console.print(f"Move {move['name']} has base power of {power} and stat bonus of {stat_calc}")
    power *= stat_calc

    return power


def isValidMove(move: dict) -> bool:
    return move['name'] not in config_battle['banned_moves'] and move['power'] > 0


def CalculateNewMoveViability(mon: dict, new_move: dict) -> int:
    """
    Function that judges the move a Pokemon is trying to learn against its moveset and returns the index of the worst
    move of the bunch.

    :param mon: The dict containing the Pokemon's info.
    :param new_move: The move that the mon is trying to learn
    :return: The index of the move to select.
    """
    # exit learning move if new move is banned or has 0 power
    if new_move['power'] == 0 or new_move['name'] in config_battle['banned_moves']:
        console.print(f"New move has base power of 0, so {mon['name']} will skip learning it.")
        return 4
    # determine how the damage formula will be affected by the mon's current stats
    attack_stat = {
        'Physical': mon['stats']['attack'],
        'Special': mon['stats']['spAttack'],
    }
    # get the effective power of each move
    move_power = []
    full_moveset = list(mon['moves'])
    full_moveset.append(new_move)
    for move in full_moveset:
        attack_type = move['kind']
        match attack_type:
            case "Physical":
                attack_bonus = mon['stats']['attack']
            case "Special":
                attack_bonus = mon['stats']['spAttack']
            case _:
                attack_bonus = 0
        power = move['power'] * attack_bonus
        if move['type'] in mon['type']:
            power *= 1.5
        if move['name'] in config_battle['banned_moves']:
            power = 0
        move_power.append(power)
    # find the weakest move of the bunch
    weakest_move_power = min(move_power)
    weakest_move = move_power.index(weakest_move_power)
    # try and aim for good coverage- it's generally better to have a wide array of move types than 4 moves of the same
    # type
    redundant_type_moves = []
    existing_move_types = {}
    for move in full_moveset:
        if move['power'] == 0:
            continue
        if move['type'] not in existing_move_types:
            existing_move_types[move['type']] = move
        else:
            if not redundant_type_moves:
                redundant_type_moves.append(existing_move_types[move['type']])
            redundant_type_moves.append(move)
    if weakest_move_power > 0 and redundant_type_moves:
        redundant_move_power = []
        for move in redundant_type_moves:
            attack_type = move['kind']
            match attack_type:
                case "Physical":
                    attack_bonus = mon['stats']['attack']
                case "Special":
                    attack_bonus = mon['stats']['spAttack']
                case _:
                    attack_bonus = 0
            power = move['power'] * attack_bonus
            if move['type'] in mon['type']:
                power *= 1.5
            if move['name'] in config_battle['banned_moves']:
                power = 0
            redundant_move_power.append(power)
        weakest_move_power = min(redundant_move_power)
        weakest_move = full_moveset.index(redundant_type_moves[redundant_move_power.index(weakest_move_power)])
        console.print("Opting to replace a move that has a redundant type so as to maximize coverage.")
    console.print(f"Move to replace is {full_moveset[weakest_move]['name']} with a calculated power of {weakest_move_power}")
    return weakest_move


def FindEffectiveMove(ally: dict, foe: dict) -> dict:
    """
    Finds the best move for the ally to use on the foe.

    :param ally: The pokemon being used to battle.
    :param foe: The pokemon being battled.
    :return: A dictionary containing the name of the move to use, the move's index, and the effective power of the move.
    """
    move_power = []
    foe_types = pokemon_list[foe["name"]]["type"]
    foe_defenses = {
        'physical': foe['stats']['defense'],
        'special': foe['stats']['spDefense'],
    }
    ally_types = pokemon_list[ally["name"]]["type"]
    ally_attacks = {
        'physical': foe['stats']['attack'],
        'special': foe['stats']['spAttack'],
    }

    # calculate power of each possible move
    for i, move in enumerate(ally["moves"]):
        move_power.append(getMovePower(move, ally_types, foe_types, ally_attacks, foe_defenses))

    # calculate best move and return info
    best_move_index = move_power.index(max(move_power))
    return {
        'name': ally['moves'][best_move_index]['name'],
        'index': best_move_index,
        'power': max(move_power),
    }


def BattleOpponent() -> bool:
    """
    Function to battle wild Pokémon. This will only battle with the lead pokemon of the party, and will run if it dies
    or runs out of PP.
    :return: Boolean value of whether the battle was won.
    """
    ally_fainted = False
    foe_fainted = False

    while not ally_fainted and not foe_fainted and GetTrainer()['state'] not in (
            GameState.OVERWORLD, GameState.WHITEOUT
    ) and "scurried" not in DecodeString(ReadSymbol('gStringVar4')):
        if GetTrainer()['state'] == GameState.OVERWORLD:
            return True

        best_move = FindEffectiveMove(GetParty()[0], GetOpponent())

        if best_move['power'] < 10:
            console.print('Lead pokemon has no effective moves to battle the foe!')
            FleeBattle()
            return False

        # If effective moves are present, let's fight this thing!
        while battle_text in DecodeString(ReadSymbol("gDisplayedStringBattle")):
            SelectBattleOption(0, cursor_type="gActionSelectionCursor")

        WaitFrames(5)

        console.print('Best move against foe is {} (Effective power is {})'.format(
            best_move['name'],
            best_move['power']
        ))

        SelectBattleOption(best_move['index'], cursor_type='gMoveSelectionCursor')

        WaitFrames(5)

        while (
                GetTrainer()["state"] != GameState.OVERWORLD and
                battle_text not in DecodeString(ReadSymbol('gDisplayedStringBattle')) and
                "whited out!" not in DecodeString(ReadSymbol('gDisplayedStringBattle'))
        ):
            while GetTrainer()["state"] == GameState.EVOLUTION:
                if config_battle['stop_evolution']:
                    PressButton(['B'])
                else:
                    PressButton(['A'])
                if 'elete a move' in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                    break
            if 'elete a move' not in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                PressButton(['B'])
                WaitFrames(1)
            if 'elete a move' in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                HandleMoveLearn()

        ally_fainted = GetParty()[0]['stats']['hp'] == 0
        foe_fainted = GetOpponent()['stats']['hp'] == 0

    if ally_fainted:
        console.print('Lead Pokemon fainted!')
        party = GetParty()
        if sum([party[key]['stats']['hp'] for key in party.keys()]) == 0:
            console.print("All pokemon have fainted.")
            os._exit(0)
        FleeBattle()
        return False
    else:
        while GetTrainer()["state"] != GameState.OVERWORLD:
            while GetTrainer()["state"] == GameState.EVOLUTION:
                if config_battle['stop_evolution']:
                    PressButton(['B'])
                else:
                    PressButton(['A'])
            if 'Delete a move' not in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                PressButton(['B'])
                WaitFrames(1)
            if 'Delete a move' in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                HandleMoveLearn()
    return True


def HandleMoveLearn():
    match config_battle['new_move']:
        case 'stop':
            console.print('New move trying to be learned, stopping bot...')
            input('Press enter to exit...')
            os._exit(0)
        case 'cancel':
            while GetTrainer()['state'] != GameState.OVERWORLD:
                while GetTrainer()['state'] == GameState.EVOLUTION:
                    if config_battle['stop_evolution']:
                        PressButton(['B'])
                    else:
                        PressButton(['A'])
                if 'Stop learning' not in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                    PressButton(['B'])
                else:
                    PressButton(['A'])
        case 'learn_best':
            on_learn_screen = False
            while not on_learn_screen:
                for task in ParseTasks():
                    if task['task_func'] in [TaskFunc.LEARN_MOVE_RS, TaskFunc.LEARN_MOVE_E, TaskFunc.LEARN_MOVE_FRLG]:
                        if task['is_active']:
                            on_learn_screen = True
                            break
                PressButton(['A'])

            learning_mon = GetLearningMon()
            learning_move = GetLearningMove()
            worst_move = CalculateNewMoveViability(learning_mon, learning_move)
            while GetMoveLearningCursorPos() != worst_move:
                if GetMoveLearningCursorPos() > worst_move:
                    PressButton(['Up'])
                else:
                    PressButton(['Down'])
            while GetTrainer()['state'] != GameState.BATTLE:
                PressButton(['A'])
            while "Stop learning" in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                PressButton(['A'])

        case _:
            console.print("Config new_move_mode invalid.")


def GetLearningMon() -> dict:
    idx = int.from_bytes(ReadAddress(int.from_bytes(ReadSymbol('sMonSummaryScreen'), 'little'), offset=16574, size=1),
                         'little')
    return GetParty()[idx]


def GetLearningMove() -> dict:
    """
    helper function that returns the move trying to be learned
    """
    return moves_list[
        int.from_bytes(ReadAddress(int.from_bytes(ReadSymbol('sMonSummaryScreen'), 'little'), offset=16580, size=2),
                       'little')]


def GetMoveLearningCursorPos() -> int:
    """
    helper function that returns the position of the move learning cursor
    """
    return int.from_bytes(
        ReadAddress(int.from_bytes(ReadSymbol('sMonSummaryScreen'), 'little'), offset=16582), 'little'
    )


def CheckForPickup() -> NoReturn:
    """
    Function that handles pickup farming.
    """
    try:
        pickup_threshold = config_battle["pickup_threshold"]
    except:
        pickup_threshold = 1
    pokemon_with_pickup = 0
    pokemon_with_pickup_and_item = []
    party = GetParty()
    for i in range(len(party)):
        if party[i]['ability'] == "Pickup":
            pokemon_with_pickup += 1
            if party[i]['item']['name'] != 'None':
                pokemon_with_pickup_and_item.append(i)
    if pickup_threshold > pokemon_with_pickup > 0:
        console.print(
            "The pickup threshold is higher than the number of pokemon in the party with pickup, so the latter number will be used.")
        pickup_threshold = pokemon_with_pickup
    if len(pokemon_with_pickup_and_item) >= pickup_threshold:
        console.print("Pickup threshold is met! Gathering items.")
        TakePickupItems(pokemon_with_pickup_and_item)


def TakePickupItems(pokemon_indices: list):
    """
    Function that takes items from pokemon that have the Pickup ability.

    :param pokemon_indices: The list of indices representing the pokemon to take items from.
    """
    NavigateStartMenu(1)
    while GetTrainer()['state'] != GameState.PARTY_MENU:
        PressButton(["A"])
    for idx in pokemon_indices:
        while ParsePartyMenu()['slot_id'] != idx:
            if ParsePartyMenu()['slot_id'] > idx:
                PressButton(["Up"])
            else:
                PressButton(["Down"])
        while "Choose a" in DecodeString(ReadSymbol('gStringVar4')):
            PressButton(["A"])
        while "Do what with this" in DecodeString(ReadSymbol('gStringVar4')):
            NavigateMenu(2)
        while "Do what with an" in DecodeString(ReadSymbol('gStringVar4')):
            NavigateMenu(1)
        while "Received the" in DecodeString(ReadSymbol('gStringVar4')):
            PressButton(['B'])
    while GetTrainer()['state'] != GameState.OVERWORLD or ParseStartMenu()['open']:
        PressButton(['B'])
    for i in range(30):
        if GetTrainer()['state'] != GameState.OVERWORLD or ParseStartMenu()['open']:
            break
        PressButton(['B'])
    while GetTrainer()['state'] != GameState.OVERWORLD or ParseStartMenu()['open']:
        PressButton(['B'])


def NavigateStartMenu(desired_index: int) -> NoReturn:
    """
    Opens the start menu and moves to the option with the desired index from the menu.

    :param desired_index: The index of the option to select from the menu.
    """
    while not ParseStartMenu()['open']:
        PressButton(['Start'])
    current_cursor_position = ParseStartMenu()['cursor_pos']
    while current_cursor_position != desired_index:
        if current_cursor_position < desired_index:
            PressButton(["Down"])
        else:
            PressButton(['Up'])
        current_cursor_position = ParseStartMenu()['cursor_pos']


def NavigateMenu(desired_index: int) -> NoReturn:
    """
    Given an index, attempts to navigate to the index and press A.
    """
    if desired_index > ParseMenu()['maxCursorPos'] or desired_index < ParseMenu()['minCursorPos']:
        console.print("Can't select this option.")
        return
    while ParseMenu()['cursorPos'] != desired_index:
        if ParseMenu()['cursorPos'] > desired_index:
            PressButton(["Up"])
        else:
            PressButton(["Down"])
    PressButton(["A"])


def RotatePokemon():
    """
    function to swap out lead battler if PP or HP get too low
    """
    NavigateStartMenu(1)
    while GetTrainer()['state'] != GameState.PARTY_MENU:
        PressButton(["A"])
    party = GetParty()
    new_lead_idx = 0
    for i in range(len(party)):
        if party[i]['stats']['hp'] > 0:
            print(f"Pokemon {party[i]['name']} has hp!")
            for move in party[i]['moves']:
                if move['power'] > 0 and move['remaining_pp'] > 0:
                    print(f"Pokemon {party[i]['name']} has usable moves!")
                    new_lead_idx = i
                    break
            if new_lead_idx > 0:
                break
    if new_lead_idx > 0:

        while ParsePartyMenu()['slot_id'] != new_lead_idx:
            if ParsePartyMenu()['slot_id'] > new_lead_idx:
                PressButton(["Up"])
            else:
                PressButton(["Down"])

        while "Choose" in DecodeString(ReadSymbol('gStringVar4')):
            PressButton(["A"])
        while "Do what with this" in DecodeString(ReadSymbol('gStringVar4')):
            NavigateMenu(1)
        while "Move to" in DecodeString(ReadSymbol('gStringVar4')):
            if ParsePartyMenu()['slot_id_2'] != 0:
                PressButton(['Up'])
            else:

                PressButton(['A'])
        while "Choose" in DecodeString(ReadSymbol('gStringVar4')):
            PressButton(['B'])
        while GetTrainer()['state'] != GameState.OVERWORLD or ParseStartMenu()['open']:
            PressButton(['B'])
        for i in range(30):
            if GetTrainer()['state'] != GameState.OVERWORLD or ParseStartMenu()['open']:
                break
            PressButton(['B'])
        while GetTrainer()['state'] != GameState.OVERWORLD or ParseStartMenu()['open']:
            PressButton(['B'])
    else:
        console.print("No pokemon are fit for battle.")
        os._exit
