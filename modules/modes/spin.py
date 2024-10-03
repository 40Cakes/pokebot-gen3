from typing import Generator

from modules.player import get_player_avatar
from ._interface import BotMode
from .util import apply_white_flute_if_available, spin


class SpinMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Spin"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def run(self) -> Generator:
        yield from apply_white_flute_if_available()
        yield from spin()
