import struct
from enum import IntEnum, auto

from modules.context import context
from modules.game import (
    _event_flags,
    _event_vars,
    get_event_flag_offset,
    get_event_var_offset,
    get_symbol,
    get_symbol_name,
)
from modules.state_cache import state_cache


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

        return context.emulator.read_bytes(addr + offset, size)
    except SystemExit:
        raise


def write_symbol(name: str, data: bytes, offset: int = 0x0) -> bool:
    try:
        addr, length = get_symbol(name)
        if len(data) + offset > length:
            raise Exception(
                f"{len(data) + offset} bytes of data provided, is too large for symbol {addr} ({length} bytes)!"
            )

        context.emulator.write_bytes(addr + offset, data)
        return True
    except SystemExit:
        raise


def get_save_block(num: int = 1, offset: int = 0, size: int = 0) -> bytes | None:
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
        if context.rom.is_rs:
            return read_symbol(f"gSaveBlock{num}", offset, size)
        p_trainer = unpack_uint32(read_symbol(f"gSaveBlock{num}Ptr"))
        if p_trainer == 0:
            return None
        return context.emulator.read_bytes(p_trainer + offset, size)
    except SystemExit:
        raise


def write_to_save_block(data: bytes, num: int = 1, offset: int = 0) -> bool:
    """
    Writes data to a save block - ! use with care, high potential of corrupting save data in memory

    :param data: Data to write to saveblock
    :param num: 1 or 2 (gSaveblock1 or gSaveblock2)
    see: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Game_save_A.2C_Game_save_B
    :param offset: Write n bytes offset from beginning of the save block
    :return: Success true/false (bool)
    """
    # https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)
    try:
        if context.rom.is_rs:
            return write_symbol(f"gSaveBlock{num}", data, offset)
        p_trainer = unpack_uint32(read_symbol(f"gSaveBlock{num}Ptr"))
        if p_trainer == 0:
            return False
        return context.emulator.write_bytes(p_trainer + offset, data)
    except SystemExit:
        raise


class GameState(IntEnum):
    # Menus
    BAG_MENU = auto()
    CHOOSE_STARTER = auto()
    PARTY_MENU = auto()
    # Battle related
    BATTLE = auto()
    BATTLE_STARTING = auto()
    BATTLE_ENDING = auto()
    # Misc
    OVERWORLD = auto()
    CHANGE_MAP = auto()
    TITLE_SCREEN = auto()
    MAIN_MENU = auto()
    GARBAGE_COLLECTION = auto()
    EVOLUTION = auto()
    EGG_HATCH = auto()
    WHITEOUT = auto()
    UNKNOWN = auto()
    QUEST_LOG = auto()


def get_game_state_symbol() -> str:
    callback2 = read_symbol("gMain", 4, 4)  # gMain.callback2
    addr = unpack_uint32(callback2) - 1
    callback_name = get_symbol_name(addr)
    state_cache.callback2 = callback_name
    return callback_name


def get_game_state() -> GameState:
    if state_cache.game_state.age_in_frames == 0:
        return state_cache.game_state.value

    match get_game_state_symbol():
        case (
            "CB2_SETUPOVERWORLDFORQLPLAYBACKWITHWARPEXIT"
            | "CB2_SETUPOVERWORLDFORQLPLAYBACK"
            | "CB2_LOADMAPFORQLPLAYBACK"
            | "CB2_ENTERFIELDFROMQUESTLOG"
        ):
            return GameState.QUEST_LOG
        case "CB2_OVERWORLD":
            result = GameState.OVERWORLD
        case "BATTLEMAINCB2":
            result = GameState.BATTLE
        case "CB2_BAGMENURUN" | "SUB_80A3118":
            result = GameState.BAG_MENU
        case "CB2_UPDATEPARTYMENU" | "CB2_PARTYMENUMAIN":
            result = GameState.PARTY_MENU
        case "CB2_INITBATTLE" | "CB2_HANDLESTARTBATTLE":
            result = GameState.BATTLE_STARTING
        case "CB2_ENDWILDBATTLE":
            result = GameState.BATTLE_ENDING
        case "CB2_LOADMAP" | "CB2_LOADMAP2" | "CB2_DOCHANGEMAP" | "SUB_810CC80":
            result = GameState.CHANGE_MAP
        case "CB2_STARTERCHOOSE" | "CB2_CHOOSESTARTER":
            result = GameState.CHOOSE_STARTER
        case (
            "CB2_INITCOPYRIGHTSCREENAFTERBOOTUP"
            | "CB2_WAITFADEBEFORESETUPINTRO"
            | "CB2_SETUPINTRO"
            | "CB2_INTRO"
            | "CB2_INITTITLESCREEN"
            | "CB2_TITLESCREENRUN"
            | "CB2_INITCOPYRIGHTSCREENAFTERTITLESCREEN"
            | "CB2_INITMAINMENU"
            | "MAINCB2"
            | "MAINCB2_INTRO"
        ):
            result = GameState.TITLE_SCREEN
        case "CB2_MAINMENU":
            result = GameState.MAIN_MENU
        case "CB2_EVOLUTIONSCENEUPDATE":
            result = GameState.EVOLUTION
        case "CB2_EGGHATCH" | "CB2_LOADEGGHATCH" | "CB2_EGGHATCH_0" | "CB2_EGGHATCH_1":
            result = GameState.EGG_HATCH
        case "CB2_WHITEOUT":
            result = GameState.WHITEOUT
        case _:
            result = GameState.UNKNOWN

    state_cache.game_state = result
    return result


