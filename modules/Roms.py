from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

ROMS_DIRECTORY = Path(__file__).parent.parent / "roms"


class ROMLanguage(StrEnum):
    English = "E"
    French = "F"
    German = "D"
    Italian = "I"
    Japanese = "J"
    Other = "P"
    Spanish = "S"


@dataclass
class ROM:
    file: Path
    game_title: str
    game_code: str
    language: ROMLanguage
    maker_code: str
    software_version: int


def ListAvailableRoms() -> list[ROM]:
    """
    This scans all files in the `roms/` directory and returns any entry that might
    be a valid GBA ROM, along with some meta data that could be extracted from the
    ROM header.

    The ROM (header) structure is described on this website:
    https://problemkaputt.de/gbatek-gba-cartridge-header.htm

    :return: List of all the valid ROMS that have been found
    """
    if not ROMS_DIRECTORY.is_dir():
        raise RuntimeError(f"Directory {str(ROMS_DIRECTORY)} does not exist!")

    roms = []
    for file in ROMS_DIRECTORY.iterdir():
        if file.is_file():
            try:
                roms.append(LoadROMData(file))
            except RuntimeError:
                pass

    return roms


def LoadROMData(file) -> ROM:
    # GBA Cardridge headers are 0xC0 bytes long, so any files smaller than that cannot be a ROM.
    if file.stat().st_size < 0xC0:
        raise RuntimeError("This does not seem to be a valid ROM.")

    with open(file, "rb") as handle:
        # The byte at location 0xB2 must have value 0x96 in valid GBA ROMs
        handle.seek(0xB2)
        magic_number = int.from_bytes(handle.read(1))
        if magic_number != 0x96:
            raise RuntimeError("This does not seem to be a valid ROM.")

        handle.seek(0xA0)
        game_title = handle.read(12).decode('ascii')
        game_code = handle.read(4).decode('ascii')
        maker_code = handle.read(2).decode('ascii')

        handle.seek(0xBC)
        software_version = int.from_bytes(handle.read(1))

        return ROM(file, game_title, game_code[:3], ROMLanguage(game_code[3]), maker_code, software_version)
