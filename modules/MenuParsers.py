import struct

from modules.Config import ForceManualMode
from modules.Console import console
from modules.Gui import GetROM, GetEmulator
from modules.Memory import GetSymbolName, ReadSymbol, GetTaskFunc, ParseTasks, GetTask, unpack_uint32
from modules.Enums import TaskFunc, StartMenuOptionHoenn, StartMenuOptionKanto
from modules.Pokemon import GetParty, moves_list, ParsePokemon


def get_party_menu_cursor_pos() -> dict:
    """
    Function to parse the party menu data and return usable information
    """
    party_menu = {
        "slot_id": -1,
        "slot_id_2": -1,
    }

    if GetROM().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        pMenu = ReadSymbol("gPartyMenu")
        party_menu["main_cb"] = GetSymbolName(unpack_uint32(pMenu[0:4]) - 1)
        party_menu["taskfunc"] = GetSymbolName(unpack_uint32(pMenu[4:8]) - 1)
        party_menu["menu_type_and_layout"] = struct.unpack("<B", pMenu[8:9])[0]
        party_menu["slot_id"] = struct.unpack("<b", pMenu[9:10])[0]
        party_menu["slot_id_2"] = struct.unpack("<b", pMenu[10:11])[0]
        party_menu["action"] = struct.unpack("<B", pMenu[11:12])[0]
        party_menu["bagItem"] = struct.unpack("<H", pMenu[12:14])[0]
        party_menu["data1"] = struct.unpack("<h", pMenu[14:16])[0]
        party_menu["learn_move_state"] = struct.unpack("<h", pMenu[16:18])[0]
    else:
        party_menu["slot_id"] = int.from_bytes(
            GetEmulator().ReadBytes(0x0202002F + len(GetParty()) * 136 + 3, length=1), "little"
        )
        party_menu["slot_id_2"] = party_menu["slot_id"]

    if party_menu["slot_id"] == -1:
        console.print("Error detecting cursor position. Switching to manual mode...")
        ForceManualMode()
    return party_menu


def parse_menu() -> dict:
    """
    Function to parse the currently displayed menu and return usable information.
    """
    if GetROM().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        menu = ReadSymbol("sMenu")
        cursor_pos = struct.unpack("<b", menu[2:3])[0]
        min_cursor_pos = struct.unpack("<b", menu[3:4])[0]
        max_cursor_pos = struct.unpack("<b", menu[4:5])[0]
    else:
        cursor_pos = int.from_bytes(ReadSymbol("sPokeMenuCursorPos", 0, 1), "little")
        min_cursor_pos = 0
        max_cursor_pos = int.from_bytes(ReadSymbol("sPokeMenuOptionsNo"), "little") - 1

    return {
        "minCursorPos": min_cursor_pos,
        "maxCursorPos": max_cursor_pos,
        "cursorPos": cursor_pos,
    }


def parse_party_menu() -> dict:
    """
    Function to parse info about the party menu
    """
    if GetROM().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        pmi_pointer = ReadSymbol("sPartyMenuInternal")
        addr = int(struct.unpack("<I", pmi_pointer)[0]) - 1
        party_menu_internal = GetEmulator().ReadBytes(addr, length=30)
        party_menu_info = {
            "actions": [struct.unpack("<B", party_menu_internal[16 + i : 17 + i])[0] for i in range(8)],
            "numActions": struct.unpack("<B", party_menu_internal[24:25])[0],
        }
    else:
        actions = []
        num_actions = int.from_bytes(ReadSymbol("sPokeMenuOptionsNo"), "little")

        for i in range(num_actions):
            actions.append(ReadSymbol("sPokeMenuOptionsOrder")[i])

        party_menu_info = {"actions": actions, "numActions": num_actions}

    return party_menu_info


def get_battle_cursor(cursor_type: str) -> int:
    return unpack_uint32(ReadSymbol(cursor_type, 0, 4))


