import sys
import typing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import jsonschema
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
    last_played: typing.Union[datetime, None]


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

    try:
        metadata = YAML().load(metadata_file)
        jsonschema.validate(metadata, YAML().load(metadata_schema))
    except:
        console.print_exception(show_locals=True)
        console.print(f'[bold red]Metadata file for profile "{path.name}" is invalid![/]')
        sys.exit(1)

    current_state = path / "current_state.ss1"
    if current_state.exists():
        last_played = datetime.fromtimestamp(current_state.stat().st_mtime)
    else:
        last_played = None

    rom_file = ROMS_DIRECTORY / metadata['rom']['file_name']
    if rom_file.is_file():
        rom = LoadROMData(rom_file)
        return Profile(rom, path, last_played)
    else:
        for rom in ListAvailableRoms():
            if rom.game_code == metadata['rom']['game_code'] \
                    and rom.software_version == metadata['rom']['software_version'] \
                    and rom.language == metadata['rom']['language']:
                return Profile(rom, path, last_played)

    console.print(f'[bold red]Could not find a ROM for profile "{path.name}".[/]')
    sys.exit(1)


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

    return Profile(rom, profile_directory, None)
