import struct
from enum import IntEnum

from modules.context import context
from modules.memory import get_symbol_name, read_symbol, unpack_uint32
from modules.pokemon import get_party, parse_pokemon, Pokemon, get_move_by_index, Move
from modules.tasks import get_task, task_is_active


class CursorOptionEFRLG(IntEnum):
    SUMMARY = 0
    SWITCH = 1
    CANCEL_1 = 2
    ITEM = 3
    GIVE_ITEM = 4
    TAKE_ITEM = 5
    MAIL = 6
    TAKE_MAIL = 7
    READ = 8
    CANCEL_2 = 9
    SHIFT = 10
    SEND_OUT = 11
    ENTER = 12
    NO_ENTRY = 13
    STORE = 14
    REGISTER = 15
    TRADE_1 = 16
    TRADE_2 = 17
    TOSS = 18
    CUT = 19
    FLASH = 20
    ROCK_SMASH = 21
    STRENGTH = 22
    SURF = 23
    FLY = 24
    DIVE = 25
    WATERFALL = 26
    TELEPORT = 27
    DIG = 28
    SECRET_POWER = 29
    MILK_DRINK = 30
    SOFTBOILED = 31
    SWEET_SCENT = 32


class CursorOptionRS(IntEnum):
    SUMMARY = 0
    SWITCH = 1
    ITEM = 2
    CANCEL_1 = 3
    GIVE_ITEM = 4
    TAKE_ITEM = 5
    TAKE_MAIL = 6
    MAIL = 7
    READ = 8
    CANCEL_2 = 9
    CUT = 10
    FLASH = 11
    ROCK_SMASH = 12
    STRENGTH = 13
    SURF = 14
    FLY = 15
    DIVE = 16
    WATERFALL = 17
    TELEPORT = 18
    DIG = 19
    SECRET_POWER = 20
    MILK_DRINK = 21
    SOFTBOILED = 22
    SWEET_SCENT = 23


class StartMenuOptionHoenn(IntEnum):
    POKEDEX = 0
    POKEMON = 1
    BAG = 2
    POKENAV = 3
    PLAYER = 4
    SAVE = 5
    OPTION = 6
    EXIT = 7
    RETIRE = 8
    PLAYER2 = 9


class StartMenuOptionKanto(IntEnum):
    POKEDEX = 0
    POKEMON = 1
    BAG = 2
    PLAYER = 3
    SAVE = 4
    OPTION = 5
    EXIT = 6
    RETIRE = 7
    PLAYER2 = 8
    MAX_STARTMENU_ITEMS = 8


def get_party_menu_cursor_pos(party_length: int) -> dict:
    """
    Function to parse the party menu data and return usable information

    :param party_length: the number of Pokémon in the party
    """
    party_menu = {
        "slot_id": -1,
        "slot_id_2": -1,
    }

    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        p_menu = read_symbol("gPartyMenu")
        party_menu["main_cb"] = get_symbol_name(unpack_uint32(p_menu[0:4]) - 1)
        party_menu["taskfunc"] = get_symbol_name(unpack_uint32(p_menu[4:8]) - 1)
        party_menu["menu_type_and_layout"] = struct.unpack("<B", p_menu[8:9])[0]
        party_menu["slot_id"] = struct.unpack("<b", p_menu[9:10])[0]
        party_menu["slot_id_2"] = struct.unpack("<b", p_menu[10:11])[0]
        party_menu["action"] = struct.unpack("<B", p_menu[11:12])[0]
        party_menu["bagItem"] = struct.unpack("<H", p_menu[12:14])[0]
        party_menu["data1"] = struct.unpack("<h", p_menu[14:16])[0]
        party_menu["learn_move_state"] = struct.unpack("<h", p_menu[16:18])[0]
    else:
        party_menu["slot_id"] = int.from_bytes(
            context.emulator.read_bytes(0x0202002F + party_length * 136 + 3, length=1), "little"
        )
        party_menu["slot_id_2"] = party_menu["slot_id"]

    if party_menu["slot_id"] == -1:
        context.message = "Error detecting cursor position, switching to manual mode..."
        context.set_manual_mode()
    return party_menu


def parse_menu() -> dict:
    """
    Function to parse the currently displayed menu and return usable information.
    """
    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        menu = read_symbol("sMenu")
        cursor_pos = struct.unpack("<b", menu[2:3])[0]
        min_cursor_pos = struct.unpack("<b", menu[3:4])[0]
        max_cursor_pos = struct.unpack("<b", menu[4:5])[0]
    else:
        cursor_pos = int.from_bytes(read_symbol("sPokeMenuCursorPos", 0, 1), "little")
        min_cursor_pos = 0
        max_cursor_pos = int.from_bytes(read_symbol("sPokeMenuOptionsNo"), "little") - 1

    return {
        "minCursorPos": min_cursor_pos,
        "maxCursorPos": max_cursor_pos,
        "cursorPos": cursor_pos,
    }