def get_learning_mon() -> dict:
    """
    If the learning state is entered through evolution, returns the Pokémon that is learning the move.

    :return: The Pokémon trying to learn a move after evolution.
    """
    index = 0
    if GetROM().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        index = int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")["data"][20:22], "little")
    else:
        for i, member in GetParty().items():
            if member == ParsePokemon(
                GetEmulator().ReadBytes(
                    int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")["data"][2:4], "little")
                    | (int.from_bytes(GetTask("TASK_EVOLUTIONSCENE")["data"][4:6], "little") << 0x10),
                    length=100,
                )
            ):
                index = i
    return GetParty()[index]


def get_learning_move() -> dict:
    """
    helper function that returns the move trying to be learned
    """
    return moves_list[int.from_bytes(ReadSymbol("gMoveToLearn", size=2), "little")]


def get_learning_move_cursor_pos() -> int:
    """
    helper function that returns the position of the move learning cursor
    """
    match GetROM().game_title:
        case "POKEMON EMER":
            return int.from_bytes(
                GetEmulator().ReadBytes(struct.unpack("<I", ReadSymbol("sMonSummaryScreen"))[0] + 0x40C6, length=1),
                "little",
            )
        case "POKEMON FIRE" | "POKEMON LEAF":
            return int.from_bytes(ReadSymbol("sMoveSelectionCursorPos"), "little")
        case "POKEMON RUBY" | "POKEMON SAPP":
            return int.from_bytes(ReadSymbol("gSharedMem", offset=0x18079, size=1), "little")


def parse_start_menu() -> dict:
    """
    Helper function that decodes the state of the start menu.
    """
    tasks = ParseTasks()
    open = False

    if GetROM().game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]:
        start_menu_options_symbol = "sCurrentStartMenuActions"
        num_actions_symbol = "sNumStartMenuActions"
        start_menu_enum = StartMenuOptionHoenn
    else:
        start_menu_options_symbol = "sStartMenuOrder"
        num_actions_symbol = "sNumStartMenuItems"
        start_menu_enum = StartMenuOptionKanto

    item_indices = [i for i in ReadSymbol(start_menu_options_symbol)]
    actions = []

    for i in range(int.from_bytes(ReadSymbol(num_actions_symbol), "little")):
        actions.append(start_menu_enum(item_indices[i]).name)

    for task in tasks:
        if GetTaskFunc(task["func"]) == TaskFunc.START_MENU and task["isActive"]:
            open = True
            break

    return {
        "open": open,
        "cursor_pos": struct.unpack("<B", ReadSymbol("sStartMenuCursorPos"))[0],
        "actions": actions,
    }


def get_battle_menu() -> str:
    """
    determines whether we're on the action selection menu, move selection menu, or neither
    """
    match GetROM().game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            battle_funcs = get_battle_controller()["battler_controller_funcs"]
            if "SUB_802C098" in battle_funcs:
                return "ACTION"
            elif "HANDLEACTION_CHOOSEMOVE" in battle_funcs:
                return "MOVE"
            else:
                return "NO"
        case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
            battle_funcs = get_battle_controller()["battler_controller_funcs"]
            if "HANDLEINPUTCHOOSEACTION" in battle_funcs:
                return "ACTION"
            elif "HANDLEINPUTCHOOSEMOVE" in battle_funcs:
                return "MOVE"
            else:
                return "NO"


def get_battle_controller():
    active_battler = int.from_bytes(ReadSymbol("gActiveBattler", size=1), "little")
    battler_controller_funcs = [
        GetSymbolName(struct.unpack("<I", ReadSymbol("gBattlerControllerFuncs")[i * 4 : i * 4 + 4])[0] - 1)
        for i in range(4)
    ]
    active_battler_func = battler_controller_funcs[active_battler]
    return {
        "active_battler": active_battler,
        "battler_controller_funcs": battler_controller_funcs,
        "active_battler_func": active_battler_func,
    }


def switch_requested() -> bool:
    """
    Determines whether the prompt to use another Pokémon is on the screen
    """
    match GetROM().game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            return (
                GetSymbolName(struct.unpack("<I", ReadSymbol("gBattleScriptCurrInstr", size=4))[0] - 51)
                == "BATTLESCRIPT_HANDLEFAINTEDMON"
            )
        case _:
            return ReadSymbol("sText_UseNextPkmn") in ReadSymbol("gDisplayedStringBattle")
