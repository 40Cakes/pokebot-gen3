import os
import struct

from modules.Console import console
from modules.Memory import mGBA, ReadMemory, GetSymbolName, ReadSymbol, GetTaskFunc, ParseTasks, GetGameState, GetTask
from modules.Enums import TaskFunc, StartMenuOptionHoenn, StartMenuOptionKanto, GameState
from modules.Pokemon import GetParty, moves_list, ParsePokemon


def GetPartyMenuCursorPos() -> dict:
    """
    Function to parse the party menu data and return usable information
    """
    party_menu = {
        'slot_id': -1,
        'slot_id_2': -1,
    }
    match mGBA.game:
        case 'Pokémon Ruby' | 'Pokémon Sapphire':
            party_menu['slot_id'] = int.from_bytes(ReadMemory(0x0202002F, offset=len(GetParty()) * 136 + 3, size=1), 'little')
            party_menu['slot_id_2'] = party_menu['slot_id']
        case 'Pokémon Emerald' | 'Pokémon FireRed' | 'Pokémon LeafGreen':
            pMenu = ReadSymbol('gPartyMenu')
            party_menu['main_cb'] = GetSymbolName(int(struct.unpack('<I', pMenu[0:4])[0]) - 1)
            party_menu['taskfunc'] = GetSymbolName(int(struct.unpack('<I', pMenu[4:8])[0]) - 1)
            party_menu['menu_type_and_layout'] = struct.unpack('<B', pMenu[8:9])[0]
            party_menu['slot_id'] = struct.unpack('<b', pMenu[9:10])[0]
            party_menu['slot_id_2'] = struct.unpack('<b', pMenu[10:11])[0]
            party_menu['action'] = struct.unpack('<B', pMenu[11:12])[0]
            party_menu['bagItem'] = struct.unpack('<H', pMenu[12:14])[0]
            party_menu['data1'] = struct.unpack('<h', pMenu[14:16])[0]
            party_menu['learn_move_state'] = struct.unpack('<h', pMenu[16:18])[0]
    if party_menu['slot_id'] == -1:
        console.print('Error detecting cursor position.')
        os._exit(1)
    return party_menu


def ParseFunc(data) -> str:
    """
    helper function for parsing function pointers
    """
    addr = int(struct.unpack('<I', data)[0]) - 1
    if addr != '-0x1':
        return GetSymbolName(addr)
    return '_'


def ParseMenu() -> dict:
    """
    Function to parse the currently displayed menu and return usable information.
    """
    match mGBA.game:
        case 'Pokémon Emerald' | 'Pokémon FireRed' | 'Pokémon LeafGreen':
            menu = ReadSymbol('sMenu')
            cursor_pos = struct.unpack('<b', menu[2:3])[0]
            min_cursor_pos = struct.unpack('<b', menu[3:4])[0]
            max_cursor_pos = struct.unpack('<b', menu[4:5])[0]
        case 'Pokémon Ruby' | 'Pokémon Sapphire':
            cursor_pos = int.from_bytes(ReadSymbol('sPokeMenuCursorPos', 0, 1), 'little')
            min_cursor_pos = 0
            max_cursor_pos = int.from_bytes(ReadSymbol('sPokeMenuOptionsNo'), 'little') - 1
        case _:
            print('Not implemented yet.')
            os._exit(1)
    return {
        'minCursorPos': min_cursor_pos,
        'maxCursorPos': max_cursor_pos,
        'cursorPos': cursor_pos,
    }


