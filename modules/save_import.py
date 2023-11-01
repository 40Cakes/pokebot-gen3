import binascii
import os
import zlib
from typing import IO

from modules.memory import unpack_uint32
from modules.profiles import Profile, create_profile
from modules.roms import ROM, list_available_roms


class MigrationError(Exception):
    pass


def migrate_save_state(file: IO, profile_name: str, selected_rom: ROM) -> Profile:
    file.seek(0)
    magic = file.read(4)
    file.seek(0)

    # mGBA state files can either contain the raw serialised state data, or it can
    # contain a PNG file that contains a custom 'gbAs' chunk, which in turn contains
    # the actual (zlib-compressed) state data. We'd like to support both.
    if magic == b"\x89PNG":
        state_data, savegame_data = get_state_data_from_png(file)
    elif magic == b"\x07\x00\x00\x01":
        state_data, savegame_data = get_state_data_from_mgba_state_file(file)
    else:
        # Check whether this is a raw save game
        try:
            file.seek(0xFF8)
            magic = file.read(4)
            file.seek(0)
        except:
            magic = b""

        if magic == b"\x25\x20\x01\x08":
            state_data = None
            savegame_data = file.read()
        else:
            raise MigrationError("This does not appear to be a supported save state file.")

    # Importing a save state only makes sense if the ROM for that state is already in
    # the `roms/` directory, otherwise starting the bot would result in an immediate
    # 'ROM not found' error.
    # mGBA stores the CRC32 checksum of the ROM in its save states, so we use that to
    # find the right one.
    if state_data is not None:
        crc32 = unpack_uint32(state_data[8:12])
        matching_rom = None
        for rom in list_available_roms():
            with open(rom.file, "rb") as rom_file:
                rom_crc32 = binascii.crc32(rom_file.read())
            if rom_crc32 == crc32:
                matching_rom = rom
                break
        if matching_rom is None:
            raise MigrationError(
                'Could not find a compatible ROM for this save state... Please place your .gba ROMs in the "roms/" folder.'
            )
        selected_rom = matching_rom

    profile = create_profile(profile_name, selected_rom)
    if state_data is not None:
        with open(profile.path / "current_state.ss1", "wb") as state_file:
            state_file.write(state_data)

    if savegame_data is not None:
        with open(profile.path / "current_save.sav", "wb") as save_file:
            save_file.write(savegame_data)

    file.close()

    return profile


def get_state_data_from_mgba_state_file(file: IO) -> tuple[bytes, bytes | None]:
    state_data = file.read(0x61000)
    savegame_data = None

    # Save states may contain additional ('extended') data blocks, containing
    # things such as RTC state, cheats settings, save data, etc.
    # Structure of these data blocks is:
    #    0x00-0x04  type ID (unsigned int, little endian)
    #    0x04-0x08  length of data (unsigned int, little endian)
    #    0x08-...   data
    while True:
        extdata_type_bytes = file.read(4)
        # Detects when we reached the end of the file.
        if len(extdata_type_bytes) != 4:
            break

        extdata_type = unpack_uint32(extdata_type_bytes)
        extdata_length = unpack_uint32(file.read(4))

        # We are only interested in save data, which is identified by type=2
        if extdata_type == 2:
            savegame_data = file.read(extdata_length)
            break
        else:
            file.seek(extdata_length, os.SEEK_CUR)

    return state_data, savegame_data


def get_state_data_from_png(file: IO) -> tuple[bytes, bytes | None]:
    state_data = None
    savegame_data = None

    # Skip the PNG file header
    file.seek(8)

    # PNG files consist of chunks, each consisting of a 4-byte length,
    # 4-character ID (ASCII) and the data.
    #
    # mGBA stores the actual save state in a 'gbAs' chunk, and extended
    # data blocks (see comment in `GetStateDataFromFile()` for what those
    # are and what their data structure is) in 'gbAx' chunks.
    #
    # Both are zlib-compressed, so `zlib.decompress()` is required before
    # being able to use the data.
    while True:
        chunk_length = int.from_bytes(file.read(4), byteorder="big")
        chunk_type = file.read(4)
        if chunk_type == b"gbAs":
            state_data = zlib.decompress(file.read(chunk_length))
        elif chunk_type == b"gbAx":
            ext_type = unpack_uint32(file.read(4))
            file.seek(4, os.SEEK_CUR)
            if ext_type == 2:
                savegame_data = zlib.decompress(file.read(chunk_length - 8))
            else:
                file.seek(chunk_length - 8, os.SEEK_CUR)
        elif len(chunk_type) != 4:
            # Detects when we reached the end of the file.
            break
        else:
            file.seek(chunk_length, os.SEEK_CUR)
        file.seek(4, os.SEEK_CUR)

    if state_data is None:
        raise MigrationError("Could not find save state data in this file.")

    return state_data, savegame_data
