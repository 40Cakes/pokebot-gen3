import os
import struct
from typing import NoReturn

from modules.Config import config
from modules.Console import console
from modules.Game import DecodeString
from modules.Gui import GetROM
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import GetGameState, ReadSymbol, ParseTasks, GetTaskFunc, GetSymbolName, GetTask
from modules.Enums import GameState, TaskFunc, BattleState
from modules.MenuParsers import ParseBattleCursor, GetLearningMon, GetLearningMove, GetMoveLearningCursorPos, \
    GetPartyMenuCursorPos, ParseStartMenu
from modules.Menuing import PartyMenuIsOpen, NavigateMenu, NavigateStartMenu, SwitchPokemonActive
from modules.Pokemon import pokemon_list, type_list, GetParty, GetOpponent


def SelectBattleOption(desired_option: int) -> NoReturn:
    """
    Takes a desired battle menu option, navigates to it, and presses it.

    :param desired_option: The desired index for the selection. For the base battle menu, 0 will be FIGHT, 1 will be
    BAG, 2 will be PKMN, and 3 will be RUN.
     options.
    """
    battle_state = GetBattleState()
    match battle_state:
        case BattleState.ACTION_SELECTION:
            cursor_type = 'gActionSelectionCursor'
        case BattleState.MOVE_SELECTION:
            cursor_type = 'gMoveSelectionCursor'
        case _:
            WaitFrames(1)
            return
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
        while GetBattleState() == battle_state:
            PressButton(['A'])
            WaitFrames(1)


def FleeBattle() -> NoReturn:
    """
    Readable function to select and execute the Run option from the battle menu.
    """
    while GetGameState() != GameState.OVERWORLD:
        if GetBattleState() == BattleState.ACTION_SELECTION:
            SelectBattleOption(3)
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

    matchups = type_list[move['type']]
    category = matchups['category']

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
    # console.print('Move {} has base power of {} and stat bonus of {}'.format(
    #     move['name'],
    #     power,
    #     stat_calc))
    power *= stat_calc

    return power


def isValidMove(move: dict) -> bool:
    return move['name'] not in config['battle']['banned_moves'] and move['power'] > 0


def CalculateNewMoveViability(mon: dict, new_move: dict) -> int:
    """
    Function that judges the move a Pokémon is trying to learn against its moveset and returns the index of the worst
    move of the bunch.

    :param mon: The dict containing the Pokémon's info.
    :param new_move: The move that the mon is trying to learn
    :return: The index of the move to select.
    """
    # exit learning move if new move is banned or has 0 power
    if new_move['power'] == 0 or new_move['name'] in config['battle']['banned_moves']:
        console.print('New move has base power of 0, so {} will skip learning it.'.format(mon['name']))
        return 4
    # get the effective power of each move
    move_power = []
    full_moveset = list(mon['moves'])
    full_moveset.append(new_move)
    for move in full_moveset:
        attack_type = move['kind']
        match attack_type:
            case 'Physical':
                attack_bonus = mon['stats']['attack']
            case 'Special':
                attack_bonus = mon['stats']['spAttack']
            case _:
                attack_bonus = 0
        power = move['power'] * attack_bonus
        if move['type'] in mon['type']:
            power *= 1.5
        if move['name'] in config['battle']['banned_moves']:
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
                case 'Physical':
                    attack_bonus = mon['stats']['attack']
                case 'Special':
                    attack_bonus = mon['stats']['spAttack']
                case _:
                    attack_bonus = 0
            power = move['power'] * attack_bonus
            if move['type'] in mon['type']:
                power *= 1.5
            if move['name'] in config['battle']['banned_moves']:
                power = 0
            redundant_move_power.append(power)
        weakest_move_power = min(redundant_move_power)
        weakest_move = full_moveset.index(redundant_type_moves[redundant_move_power.index(weakest_move_power)])
        console.print('Opting to replace a move that has a redundant type so as to maximize coverage.')
    console.print('Move to replace is {} with a calculated power of {}'.format(
        full_moveset[weakest_move]['name'],
        weakest_move_power
    ))
    return weakest_move