def game_has_started() -> bool:
    """
    Reports whether the game has progressed past the main menu (save loaded
    or new game started.)
    """
    return (
        read_symbol("sPlayTimeCounterState") != b"\x00"
        and int.from_bytes(read_symbol("gObjectEvents", 0x10, 9), byteorder="little") != 0
    )


def get_event_flag(flag_name: str) -> bool:
    if flag_name not in _event_flags:
        return False

    flag_offset = get_event_flag_offset(flag_name)
    flag_byte = get_save_block(1, offset=flag_offset[0], size=1)

    return bool((flag_byte[0] >> (flag_offset[1])) & 1)


def get_event_flag_by_number(flag_number: int) -> bool:
    if context.rom.is_rs:
        offset = 0x1220
    elif context.rom.is_emerald:
        offset = 0x1270
    else:
        offset = 0x0EE0

    flag_offset = offset + (flag_number // 8)
    flag_bit = 1 << (flag_number % 8)
    flag_byte = get_save_block(1, offset=flag_offset, size=1)[0]

    return bool(flag_byte & flag_bit)


def set_event_flag(flag_name: str, new_value: bool | None = None) -> bool:
    if flag_name not in _event_flags:
        return False

    flag_offset = get_event_flag_offset(flag_name)
    flag_byte = get_save_block(1, offset=flag_offset[0], size=1)[0]

    if new_value is None:
        new_byte = flag_byte ^ (1 << flag_offset[1])
    elif new_value is True:
        new_byte = flag_byte | (1 << flag_offset[1])
    else:
        new_byte = flag_byte & ((1 << flag_offset[1]) ^ 0xFF)

    write_to_save_block(int.to_bytes(new_byte), 1, offset=flag_offset[0])
    return True


def set_event_flag_by_number(flag_number: int) -> None:
    if context.rom.is_rs:
        offset = 0x1220
    elif context.rom.is_emerald:
        offset = 0x1270
    else:
        offset = 0x0EE0

    flag_offset = offset + (flag_number // 8)
    flag_bit = 1 << (flag_number % 8)
    flag_byte = get_save_block(1, offset=flag_offset, size=1)[0]
    write_to_save_block(bytes([flag_byte ^ flag_bit]), num=1, offset=flag_offset)


def get_event_var(var_name: str) -> int:
    if var_name not in _event_vars:
        return -1
    else:
        return unpack_uint16(get_save_block(1, offset=_event_vars[var_name], size=2))


def get_event_var_by_number(var_number: int) -> int:
    if context.rom.is_rs:
        vars_offset = 0x1340
    elif context.rom.is_emerald:
        vars_offset = 0x139C
    else:
        vars_offset = 0x1000

    return unpack_uint16(get_save_block(1, offset=vars_offset + (var_number * 2), size=2))


def set_event_var(var_name: str, new_value: int) -> bool:
    if var_name not in _event_vars:
        return False

    if new_value < 0 or new_value > 2**16 - 1:
        raise ValueError(f"Event Var values must be between 0 and {2 ** 16 - 1}, but '{new_value}' was given.")

    write_to_save_block(pack_uint16(new_value), 1, offset=get_event_var_offset(var_name))
    return True
