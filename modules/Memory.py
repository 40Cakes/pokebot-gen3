import sys
import struct
from enum import IntEnum

from modules.Console import console
from modules.Game import GetSymbol, GetSymbolName, GetEventFlagOffset
from modules.Gui import GetEmulator, GetROM


def unpack_uint16(bytes: bytes) -> int:
    return struct.unpack("<H", bytes)[0]


def unpack_uint32(bytes: bytes) -> int:
    return struct.unpack("<I", bytes)[0]


def pack_uint16(int: int) -> bytes:
    return struct.pack("<H", int)


def pack_uint32(int: int) -> bytes:
    return struct.pack("<I", int)


def ReadSymbol(name: str, offset: int = 0x0, size: int = 0x0) -> bytes:
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
        addr, length = GetSymbol(name)
        if size <= 0:
            size = length

        return GetEmulator().ReadBytes(addr + offset, size)
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def WriteSymbol(name: str, data: bytes, offset: int = 0x0) -> bool:
    try:
        addr, length = GetSymbol(name)
        if len(data) + offset > length:
            raise Exception(
                f"{len(data) + offset} bytes of data provided, is too large for symbol {addr} ({length} bytes)!"
            )

        GetEmulator().WriteBytes(addr + offset, data)
        return True
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        sys.exit(1)


def ParseTasks(pretty_names: bool = False) -> list:
    try:
        gTasks = ReadSymbol("gTasks")
        tasks = []
        for x in range(16):
            name = GetSymbolName(unpack_uint32(gTasks[(x * 40) : (x * 40 + 4)]) - 1, pretty_names)
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


def GetTask(func: str) -> dict:
    tasks = ParseTasks()
    for task in tasks:
        if task["func"] == func:
            return task
    return {}


def GetSaveBlock(num: int = 1, offset: int = 0, size: int = 0) -> bytes:
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
            size = GetSymbol(f"GSAVEBLOCK{num}")[1]
        if GetROM().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            p_Trainer = unpack_uint32(ReadSymbol(f"gSaveBlock{num}Ptr"))
            if p_Trainer == 0:
                return None
            return GetEmulator().ReadBytes(p_Trainer + offset, size)
        else:
            return ReadSymbol(f"gSaveBlock{num}", offset=offset, size=size)
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)


def GetItemOffsets() -> list[tuple[int, int]]:
    # Game specific offsets
    # Source: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Section_1_-_Team_.2F_Items
    match GetROM().game_title:
        case "POKEMON FIRE" | "POKEMON LEAF":
            return [(0x298, 120), (0x310, 168), (0x3B8, 120), (0x430, 52), (0x464, 232), (0x54C, 172)]
        case "POKEMON EMER":
            return [(0x498, 200), (0x560, 120), (0x5D8, 120), (0x650, 64), (0x690, 256), (0x790, 184)]
        case _:
            return [(0x498, 200), (0x560, 80), (0x5B0, 80), (0x600, 64), (0x640, 256), (0x740, 184)]


def GetItemKey() -> int:
    match GetROM().game_title:
        case "POKEMON FIRE" | "POKEMON LEAF":
            return unpack_uint16(GetSaveBlock(2, 0xF20, 2))
        case "POKEMON EMER":
            return unpack_uint16(GetSaveBlock(2, 0xAC, 2))
        case _:
            return 0


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


def GetGameStateSymbol() -> str:
    callback2 = ReadSymbol("gMain", 4, 4)  # gMain.callback2
    addr = unpack_uint32(callback2) - 1
    return GetSymbolName(addr)


def GetGameState() -> GameState:
    match GetGameStateSymbol():
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


def GameHasStarted() -> bool:
    """
    Reports whether the game has progressed past the main menu (save loaded
    or new game started.)
    """
    return ReadSymbol("sPlayTimeCounterState") != b"\x00" and 0 != int.from_bytes(
        ReadSymbol("gObjectEvents", 0x10, 9), byteorder="little"
    )


def GetEventFlag(flag_name: str) -> bool:
    flag_offset = GetEventFlagOffset(flag_name)

    match GetROM().game_title:
        case "POKEMON FIRE" | "POKEMON LEAF":
            sav_offset = 3808
        case "POKEMON EMER":
            sav_offset = 4720
        case _:
            sav_offset = 4640

    flag_byte = GetSaveBlock(1, offset=sav_offset + (flag_offset // 8), size=1)
    return bool((flag_byte[0] >> (flag_offset % 8)) & 1)
