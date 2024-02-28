import contextlib
import json
import os
import string
from pathlib import Path

from modules.context import context
from modules.pokemon import Pokemon


def read_file(file: Path) -> str | None:
    """
    Simple function to read data from a file, return False if file doesn't exist
    :param file: File to read
    :return: File's contents (str) or None if any kind of error occurred
    """
    try:
        if os.path.exists(file):
            with open(file, mode="r", encoding="utf-8") as open_file:
                return open_file.read()
        else:
            return None
    except Exception:
        return None


def write_file(file: Path, value: str, mode: str = "w") -> bool:
    """
    Simple function to write data to a file, will create the file if doesn't exist.
    Writes to a temp file, then performs os.replace to prevent corruption of files (atomic operations).

    :param file: File to write to
    :param value: Value to write to file
    :param mode: Write mode
    :return: True if file was written to successfully, otherwise False (bool)
    """

    tmp_file = str(f"{file}.tmp")
    try:
        directory = os.path.dirname(tmp_file)
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(tmp_file, mode=mode, encoding="utf-8") as save_file:
            save_file.write(value)
            save_file.flush()
            os.fsync(save_file.fileno())

        os.replace(tmp_file, file)

    except Exception:
        return False

    finally:
        if os.path.exists(tmp_file):
            with contextlib.suppress(Exception):
                os.unlink(tmp_file)
        return True


def make_string_safe_for_file_name(base_string: str) -> str:
    """
    :return: The string name with any characters that might be problematic in file names replaced.
    """
    result = ""
    for i in range(len(base_string)):
        if base_string[i] in f"-_.()' {string.ascii_letters}{string.digits}":
            result += base_string[i]
        elif base_string[i] == "♂":
            result += "_m"
        elif base_string[i] == "♀":
            result += "_f"
        elif base_string[i] == "!":
            result += "em"
        elif base_string[i] == "?":
            result += "qm"
        else:
            result += "_"
    return result


def save_pk3(pokemon: Pokemon) -> None:
    """
    Takes the byte data of [obj]Pokémon.data and outputs it in a pkX format in the /profiles/[PROFILE]/pokemon dir.
    """
    pokemon_dir_path = context.profile.path / "pokemon"
    if not pokemon_dir_path.exists():
        pokemon_dir_path.mkdir()

    pk3_file = f"{pokemon.species.national_dex_number}"
    if pokemon.is_shiny:
        pk3_file = f"{pk3_file} ★"

    pk3_file = pokemon_dir_path / (
        f"{pk3_file} - {make_string_safe_for_file_name(pokemon.species_name_for_stats)} - {pokemon.nature} "
        f"[{pokemon.ivs.sum()}] - {hex(pokemon.personality_value)[2:].upper()}.pk3"
    )

    if os.path.exists(pk3_file):
        os.remove(pk3_file)

    # Open the file and write the data
    with open(pk3_file, "wb") as binary_file:
        binary_file.write(pokemon.data)


def get_rng_state_history() -> list:
    default = []
    try:
        file = read_file(context.profile.path / "soft_reset_frames.json")
        return json.loads(file) if file else default
    except SystemExit:
        raise
    except Exception:
        return default


def save_rng_state_history(data: list) -> bool:
    return bool(write_file(context.profile.path / "soft_reset_frames.json", json.dumps(data)))