def ParsePartyMenuInternal() -> dict:
    """
    Function to parse info about the party menu
    """
    party_menu_info = {}
    match mGBA.game:
        case 'Pokémon Emerald' | 'Pokémon FireRed' | 'Pokémon LeafGreen':
            pmi_pointer = ReadSymbol('sPartyMenuInternal')
            addr = int(struct.unpack('<I', pmi_pointer)[0]) - 1
            party_menu_internal = ReadMemory(addr, 0, int(30))
            party_menu_info = {
                "actions": [struct.unpack('<B', party_menu_internal[16 + i:17 + i])[0] for i in range(8)],
                "numActions": struct.unpack('<B', party_menu_internal[24:25])[0],
            }
        case "Pokémon Ruby" | "Pokémon Sapphire":
            actions = []
            num_actions = int.from_bytes(ReadSymbol('sPokeMenuOptionsNo'), 'little')
            for i in range(num_actions):
                actions.append(ReadSymbol('sPokeMenuOptionsOrder')[i])
            party_menu_info = {
                "actions": actions,
                "numActions": num_actions
            }
        case _:
            print('Not implemented yet.')
            os._exit(1)
    return party_menu_info


def ParseBattleCursor(cursor_type: str) -> int:
    return int.from_bytes(ReadSymbol(cursor_type, 0, 4), 'little')


def GetLearningMon() -> dict:
    """
    If the learning state is entered through evolution, returns the pokemon that is learning the move.

    :return: The pokemon trying to learn a move after evolution.
    """
    idx = 0
    match mGBA.game:
        case 'Pokémon Emerald' | 'Pokémon FireRed' | 'Pokémon LeafGreen':
            idx = int.from_bytes(GetTask('TASK_EVOLUTIONSCENE')['data'][20:22], 'little')
        case 'Pokémon Ruby' | 'Pokémon Sapphire':
            for i, member in GetParty().items():
                if member == ParsePokemon(ReadMemory(
                        int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][2:4], 'little') | (
                                int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")['data'][4:6], 'little') << 0x10),
                        size=100)):
                    idx = i
        case _:
            console.print('Not yet implemented...')
            os._exit(1)
    return GetParty()[idx]


def GetLearningMove() -> dict:
    """
    helper function that returns the move trying to be learned
    """
    return moves_list[int.from_bytes(ReadSymbol('gMoveToLearn', size=2), 'little')]


def GetMoveLearningCursorPos() -> int:
    """
    helper function that returns the position of the move learning cursor
    """
    match mGBA.game:
        case 'Pokémon Emerald':
            return int.from_bytes(ReadMemory(
                struct.unpack('<I', ReadSymbol('sMonSummaryScreen'))[0], offset=0x40C6, size=1), 'little')
        case 'Pokémon FireRed' | 'Pokémon LeafGreen':
            return int.from_bytes(ReadSymbol('sMoveSelectionCursorPos'), 'little')
        case 'Pokémon Ruby' | 'Pokémon Sapphire':
            return int.from_bytes(ReadSymbol('gSharedMem', offset=0x18079, size=1), 'little')


def ParseStartMenu() -> dict:
    """
    Helper function that decodes the state of the start menu.
    """
    tasks = ParseTasks()
    open = False
    match mGBA.game:
        case 'Pokémon Ruby' | 'Pokémon Sapphire' | 'Pokémon Emerald':
            start_menu_options_symbol = 'sCurrentStartMenuActions'
            num_actions_symbol = 'sNumStartMenuActions'
            start_menu_enum = StartMenuOptionHoenn
        case _:
            start_menu_options_symbol = 'sStartMenuOrder'
            num_actions_symbol = 'sNumStartMenuItems'
            start_menu_enum = StartMenuOptionKanto
    item_indices = [i for i in ReadSymbol(start_menu_options_symbol)]
    actions = []
    for i in range(int.from_bytes(ReadSymbol(num_actions_symbol), 'little')):
        actions.append(start_menu_enum(item_indices[i]).name)
    for task in tasks:
        if GetTaskFunc(task['func']) == TaskFunc.START_MENU and task['isActive']:
            open = True
            break
    return {
        "open": open,
        "cursor_pos": struct.unpack('<B', ReadSymbol('sStartMenuCursorPos'))[0],
        "actions": actions,
    }
