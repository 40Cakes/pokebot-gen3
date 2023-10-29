import math

from modules.console import console
from modules.game import get_symbol
from modules.gui import get_emulator, get_rom, set_message
from modules.memory import read_symbol, unpack_uint32
from modules.pokemon import Pokemon

# see pret/pokeemerald:include/pokemon_storage_system.h
TOTAL_BOXES_COUNT = 14
IN_BOX_ROWS = 5
IN_BOX_COLUMNS = 6
IN_BOX_COUNT = IN_BOX_ROWS * IN_BOX_COLUMNS


def _find_pokemon_storage_offset() -> tuple[int, int]:
    if get_rom().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        offset = unpack_uint32(read_symbol("gPokemonStoragePtr"))
        length = get_symbol("gPokemonStorage")[1]
    else:
        offset, length = get_symbol("gPokemonStorage")
    return offset, length


def import_into_storage(data: bytes) -> bool:
    data = data[:80]

    # find first available spot offset
    space_available = False
    g_pokemon_storage = _find_pokemon_storage_offset()[0]
    for i in range(IN_BOX_COUNT * TOTAL_BOXES_COUNT):
        # the first 4 bytes are the current box
        # first mon is stored at offset gPokemonStorage + 4
        offset_to_check = 4 + i * 80
        # if a spot is space_available, it is all 0
        space_available = unpack_uint32(get_emulator().read_bytes(g_pokemon_storage + offset_to_check, 4)) == 0
        if space_available:
            available_offset = offset_to_check
            break

    pokemon = Pokemon(data)
    if pokemon.is_valid and space_available:
        box = math.floor((available_offset/80) / IN_BOX_COUNT)
        message = f"Saved {pokemon.species.name} to PC box {box}!"

        get_emulator().write_bytes(g_pokemon_storage + available_offset, data)
        set_message(message)
        console.print(message)
    else:
        message = f"Not enough room in PC to automatically import {pokemon.species.name}!"
        set_message(message)
        console.print(message)
        return False
    return True