def FindEffectiveMove(ally: dict, foe: dict) -> dict:
    """
    Finds the best move for the ally to use on the foe.

    :param ally: The Pokémon being used to battle.
    :param foe: The Pokémon being battled.
    :return: A dictionary containing the name of the move to use, the move's index, and the effective power of the move.
    """
    move_power = []
    foe_types = pokemon_list[foe['name']]['type']
    foe_defenses = {
        'physical': foe['stats']['defense'],
        'special': foe['stats']['spDefense'],
    }
    ally_types = pokemon_list[ally['name']]['type']
    ally_attacks = {
        'physical': foe['stats']['attack'],
        'special': foe['stats']['spAttack'],
    }

    # calculate power of each possible move
    for i, move in enumerate(ally['moves']):
        move_power.append(getMovePower(move, ally_types, foe_types, ally_attacks, foe_defenses))

    # calculate best move and return info
    best_move_index = move_power.index(max(move_power))
    return {
        'name': ally['moves'][best_move_index]['name'],
        'index': best_move_index,
        'power': max(move_power),
    }


def NavigateMoveLearnMenu(idx):
    """
    Function that handles navigation of the move learning menu

    :param idx: the move to select (usually for forgetting a move)
    """
    while GetLearnMoveState() == "MOVE_MENU":
        if GetMoveLearningCursorPos() < idx:
            up_presses = GetMoveLearningCursorPos() + 5 - idx
            down_presses = idx - GetMoveLearningCursorPos()
        else:
            up_presses = GetMoveLearningCursorPos() - idx
            down_presses = idx - GetMoveLearningCursorPos() + 5
        if down_presses > up_presses:
            PressButton(['Up'])
        else:
            PressButton(['Down'])
        WaitFrames(1)
        if GetMoveLearningCursorPos() == idx:
            PressButton(['A'])


def HandleMoveLearn(leveled_mon: int):
    match config['battle']['new_move']:
        case 'stop':
            console.print('New move trying to be learned, stopping bot...')
            input('Press enter to exit...')
            os._exit(0)
        case 'cancel':
            while GetGameState() != GameState.OVERWORLD:
                while GetGameState() == GameState.EVOLUTION:
                    if config['battle']['stop_evolution']:
                        PressButton(['B'])
                    else:
                        PressButton(['A'])
                if GetLearnMoveState() != "STOP_LEARNING":
                    PressButton(['B'])
                else:
                    PressButton(['A'])
        case 'learn_best':
            if GetGameState() == GameState.BATTLE:
                learning_mon = GetParty()[leveled_mon]
            else:
                learning_mon = GetLearningMon()
            learning_move = GetLearningMove()
            worst_move = CalculateNewMoveViability(learning_mon, learning_move)
            if worst_move == 4:
                while GetLearnMoveState() == "LEARN_YN":
                    PressButton(['B'])
                for i in range(60):
                    if GetLearnMoveState() != "STOP_LEARNING":
                        WaitFrames(1)
                    else:
                        break
                while GetLearnMoveState() == "STOP_LEARNING":
                    PressButton(['A'])
            else:
                while GetLearnMoveState() == "LEARN_YN":
                    PressButton(['A'])
                for i in range(60):
                    if not GetLearnMoveState() == "MOVE_MENU":
                        WaitFrames(1)
                    else:
                        break
                NavigateMoveLearnMenu(worst_move)
                while GetLearnMoveState() == "STOP_LEARNING":
                    PressButton(["B"])
            while GetBattleState() == BattleState.LEARNING and GetLearnMoveState() not in ["MOVE_MENU", "LEARN_YN", "STOP_LEARNING"]:
                PressButton(["B"])


def SwitchRequested() -> bool:
    """
    determines whether the prompt to use another pokemon is on the screen
    """
    match GetROM().game_title:
        case 'POKEMON RUBY' | 'POKEMON SAPP':
            return GetSymbolName(struct.unpack('<I', ReadSymbol('gBattleScriptCurrInstr', size=4))[0] - 51) == "BATTLESCRIPT_HANDLEFAINTEDMON"
        case _:
            return DecodeString(ReadSymbol('sText_UseNextPkmn')) in DecodeString(ReadSymbol('gDisplayedStringBattle'))


