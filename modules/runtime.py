import sys
from pathlib import Path


def is_bundled_app() -> bool:
    """
    :return: Whether the bot is running in a bundled app (i.e. something built by pyinstaller.)
    """
    return getattr(sys, "frozen", False)


def is_virtualenv() -> bool:
    """
    :return: Whether we are running in a virtualenv (True) or in the global Python environment (False)
    """
    return sys.prefix != sys.base_prefix


def get_base_path() -> Path:
    """
    :return: A `Path` object to the base directory of the bot (where `pokebot.py` or `pokebot.exe`
             are located.)
    """
    if is_bundled_app():
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent


def get_data_path() -> Path:
    """
    :return: A `Path` object to the `data` directory. Not that in pyinstaller distributions, this
             might be in a different place, hence this separate function.
    """
    return Path(__file__).parent / "data"


def get_sprites_path() -> Path:
    """
    :return: A `Path` object to the `sprites` directory. Not that in pyinstaller distributions, this
             might be in a different place, hence this separate function.
    """
    return Path(__file__).parent.parent / "sprites"
