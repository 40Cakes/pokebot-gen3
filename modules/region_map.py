from modules.context import context
from modules.memory import read_symbol, unpack_uint32, unpack_uint16


def get_map_cursor() -> tuple[int, int] | None:
    if context.rom.is_frlg:
        symbol_name = "sMapCursor"
        offset = 0
    elif context.rom.is_emerald:
        symbol_name = "sRegionMap"
        offset = 0x54
    else:
        symbol_name = "gRegionMap"
        offset = 0x54

    pointer = unpack_uint32(read_symbol(symbol_name))
    if pointer == 0:
        return None

    data = context.emulator.read_bytes(pointer + offset, 4)
    return unpack_uint16(data[0:2]), unpack_uint16(data[2:4])
