import os
import re
from dataclasses import dataclass
from pathlib import Path

import jsonschema
from rich.prompt import Prompt, IntPrompt
from ruamel.yaml import YAML

from modules.Console import console
from modules.Roms import ROMS_DIRECTORY, ROM, ListAvailableRoms, LoadROMData

PROFILES_DIRECTORY = Path(__file__).parent.parent / "config"

metadata_schema = """
type: object
properties:
    version:
        type: integer
        enum:
            - 1
    rom:
        type: object
        properties:
            file_name:
                type: string
            game_code:
                type: string
            software_version:
                type: integer
            language:
                type: string
                enum:
                    - E
                    - F
                    - D
                    - I
                    - J
                    - P
                    - S
"""


@dataclass
class Profile:
    rom: ROM
    path: Path


def ListAvailableProfiles() -> list[Profile]:
    if not PROFILES_DIRECTORY.is_dir():
        raise RuntimeError(f"Directory {str(PROFILES_DIRECTORY)} does not exist!")

    profiles = []
    for entry in PROFILES_DIRECTORY.iterdir():
        try:
            profiles.append(LoadProfile(entry))
        except RuntimeError:
            pass

    return profiles


def LoadProfileByName(name: str) -> Profile:
    return LoadProfile(PROFILES_DIRECTORY / name)


def LoadProfile(path) -> Profile:
    if not path.is_dir():
        raise RuntimeError('Path is not a valid profile directory.')

    metadata_file = path / "metadata.yml"
    if not metadata_file.is_file():
        raise RuntimeError('Path is not a valid profile directory.')

    metadata = {}
    try:
        metadata = YAML().load(metadata_file)
        jsonschema.validate(metadata, YAML().load(metadata_schema))
    except:
        console.print_exception(show_locals=True)
        console.print(f'[bold red]Metadata file for profile "{path.name}" is invalid![/]')
        input('Press enter to exit...')
        os._exit(1)

    rom_file = ROMS_DIRECTORY / metadata['rom']['file_name']
    if rom_file.is_file():
        rom = LoadROMData(rom_file)
        return Profile(rom, path)
    else:
        for rom in ListAvailableRoms():
            if rom.game_code == metadata['rom']['game_code'] \
                    and rom.software_version == metadata['rom']['software_version'] \
                    and rom.language == metadata['rom']['language']:
                return Profile(rom, path)

    console.print(f'[bold red]Could not find a ROM for profile "{path.name}".[/]')
    input('Press enter to exit...')
    os._exit(1)


def ProfileDirectoryExists(name: str) -> bool:
    return (PROFILES_DIRECTORY / name).exists()


def CreateProfile(name: str, rom: ROM) -> Profile:
    profile_directory = PROFILES_DIRECTORY / name
    if profile_directory.exists():
        raise RuntimeError(f'There already is a profile called "{name}", cannot create a new one with that name.')

    profile_directory.mkdir()
    YAML().dump({
        "version": 1,
        "rom": {
            "file_name": rom.file.name,
            "game_code": rom.game_code,
            "software_version": rom.software_version,
            "language": str(rom.language)
        }
    }, profile_directory / "metadata.yml")

    return Profile(rom, profile_directory)


def CreateNewProfileConsoleHelper() -> Profile:
    roms = ListAvailableRoms()
    if len(roms) == 0:
        console.print(f'[bold red] Could not find any ROMs. Please put your *.gba files into the `roms/` directory.[/]')
        os._exit(1)

    name = None
    name_check = re.compile('^[-_a-zA-Z0-9]+$')
    while name is None:
        input_name = str(
            Prompt.ask("Name of the new profile (must only contain letters, digits, hyphen and underscore)"))
        if not name_check.match(input_name):
            console.print(f'[bold red] "{input_name}" is not a valid profile name.[/]')
            continue
        if ProfileDirectoryExists(input_name):
            console.print(f'[bold red] A profile named "{input_name}" already exists.[/]')
            continue
        name = input_name

    print("")
    print("Available ROMs:")
    for i in range(1, len(roms) + 1):
        rom = roms[i - 1]
        print(f"    [{i}] {rom.file.name} ({rom.game_title}, v{rom.software_version}, language: {rom.language})")
    rom = None
    while rom is None:
        input_rom = int(IntPrompt.ask("ROM to use for this profile (cannot be changed afterwards)"))
        if input_rom < 1 or input_rom > len(roms):
            console.print(f'[bold red] Please select a number between 1 and {len(roms)}.[/]')
            continue
        rom = roms[input_rom - 1]

    return CreateProfile(name, rom)


def SelectProfileConsoleHelper(available_profiles: list[Profile]) -> Profile:
    print("Available profiles:")
    for n in range(1, len(available_profiles) + 1):
        print(f"    [{n}] {available_profiles[n - 1].path.name}")
    print("    [n] Create a new profile")
    profile = None
    while profile is None:
        input = Prompt.ask("Choice")
        if input == "n":
            profile = CreateNewProfileConsoleHelper()
        else:
            profile_id = int(input)
            if profile_id <= 0 or profile_id > len(available_profiles):
                console.print(f'[bold red] Please select a number between 1 and {len(available_profiles)}.[/]')
                continue
            else:
                profile = available_profiles[profile_id - 1]

    return profile
