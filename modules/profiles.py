import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from modules import exceptions
from modules.config import load_config_file, save_config_file
from modules.config.schemas_v1 import ProfileMetadata, ProfileMetadataROM
from modules.console import console
from modules.roms import ROMS_DIRECTORY, ROM, list_available_roms, load_rom_data
from modules.runtime import get_base_path

PROFILES_DIRECTORY = get_base_path() / "profiles"


@dataclass
class Profile:
    """
    Profiles are config directories that contain all data for a save game, such as saves,
    screenshots, stats, custom config, etc. -- except the ROM itself.

    The only requirements for a Profile are: There must be a subdirectory in `profiles/` with
    the name of the profile, and inside that directory there must be a file called
    `metadata.yml` that satisfies the `metadata_schema`.

    This metadata file specifies which game/ROM a save game is associated with, so we can
    load the correct ROM when selected.
    """

    rom: ROM
    path: Path
    last_played: datetime | None


def list_available_profiles() -> list[Profile]:
    if not PROFILES_DIRECTORY.is_dir():
        raise RuntimeError(f"Directory {str(PROFILES_DIRECTORY)} does not exist!")

    profiles = []
    for entry in PROFILES_DIRECTORY.iterdir():
        if entry.name.startswith('_'):
            continue
        try:
            profiles.append(load_profile(entry))
        except RuntimeError:
            pass

    return profiles


def load_profile_by_name(name: str) -> Profile:
    return load_profile(PROFILES_DIRECTORY / name)


def load_profile(path: Path) -> Profile:
    if not path.is_dir():
        raise RuntimeError("Path is not a valid profile directory.")
    metadata = load_config_file(path / ProfileMetadata.filename, ProfileMetadata, strict=True)
    current_state = path / "current_state.ss1"
    if current_state.exists():
        last_played = datetime.fromtimestamp(current_state.stat().st_mtime)
    else:
        last_played = None

    rom_file = ROMS_DIRECTORY / metadata.rom.file_name
    if rom_file.is_file():
        rom = load_rom_data(rom_file)
        return Profile(rom, path, last_played)
    else:
        for rom in list_available_roms():
            if all([
                rom.game_code == metadata.rom.game_code,
                rom.revision == metadata.rom.revision,
                rom.language == metadata.rom.language,
            ]):
                return Profile(rom, path, last_played)

    console.print(
        f"[bold red]Could not find ROM `{metadata.rom.file_name}` for profile `{path.name}`, "
        f"please place `{metadata.rom.file_name}` into `{ROMS_DIRECTORY}`!"
    )
    sys.exit(1)


def profile_directory_exists(name: str) -> bool:
    return (PROFILES_DIRECTORY / name).exists()


def create_profile(name: str, rom: ROM) -> Profile:
    if name.startswith('_'):
        raise exceptions.PrettyValueError(f'Profile names cannot start with the underscore "_" character.')
    profile_directory = PROFILES_DIRECTORY / name
    if profile_directory.exists():
        raise RuntimeError(f'There already is a profile called "{name}", cannot create a new one with that name.')

    rom_cfg = ProfileMetadataROM(
        file_name=rom.file.name,
        game_code=rom.game_code,
        revision=rom.revision,
        language=str(rom.language),
    )
    profile_metadata = ProfileMetadata(rom=rom_cfg)
    save_config_file(profile_directory, profile_metadata, strict=False)

    return Profile(rom, profile_directory, None)
