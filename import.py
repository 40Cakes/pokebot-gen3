import binascii
import os
import shutil
import tkinter as tk
import zlib
from pathlib import Path
from tkinter import ttk, filedialog, font
from typing import IO, Union

from modules.Game import SetROM, GetSymbol, DecodeString
from modules.Memory import unpack_uint16, unpack_uint32
from modules.Profiles import Profile, CreateProfile, ProfileDirectoryExists
from modules.Roms import ListAvailableRoms
from version import pokebot_name, pokebot_version


class MigrationError(Exception):
    pass


def MigrateSaveState(file: IO) -> Profile:
    file.seek(0)
    magic = file.read(4)
    file.seek(0)

    # mGBA state files can either contain the raw serialised state data, or it can
    # contain a PNG file that contains a custom 'gbAs' chunk, which in turn contains
    # the actual (zlib-compressed) state data. We'd like to support both.
    if magic == b'\x89PNG':
        state_data, savegame_data = GetStateDataFromPNG(file)
    elif magic == b'\x07\x00\x00\x01':
        state_data, savegame_data = GetStateDataFromFile(file)
    else:
        raise MigrationError('This does not appear to be a supported save state file.')

    # Importing a save state only makes sense if the ROM for that state is already in
    # the `roms/` directory, otherwise starting the bot would result in an immediate
    # 'ROM not found' error.
    # mGBA stores the CRC32 checksum of the ROM in its save states, so we use that to
    # find the right one.
    crc32 = unpack_uint32(state_data[8:12])
    matching_rom = None
    for rom in ListAvailableRoms():
        with open(rom.file, 'rb') as rom_file:
            rom_crc32 = binascii.crc32(rom_file.read())
        if rom_crc32 == crc32:
            matching_rom = rom
            break
    if matching_rom is None:
        raise MigrationError('Could not find a compatible ROM for this save state... Please place your .gba ROMs in the "roms/" folder.')
    SetROM(matching_rom)

    # Figure out the trainer name so we can use it as the name for the newly imported profile.
    # This code is adapted from `modules/Trainer.py`, except it uses the RAM data stored in the
    # save state instead of accessing a running emulator.
    if matching_rom.game_title in ['POKEMON EMER', 'POKEMON FIRE', 'POKEMON LEAF']:
        pointer_offset = (GetSymbol('gSaveBlock2Ptr')[0] & 0x7FFF) + 0x19000
        pointer = unpack_uint32(state_data[pointer_offset:pointer_offset + 4])
        save_block_offset = (pointer & 0x3FFFF) + 0x21000
        save_block = state_data[save_block_offset:save_block_offset + 12]
    else:
        save_block_offset = (GetSymbol('gSaveBlock2')[0] & 0x3FFFF) + 0x21000
        save_block = state_data[save_block_offset:save_block_offset + 12]

    trainer_name = DecodeString(save_block[0:7])
    trainer_id = unpack_uint16(save_block[10:12])

    profile_name = trainer_name
    n = 2
    while ProfileDirectoryExists(profile_name):
        profile_name = f'{trainer_name}_{str(n)}'
        n += 1

    profile = CreateProfile(profile_name, matching_rom)
    with open(profile.path / 'current_state.ss1', 'wb') as state_file:
        state_file.write(state_data)

    if savegame_data is not None:
        with open(profile.path / 'current_save.sav', 'wb') as save_file:
            save_file.write(savegame_data)

    # In case this save state has been used with the old Pymem implementation of the bot, try to
    # import config and stats into the new directory structure.
    full_game_code = (matching_rom.game_code + str(matching_rom.language)).upper()
    config_dir = Path(__file__).parent / 'config' / full_game_code / f'{trainer_id}-{trainer_name}'
    stats_dir = Path(__file__).parent / 'stats' / full_game_code / f'{trainer_id}-{trainer_name}'

    if config_dir.is_dir():
        shutil.copytree(config_dir, profile.path / 'config')

    if stats_dir.is_dir():
        shutil.copytree(stats_dir, profile.path / 'stats')

    file.close()

    return profile


def GetStateDataFromFile(file: IO) -> tuple[bytes, Union[bytes, None]]:
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


def GetStateDataFromPNG(file: IO) -> tuple[bytes, Union[bytes, None]]:
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
        chunk_length = int.from_bytes(file.read(4))
        chunk_type = file.read(4)
        if chunk_type == b'gbAs':
            state_data = zlib.decompress(file.read(chunk_length))
        elif chunk_type == b'gbAx':
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
        raise MigrationError('Could not find save state data in this file.')

    return state_data, savegame_data


def HandleButtonClick() -> None:
    global error_label

    filetypes = [
        ('mGBA Save States', ('*.ss0', '*.ss1', '*.ss2', '*.ss3', '*.ss4', '*.ss5', '*.ss6', '*.ss7', '*.ss8', '*.ss9'))
    ]

    file = filedialog.askopenfile(
        title='Select Save State',
        initialdir=Path(__file__).parent,
        filetypes=filetypes,
        mode='rb'
    )

    if file is not None:
        try:
            profile = MigrateSaveState(file)
            ShowSuccessMessage(profile.path.name, profile.rom.game_name)
        except MigrationError as error:
            error_label.config(text=str(error), wraplength=360, justify='center')


def ShowSuccessMessage(profile_name, game_name) -> None:
    global window, frame, label_font

    frame.destroy()
    frame = ttk.Frame(window)
    frame.grid()

    headline = 'Save state has been imported successfully! 🥳'
    ttk.Label(frame, text=headline, font=label_font).grid(column=0, row=0, columnspan=2, pady=10)

    ttk.Label(frame, text='Profile Name:', foreground='#666666').grid(column=0, row=2, sticky='E', padx=10, pady=2)
    ttk.Label(frame, text=profile_name).grid(column=1, row=2, sticky='W', padx=10, pady=2)

    ttk.Label(frame, text='Game:', foreground='#666666').grid(column=0, row=3, sticky='E', padx=10, pady=2)
    ttk.Label(frame, text=game_name).grid(column=1, row=3, sticky='W', padx=10, pady=2)

    help_message = 'You can now run pokebot.py and select the newly imported profile to run.'
    ttk.Label(frame, text=help_message, wraplength=360, justify='center').grid(column=0, row=4, columnspan=2, pady=20)

    ttk.Button(frame, text='Close', command=window.destroy, cursor='hand2').grid(column=0, row=5, columnspan=2, pady=30)


if __name__ == '__main__':
    window = tk.Tk()
    window.title(f'Save Importer for {pokebot_name} {pokebot_version}')
    window.geometry('480x320')

    window.bind('<KeyPress>', lambda event: event.keysym == 'Escape' and window.destroy())

    window.grid_rowconfigure(0, weight=1)
    window.grid_columnconfigure(0, weight=1)

    frame = ttk.Frame(window)
    frame.grid()

    label_font = font.Font(weight='bold')
    ttk.Label(frame, text='Import mGBA Save State', font=label_font).grid(column=0, row=0, pady=10)

    help_message = """This tool creates new bot profiles from imported mGBA save state files.
    
    Note: you can only import save states (.ss1, .ss2, ...) and NOT save game files (.sav)!"""
    ttk.Label(frame, text=help_message, wraplength=360, justify='center').grid(column=0, row=1)
    ttk.Button(frame, text='Select file', command=HandleButtonClick, cursor='hand2').grid(column=0, row=2, pady=20)

    error_label = ttk.Label(frame, text='', foreground='red')
    error_label.grid(column=0, row=3)

    window.mainloop()