def GetBattleState() -> BattleState:
    """
    Determines the state of the battle so the battle loop can figure out the right choice to make.
    """
    match GetGameState():
        case GameState.OVERWORLD:
            return BattleState.OVERWORLD
        case GameState.EVOLUTION:
            match GetLearnMoveState():
                case "LEARN_YN" | "MOVEMENU" | "STOP_LEARNING":
                    return BattleState.LEARNING
                case _:
                    return BattleState.EVOLVING
        case GameState.PARTY_MENU:
            return BattleState.PARTY_MENU
        case _:
            match GetLearnMoveState():
                case "LEARN_YN" | "MOVEMENU" | "STOP_LEARNING":
                    return BattleState.LEARNING
                case _:
                    match GetBattleMenu():
                        case "ACTION":
                            return BattleState.ACTION_SELECTION
                        case "MOVE":
                            return BattleState.MOVE_SELECTION
                        case _:
                            if SwitchRequested():
                                return BattleState.SWITCH_POKEMON
                            else:
                                return BattleState.OTHER


def GetBattleMenu() -> str:
    """
    determines whether we're on the action selection menu, move selection menu, or neither
    """
    match GetROM().game_title:
        case 'POKEMON RUBY' | 'POKEMON SAPP':
            battle_funcs = ParseBattleController()['battler_controller_funcs']
            if 'SUB_802C098' in battle_funcs:
                return "ACTION"
            elif 'HANDLEACTION_CHOOSEMOVE' in battle_funcs:
                return "MOVE"
            else:
                return "NO"
        case 'POKEMON EMER' | 'POKEMON FIRE' | 'POKEMON LEAF':
            battle_funcs = ParseBattleController()['battler_controller_funcs']
            if 'HANDLEINPUTCHOOSEACTION' in battle_funcs:
                return "ACTION"
            elif 'HANDLEINPUTCHOOSEMOVE' in battle_funcs:
                return "MOVE"
            else:
                return "NO"



def ParseBattleController():
    active_battler = int.from_bytes(ReadSymbol('gActiveBattler', size=1), 'little')
    battler_controller_funcs = [GetSymbolName(struct.unpack('<I', ReadSymbol('gBattlerControllerFuncs')[i*4:i*4+4])[0] - 1) for i in range(4)]
    active_battler_func = battler_controller_funcs[active_battler]
    return {
        "active_battler": active_battler,
        "battler_controller_funcs": battler_controller_funcs,
        "active_battler_func": active_battler_func,
    }


