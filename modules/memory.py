import sys
import struct
from enum import IntEnum

from modules.console import console
from modules.game import get_symbol, get_symbol_name, get_event_flag_offset
from modules.gui import get_emulator, get_rom


def unpack_uint16(bytes: bytes) -> int:
    return struct.unpack("<H", bytes)[0]


def unpack_uint32(bytes: bytes) -> int:
    return struct.unpack("<I", bytes)[0]


def pack_uint16(int: int) -> bytes:
    return struct.pack("<H", int)


def pack_uint32(int: int) -> bytes:
    return struct.pack("<I", int)


def read_symbol(name: str, offset: int = 0x0, size: int = 0x0) -> bytes:
    """
    This function uses the symbol tables from the Pokémon decompilation projects found here: https://github.com/pret
    Symbol tables are loaded and parsed as a dict in the `Emulator` class, the .sym files for each game can be found
    in `modules/data/symbols`.

    Format of symbol tables:
    `020244ec g 00000258 gPlayerParty`
    020244ec     - memory address
    g            - (l,g,,!) local, global, neither, both
    00000258     - size in bytes (base 16) (0x258 = 600 bytes)
    gPlayerParty - name of the symbol

    GBA memory domains: https://corrupt.wiki/consoles/gameboy-advance/bizhawk-memory-domains
    0x02000000 - 0x02030000 - 256 KB EWRAM (general purpose RAM external to the CPU)
    0x03000000 - 0x03007FFF - 32 KB IWRAM (general purpose RAM internal to the CPU)
    0x08000000 - 0x???????? - Game Pak ROM (0 to 32 MB)

    :param name: name of the symbol to read
    :param offset: (optional) add n bytes to the address of symbol
    :param size: (optional) override the size to read n bytes
    :return: (bytes)
    """
    try:
        addr, length = get_symbol(name)
        if size <= 0:
            size = length

        return get_emulator().read_bytes(addr + offset, size)
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def write_symbol(name: str, data: bytes, offset: int = 0x0) -> bool:
    try:
        addr, length = get_symbol(name)
        if len(data) + offset > length:
            raise Exception(
                f"{len(data) + offset} bytes of data provided, is too large for symbol {addr} ({length} bytes)!"
            )

        get_emulator().write_bytes(addr + offset, data)
        return True
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        sys.exit(1)


def parse_tasks(pretty_names: bool = False) -> list:
    try:
        gTasks = read_symbol("gTasks")
        tasks = []
        for x in range(16):
            name = get_symbol_name(unpack_uint32(gTasks[(x * 40) : (x * 40 + 4)]) - 1, pretty_names)
            if name == "":
                name = str(gTasks[(x * 40) : (x * 40 + 4)])
            tasks.append(
                {
                    "func": name,
                    "isActive": bool(gTasks[(x * 40 + 4)]),
                    "prev": gTasks[(x * 40 + 5)],
                    "next": gTasks[(x * 40 + 6)],
                    "priority": gTasks[(x * 40 + 7)],
                    "data": gTasks[(x * 40 + 8) : (x * 40 + 40)],
                }
            )
        return tasks
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def get_task(func: str) -> dict:
    tasks = parse_tasks()
    for task in tasks:
        if task["func"] == func:
            return task
    return {}


def get_save_block(num: int = 1, offset: int = 0, size: int = 0) -> bytes:
    """
    The Generation III save file is broken up into two game save blocks, this function will return sections from these
    save blocks. Emerald, FireRed and LeafGreen SaveBlocks will randomly move around in memory, which requires following
     a pointer to find them reliably.

    :param num: 1 or 2 (gSaveblock1 or gSaveblock2)
    see: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Game_save_A.2C_Game_save_B
    :param offset: Read n bytes offset from beginning of the save block, use with `size` - useful to reduce amount of
    bytes read if only specific memory region is required.
    :param size: Read n bytes from the offset
    :return: SaveBlock (bytes)
    """
    # https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)
    try:
        if not size:
            size = get_symbol(f"GSAVEBLOCK{num}")[1]
        if get_rom().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            p_Trainer = unpack_uint32(read_symbol(f"gSaveBlock{num}Ptr"))
            if p_Trainer == 0:
                return None
            return get_emulator().read_bytes(p_Trainer + offset, size)
        else:
            return read_symbol(f"gSaveBlock{num}", offset=offset, size=size)
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


class GameState(IntEnum):
    # Menus
    BAG_MENU = 100
    CHOOSE_STARTER = 101
    PARTY_MENU = 102
    # Battle related
    BATTLE = 200
    BATTLE_STARTING = 201
    BATTLE_ENDING = 202
    # Misc
    OVERWORLD = 900
    CHANGE_MAP = 901
    TITLE_SCREEN = 902
    MAIN_MENU = 903
    UNKNOWN = 999


def get_game_state_symbol() -> str:
    callback2 = read_symbol("gMain", 4, 4)  # gMain.callback2
    addr = unpack_uint32(callback2) - 1
    return get_symbol_name(addr)


def get_game_state() -> GameState:
    match get_game_state_symbol():
        case "CB2_OVERWORLD":
            return GameState.OVERWORLD
        case "BATTLEMAINCB2":
            return GameState.BATTLE
        case "CB2_BAGMENURUN" | "SUB_80A3118":
            return GameState.BAG_MENU
        case "CB2_UPDATEPARTYMENU" | "CB2_PARTYMENUMAIN":
            return GameState.PARTY_MENU
        case "CB2_INITBATTLE" | "CB2_HANDLESTARTBATTLE":
            return GameState.BATTLE_STARTING
        case "CB2_ENDWILDBATTLE":
            return GameState.BATTLE_ENDING
        case "CB2_LOADMAP" | "CB2_LOADMAP2" | "CB2_DOCHANGEMAP" | "SUB_810CC80":
            return GameState.CHANGE_MAP
        case "CB2_STARTERCHOOSE" | "CB2_CHOOSESTARTER":
            return GameState.CHOOSE_STARTER
        case "CB2_INITCOPYRIGHTSCREENAFTERBOOTUP" | "CB2_WAITFADEBEFORESETUPINTRO" | "CB2_SETUPINTRO" | "CB2_INTRO" | "CB2_INITTITLESCREEN" | "CB2_TITLESCREENRUN" | "CB2_INITCOPYRIGHTSCREENAFTERTITLESCREEN" | "CB2_INITMAINMENU" | "MAINCB2" | "MAINCB2_INTRO":
            return GameState.TITLE_SCREEN
        case "CB2_MAINMENU":
            return GameState.MAIN_MENU
        case _:
            return GameState.UNKNOWN


def game_has_started() -> bool:
    """
    Reports whether the game has progressed past the main menu (save loaded
    or new game started.)
    """
    return read_symbol("sPlayTimeCounterState") != b"\x00" and 0 != int.from_bytes(
        read_symbol("gObjectEvents", 0x10, 9), byteorder="little"
    )


def get_event_flag(flag_name: str) -> bool:
    flag_offset = get_event_flag_offset(flag_name)
    flag_byte = get_save_block(1, offset=flag_offset[0], size=1)

    return bool((flag_byte[0] >> (flag_offset[1])) & 1)
