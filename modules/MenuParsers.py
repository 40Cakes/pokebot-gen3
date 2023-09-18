import os
import struct

from modules.Console import console
from modules.Memory import mGBA, ReadMemory, GetSymbolName, ReadSymbol, GetTaskFunc, ParseTasks
from modules.Enums import TaskFunc, StartMenuOptionHoenn, StartMenuOptionKanto
from modules.Pokemon import GetParty, moves_list


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


def ParseMain() -> dict:
    """
    function to parse the data in gMain and return usable info
    """
    main = ReadSymbol('gMain')

    # parse the bits and bobs in the main struct
    callback1 = ParseFunc(main[0:4])
    callback2 = ParseFunc(main[4:8])
    saved_callback = ParseFunc(main[8:12])
    vblank_callback = ParseFunc(main[12:16])
    hblank_callback = ParseFunc(main[16:20])
    vcount_callback = ParseFunc(main[20:24])
    serial_callback = ParseFunc(main[24:28])
    held_keys_raw = struct.unpack('<H', main[40:42])[0]
    new_keys_raw = struct.unpack('<H', main[42:44])[0]
    held_keys = struct.unpack('<H', main[44:46])[0]
    new_keys = struct.unpack('<H', main[46:48])[0]
    new_and_repeated_keys = struct.unpack('<H', main[48:50])[0]
    key_repeat_counter = struct.unpack('<H', main[50:52])[0]
    watched_keys_pressed = struct.unpack('<H', main[52:54])[0]
    watched_keys_mask = struct.unpack('<H', main[54:56])[0]
    obj_count = struct.unpack('<B', main[56:57])[0]

    main_dict = {
        'callback_1': callback1,
        'callback_2': callback2,
        'saved_callback': saved_callback,
        'vblank_callback': vblank_callback,
        'hblank_callback': hblank_callback,
        'vcount_callback': vcount_callback,
        'serial_callback': serial_callback,
        'held_keys_raw': held_keys_raw,
        'new_keys_raw': new_keys_raw,
        'held_keys': held_keys,
        'new_keys': new_keys,
        'new_and_repeated_keys': new_and_repeated_keys,
        'key_repeat_counter': key_repeat_counter,
        'watched_keys_pressed': watched_keys_pressed,
        'watched_keys_mask': watched_keys_mask,
        'obj_count': obj_count,
    }
    return main_dict


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
    idx = 0
    match mGBA.game:
        case 'Pokémon FireRed' | 'Pokémon LeafGreen':
            if ParseMain()['callback_1'] == 'BATTLEMAINCB1':
                idx = int.from_bytes(ReadMemory(
                    struct.unpack('<I', ReadSymbol('gBattleStruct'))[0], offset=0x10, size=1), 'little')
            else:
                console.print('Not yet implemented...')
                os._exit(1)
        case 'Pokémon Emerald':
            idx = int.from_bytes(ReadMemory(
                struct.unpack('<I', ReadSymbol('sMonSummaryScreen'))[0], offset=0x40BE, size=1), 'little')
        case 'Pokémon Ruby' | 'Pokémon Sapphire':
            idx = int.from_bytes(ReadSymbol('gSharedMem', offset=0x18009, size=1), 'little')
        case _:
            console.print('Not yet implemented...')
            os._exit(1)
    return GetParty()[idx]


def GetLearningMove() -> dict:
    """
    helper function that returns the move trying to be learned
    """
    match mGBA.game:
        case 'Pokémon Emerald':
            return moves_list[struct.unpack('<H', ReadMemory(
                struct.unpack('<I', ReadSymbol('sMonSummaryScreen'))[0], offset=0x40C4, size=2))[0]]
        case 'Pokémon FireRed' | 'Pokémon LeafGreen':
            return moves_list[struct.unpack('<H', ReadSymbol('gMoveToLearn'))[0]]
        case 'Pokémon Ruby' | 'Pokémon Sapphire':
            return moves_list[int.from_bytes(ReadSymbol('gMoveToLearn', size=1), 'little')]


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