def parse_party_menu() -> dict:
    """
    Function to parse info about the party menu
    """
    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        pmi_pointer = read_symbol("sPartyMenuInternal")
        addr = int(struct.unpack("<I", pmi_pointer)[0]) - 1
        party_menu_internal = context.emulator.read_bytes(addr, length=30)
        party_menu_info = {
            "actions": [struct.unpack("<B", party_menu_internal[16 + i : 17 + i])[0] for i in range(8)],
            "numActions": struct.unpack("<B", party_menu_internal[24:25])[0],
        }
    else:
        actions = []
        num_actions = int.from_bytes(read_symbol("sPokeMenuOptionsNo"), "little")

        for i in range(num_actions):
            actions.append(read_symbol("sPokeMenuOptionsOrder")[i])

        party_menu_info = {"actions": actions, "numActions": num_actions}

    return party_menu_info


def get_battle_cursor(cursor_type: str) -> int:
    return unpack_uint32(read_symbol(cursor_type, 0, 4))


def get_learning_mon() -> Pokemon:
    """
    If the learning state is entered through evolution, returns the Pokémon that is learning the move.

    :return: The Pokémon trying to learn a move after evolution.
    """
    index = 0
    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        index = int.from_bytes(get_task("TASK_EVOLUTIONSCENE").data[20:22], "little")
    else:
        for i, member in enumerate(get_party()):
            if member == parse_pokemon(
                context.emulator.read_bytes(
                    int.from_bytes(get_task("TASK_EVOLUTIONSCENE").data[2:4], "little")
                    | (int.from_bytes(get_task("TASK_EVOLUTIONSCENE").data[4:6], "little") << 0x10),
                    length=100,
                )
            ):
                index = i
    return get_party()[index]


def get_learning_move() -> Move:
    """
    helper function that returns the move trying to be learned
    """
    return get_move_by_index(int.from_bytes(read_symbol("gMoveToLearn", size=2), "little"))


def get_learning_move_cursor_pos() -> int:
    """
    helper function that returns the position of the move learning cursor
    """
    match context.rom.game_title:
        case "POKEMON EMER":
            return int.from_bytes(
                context.emulator.read_bytes(
                    struct.unpack("<I", read_symbol("sMonSummaryScreen"))[0] + 0x40C6, length=1
                ),
                "little",
            )
        case "POKEMON FIRE" | "POKEMON LEAF":
            return int.from_bytes(read_symbol("sMoveSelectionCursorPos"), "little")
        case "POKEMON RUBY" | "POKEMON SAPP":
            return int.from_bytes(read_symbol("gSharedMem", offset=0x18079, size=1), "little")


def parse_start_menu() -> dict:
    """
    Helper function that decodes the state of the start menu.
    """
    is_open = False

    if context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]:
        start_menu_options_symbol = "sCurrentStartMenuActions"
        num_actions_symbol = "sNumStartMenuActions"
        start_menu_enum = StartMenuOptionHoenn
    else:
        start_menu_options_symbol = "sStartMenuOrder"
        num_actions_symbol = "sNumStartMenuItems"
        start_menu_enum = StartMenuOptionKanto

    item_indices = [i for i in read_symbol(start_menu_options_symbol)]
    actions = []

    for i in range(int.from_bytes(read_symbol(num_actions_symbol), "little")):
        actions.append(start_menu_enum(item_indices[i]).name)

    for task in ["SUB_80712B4", "TASK_SHOWSTARTMENU", "TASK_STARTMENUHANDLEINPUT"]:
        if task_is_active(task):
            is_open = True
            break

    return {
        "open": is_open,
        "cursor_pos": struct.unpack("<B", read_symbol("sStartMenuCursorPos"))[0],
        "actions": actions,
    }


def get_battle_menu() -> str:
    """
    determines whether we're on the action selection menu, move selection menu, or neither
    """
    match context.rom.game_title:
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
    active_battler = int.from_bytes(read_symbol("gActiveBattler", size=1), "little")
    battler_controller_funcs = [
        get_symbol_name(struct.unpack("<I", read_symbol("gBattlerControllerFuncs")[i * 4 : i * 4 + 4])[0] - 1)
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
    match context.rom.game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            return (
                get_symbol_name(struct.unpack("<I", read_symbol("gBattleScriptCurrInstr", size=4))[0] - 51)
                == "BATTLESCRIPT_HANDLEFAINTEDMON"
            )
        case _:
            return read_symbol("sText_UseNextPkmn") in read_symbol("gDisplayedStringBattle")


def get_cursor_options(idx: int) -> str:
    match context.rom.game_title:
        case "POKEMON FIRE" | "POKEMON LEAF" | "POKEMON EMER":
            return CursorOptionEFRLG(idx).name
        case _:
            return CursorOptionRS(idx).name