def GetLearnMoveState() -> str:
    """
    Determines what step of the move_learning process we're on.
    """
    learn_move_yes_no = False
    stop_learn_move_yes_no = False
    match GetGameState():
        case GameState.BATTLE:
            learn_move_yes_no = GetSymbolName(struct.unpack('<I', ReadSymbol('gBattleScriptCurrInstr', size=4))[0]-17) == "BATTLESCRIPT_ASKTOLEARNMOVE"
            stop_learn_move_yes_no = GetSymbolName(struct.unpack('<I', ReadSymbol('gBattleScriptCurrInstr', size=4))[0]-32) == "BATTLESCRIPT_ASKTOLEARNMOVE"

        case GameState.EVOLUTION:

            match GetROM().game_title:
                case 'POKEMON RUBY' | 'POKEMON SAPP':
                    learn_move_yes_no = (
                            int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][0:2], 'little') == 21 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][16:18], 'little') == 4 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][18:20], 'little') == 5 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][20:22], 'little') == 9
                    )
                    stop_learn_move_yes_no = (
                            int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][0:2], 'little') == 21 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][16:18], 'little') == 4 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][18:20], 'little') == 10 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][20:22], 'little') == 0
                    )
                case 'POKEMON EMER':
                    learn_move_yes_no = (
                            int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][0:2], 'little') == 22 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][12:14], 'little') in [3, 4] and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][14:16], 'little') == 5 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][16:18], 'little') == 10
                    )
                    stop_learn_move_yes_no = (
                            int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][0:2], 'little') == 22 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][12:14], 'little') == [3, 4] and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][14:16], 'little') == 11 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][16:18], 'little') == 0
                    )

                case 'POKEMON FIRE' | 'POKEMON LEAF':
                    learn_move_yes_no = (
                            int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][0:2], 'little') == 24 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][12:14], 'little') == 4 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][14:16], 'little') == 5 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][16:18], 'little') == 10
                    )
                    stop_learn_move_yes_no = (
                            int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][0:2], 'little') == 24 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][12:14], 'little') == 4 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][14:16], 'little') == 11 and
                            int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][16:18], 'little') == 0
                    )
    match GetROM().game_title:
        case 'POKEMON RUBY' | 'POKEMON SAPP':
            move_menu_task = GetTask("SUB_809E260")
        case 'POKEMON EMER':
            move_menu_task = GetTask("TASK_HANDLEREPLACEMOVEINPUT")
        case 'POKEMON FIRE' | 'POKEMON LEAF':
            move_menu_task = GetTask("TASK_INPUTHANDLER_SELECTORFORGETMOVE")
        case _:
            move_menu_task = None
    move_menu = (move_menu_task != {} and move_menu_task['isActive'])


    if move_menu:
        return "MOVE_MENU"
    elif stop_learn_move_yes_no:
        return "STOP_LEARNING"
    elif learn_move_yes_no:
        return "LEARN_YN"
    else:
        return "NO"


def HandleEvolutionScene():
    """
    Stops evolution if configured to do so, otherwise mashes A
    """
    if config['battle']['stop_evolution']:
        PressButton(['B'])
    else:
        PressButton(['A'])


def GetCurrentBattler() -> list:
    """
    Determines which pokemon is battling
    """
    match GetROM().game_title:
        case 'POKEMON RUBY' | 'POKEMON SAPP':
            # this tells us which pokemon from our party are battling. 0 represents a pokemon in the party who isn't battling, and also the pokemon at index 0 :(
            battler_indices = [int.from_bytes(ReadSymbol('gBattlerPartyIndexes', size=12)[2*i:2*i+2], 'little') for i in range(len(GetParty()))]
            # this tells us how many pokemon are battling (2 for single battle, 4 for double) which allows us to get the pokemon info for the party members currently participating in the battle
            num_battlers = ReadSymbol('gBattlersCount', size=1)[0]
            # If we only have one party member, it's obviously the current battler so don't do the calcs for who's in battle
            if len(GetParty()) == 1:
                return GetParty()
            current_battlers = [GetParty()[battler_indices[i*2]] for i in range(num_battlers//2)]
            return current_battlers
        case 'POKEMON EMER' | 'POKEMON FIRE' | 'POKEMON LEAF':
            # this tells us which pokemon from our party are battling. 0 represents a pokemon in the party who isn't battling, and also the pokemon at index 0 :(
            battler_indices = [int.from_bytes(ReadSymbol('gBattlerPartyIndexes', size=12)[2*i:2*i+2], 'little') for i in range(len(GetParty()))]
            # this tells us how many pokemon are battling (2 for single battle, 4 for double) which allows us to get the pokemon info for the party members currently participating in the battle
            num_battlers = ReadSymbol('gBattlersCount', size=1)[0]
            # If we only have one party member, it's obviously the current battler so don't do the calcs for who's in battle
            if len(GetParty()) == 1:
                return GetParty()
            current_battlers = [GetParty()[battler_indices[i*2]] for i in range(num_battlers//2)]
            return current_battlers


def GetStrongestMove() -> int:
    """
    Function that determines the strongest move to use given the current battler and the current
    """
    current_battlers = GetCurrentBattler()
    if len(current_battlers) > 1:
        console.print("Double battle detected, feature not yet implemented.")
        os._exit(2)
    else:
        current_battler = current_battlers[0]
        move = FindEffectiveMove(current_battler, GetOpponent())
        if move['power'] == 0:
            console.print('Lead Pokémon has no effective moves to battle the foe!')
            return -1

        console.print('Best move against foe is {} (Effective power is {:.2f})'.format(
            move['name'],
            move['power']
        ))
        return move['index']


def GetMonToSwitch(active_mon: int) -> int:
    """
    Figures out which pokemon should be switched out for the current active pokemon.

    :param active_mon: the party index of the pokemon that is being replaced.
    :return: the index of the pokemon to switch with the active pokemon
    """
    party = GetParty()
    match config['battle']['switch_strategy']:
        case "first_available":
            for i in range(len(party)):
                if party[i] == active_mon:
                    continue
                # check to see that the party member has enough HP to be subbed out
                elif party[i]['stats']['hp'] / party[i]['stats']['maxHP'] > .2:
                    console.print('Pokémon {} has more than 20% hp!'.format(party[i]['name']))
                    for move in party[i]['moves']:
                        if (
                                move['power'] > 0 and
                                move['remaining_pp'] > 0 and
                                move['name'] not in config['battle']['banned_moves']
                                and move['kind'] in ['Physical', 'Special']):
                            console.print('Pokémon {} has usable moves!'.format(party[i]['name']))
                            return i
            console.print("Can't find suitable replacement battler. Turning off auto battling and pickup.")
            config['battle']['battle'] = False
            config['battle']['pickup'] = False


def ShouldRotateLead() -> bool:
    """
    Determines whether the battle engine should swap out the lead pokemon.
    """
    battler = GetCurrentBattler()[0]
    battler_health_percentage = battler['stats']['hp'] / battler['stats']['maxHP']
    return battler_health_percentage < .2


def DetermineAction() -> tuple:
    """
    Determines which action to select from the action menu

    :return: a tuple containing 1. the action to take, 2. the move to use if so desired, 3. the index of the pokemon to
    switch to if so desired.
    """
    if not config['battle']['battle']:
        return "RUN", -1, -1
    elif config['battle']['replace_lead_battler'] and ShouldRotateLead():
        mon_to_switch = GetMonToSwitch(GetCurrentBattler()[0])
        return "SWITCH", -1, mon_to_switch
    else:
        match config['battle']['battle_method']:
            case "strongest":
                move = GetStrongestMove()
                if move == -1:
                    if config['battle']['replace_lead_battler']:
                        mon_to_switch = GetMonToSwitch(GetCurrentBattler()[0])
                        return "SWITCH", -1, mon_to_switch
                    action = "RUN"
                else:
                    action = "FIGHT"
                return action, move, -1
            case _:
                console.print("Not yet implemented")
                return "RUN", -1, -1


def SendOutPokemon(idx):
    """
    Navigates from the party menu to the index of the desired pokemon
    """
    # options are the entire length of the party plus a cancel option
    cursor_positions = len(GetParty()) + 1

    # navigate to the desired index as quickly as possible
    party_menu_index = GetPartyMenuCursorPos()['slot_id']
    if party_menu_index >= cursor_positions:
        party_menu_index = cursor_positions - 1
    while party_menu_index != idx:
        if party_menu_index > idx:
            up_presses = party_menu_index - idx
            down_presses = idx + cursor_positions - party_menu_index
        else:
            up_presses = party_menu_index + cursor_positions - idx
            down_presses = idx - party_menu_index
        if down_presses > up_presses:
            PressButton(['Up'])
        else:
            PressButton(['Down'])
        WaitFrames(1)
        party_menu_index = GetPartyMenuCursorPos()['slot_id']
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1
    match GetROM().game_title:
        case 'POKEMON EMER' | 'POKEMON FIRE' | 'POKEMON LEAF':
            for i in range(60):
                if "TASK_HANDLESELECTIONMENUINPUT" not in [task['func'] for task in ParseTasks()]:
                    PressButton(['A'])
                    WaitFrames(1)
                else:
                    break
            while "TASK_HANDLESELECTIONMENUINPUT" in [task['func'] for task in ParseTasks()]:
                NavigateMenu("SHIFT")
        case _:
            for i in range(60):
                if "TASK_HANDLEPOPUPMENUINPUT" not in [task['func'] for task in ParseTasks()]:
                    PressButton(['A'])
                    WaitFrames(1)
            while "TASK_HANDLEPOPUPMENUINPUT" in [task['func'] for task in ParseTasks()]:
                PressButton(['A'])
                WaitFrames(1)


def SwitchOutPokemon(idx):
    """
    Navigates from the party menu to the index of the desired pokemon
    """
    cursor_positions = len(GetParty()) + 1

    while not PartyMenuIsOpen():
        PressButton(['A'])
        
    party_menu_index = GetPartyMenuCursorPos()['slot_id']
    if party_menu_index >= cursor_positions:
        party_menu_index = cursor_positions - 1

    while party_menu_index != idx:

        if party_menu_index > idx:
            up_presses = party_menu_index - idx
            down_presses = idx + cursor_positions - party_menu_index
        else:
            up_presses = party_menu_index + cursor_positions - idx
            down_presses = idx - party_menu_index

        if down_presses > up_presses:
            PressButton(['Up'])
        else:
            PressButton(['Down'])
        WaitFrames(1)
        party_menu_index = GetPartyMenuCursorPos()['slot_id']
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1

    if GetROM().game_title in ['POKEMON EMER', 'POKEMON FIRE', 'POKEMON LEAF']:
        while not (GetTask("TASK_HANDLESELECTIONMENUINPUT") != {} and GetTask("TASK_HANDLESELECTIONMENUINPUT")['isActive']):
            PressButton(['A'])
        while GetTask("TASK_HANDLESELECTIONMENUINPUT") != {} and GetTask("TASK_HANDLESELECTIONMENUINPUT")['isActive']:
            NavigateMenu("SWITCH")
        while GetPartyMenuCursorPos()['action'] != 8:
            PressButton(['A'])
        while GetPartyMenuCursorPos()['action'] == 8:
            if GetPartyMenuCursorPos()['slot_id_2'] == 7:
                PressButton(['Down'])
            elif GetPartyMenuCursorPos()['slot_id_2'] != 0:
                PressButton(['Left'])
            else:
                PressButton(['A'])
        while GetGameState() == GameState.PARTY_MENU:
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


def RotatePokemon():
    new_lead = GetMonToSwitch(0)
    if new_lead is not None:
        NavigateStartMenu("POKEMON")
        for i in range(30):
            if GetGameState() != GameState.PARTY_MENU:
                PressButton(['A'])
        SwitchOutPokemon(new_lead)


def CheckLeadCanBattle():
    """
    Determines whether the lead pokemon is fit to fight
    """
    lead = GetParty()[0]
    lead_has_moves = False
    for move in lead['moves']:
        if (
            move['power'] > 0 and
            move['name'] not in config['battle']['banned_moves'] and
            move['remaining_pp'] > 0
        ):
            lead_has_moves = True
            break
    lead_has_hp = lead['stats']['hp'] > .2 * lead['stats']['maxHP']
    return lead_has_hp and lead_has_moves


def ExecuteAction(decision: tuple):
    """
    Given a decision made by the battle engine, executes the desired action.

    :param decision: The output of DetermineAction, containing an action, move index, and pokemon index.
    """
    action, move, pokemon = decision
    match action:
        case "RUN":
            FleeBattle()
            return
        case "FIGHT":
            if 0 > move or move > 3:
                console.print("Invalid move selection. Stopping...")
                os._exit(move)
            move_executed = False
            while not move_executed:
                match GetBattleState():
                    case BattleState.ACTION_SELECTION:
                        SelectBattleOption(0)
                    case BattleState.MOVE_SELECTION:
                        SelectBattleOption(move)
                        if GetBattleState() != BattleState.MOVE_SELECTION:
                            move_executed = True
                    case _:
                        PressButton(['B'])
        case "BAG":
            console.print("Bag not yet implemented. Stopping...")
            os._exit(3)
        case "SWITCH":
            if pokemon is None:
                ExecuteAction(("RUN", -1, -1))
            elif 0 > pokemon or pokemon > 6 :
                console.print("Invalid Pokemon selection. Stopping...")
                os._exit(pokemon)
            else:
                while not GetBattleState() == BattleState.PARTY_MENU:
                    SelectBattleOption(2)
                SendOutPokemon(pokemon)
            return


def HandleBattlerFaint():
    """
    function that handles lead battler fainting
    """
    console.print('Lead Pokémon fainted!')
    match config['battle']['faint_action']:
        case 'stop':
            console.print("Stopping...")
            os._exit(-1)
        case 'flee':
            while GetBattleState() not in [BattleState.OVERWORLD, BattleState.PARTY_MENU]:
                PressButton(['B'])
            if GetBattleState() == BattleState.PARTY_MENU:
                console.print("Couldn't flee. Stopping...")
                os._exit(-2)
            else:
                while not GetGameState() == GameState.OVERWORLD:
                    PressButton(['B'])
                return False
        case 'rotate':
            party = GetParty()
            if sum([party[key]['stats']['hp'] for key in party.keys()]) == 0:
                console.print('All Pokémon have fainted.')
                os._exit(0)
            while GetBattleState() != BattleState.PARTY_MENU:
                PressButton(['A'])
            new_lead = GetMonToSwitch(GetCurrentBattler()[0])
            if new_lead is None:
                console.print("No viable pokemon to switch in!")
                faint_action_default = str(config['battle']['faint_action'])
                config['battle']['faint_action'] = "flee"
                HandleBattlerFaint()
                config['battle']['faint_action'] = faint_action_default
                return False
            SendOutPokemon(new_lead)
            while GetBattleState() in (BattleState.SWITCH_POKEMON, BattleState.PARTY_MENU):
                PressButton(['A'])
        case _:
            console.print("Invalid faint_action option. Stopping.")
            os._exit(-3)


def CheckForLevelUp(old_party: dict, new_party: dict, leveled_mon) -> int:
    """
    Compares the previous party state to the most recently gathered party state, and returns the index of the first
    pokemon whose level is higher in the new party state.

    :param old_party: The previous party state
    :param new_party: The most recent party state
    :param leveled_mon: The index of the pokemon that was most recently leveled before this call.
    :return: The first index where a pokemon's level is higher in the new party than the old one.
    """
    if old_party.keys() != new_party.keys():
        console.print("Party length has changed. Assuming a pokemon was just caught.")
    for i in range(len(old_party)):
        if old_party[i]['level'] < new_party[i]['level']:
            return i
    return leveled_mon


def BattleOpponent() -> bool:
    """
    Function to battle wild Pokémon. This will only battle with the lead Pokémon of the party, and will run if it dies
    or runs out of PP.

    :return: Boolean value of whether the battle was won.
    """

    battle_ended = False
    foe_fainted = GetOpponent()['stats']['hp'] == 0
    prev_battle_state = GetBattleState()
    previous_party = GetParty()
    most_recent_leveled_mon_index = -1
    while not battle_ended:
        battle_state = GetBattleState()
        if battle_state != prev_battle_state:
            # print(f"Battle state: {BattleState(GetBattleState()).name}")
            prev_battle_state = battle_state

        # check for level ups
        party = GetParty()
        if previous_party != party:
            most_recent_leveled_mon_index = CheckForLevelUp(previous_party, party, most_recent_leveled_mon_index)
            previous_party = party

        foe_fainted = GetOpponent()['stats']['hp'] == 0

        match battle_state:
            case BattleState.OVERWORLD:
                battle_ended = True
            case BattleState.EVOLVING:
                HandleEvolutionScene()
            case BattleState.LEARNING:
                HandleMoveLearn(most_recent_leveled_mon_index)
            case BattleState.ACTION_SELECTION:
                ExecuteAction(DetermineAction())
            case BattleState.SWITCH_POKEMON:
                HandleBattlerFaint()
            case _:
                PressButton(['B'])

    if foe_fainted:
        return True
    return False
