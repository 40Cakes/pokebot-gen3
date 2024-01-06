from enum import Enum, auto
from typing import Generator

from modules.data.map import MapRSE, MapFRLG

from modules.context import context
from modules.map import get_map_objects
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from ._interface import BotMode, BotModeError
from ._util import follow_path


class ModeTowerDuoStates(Enum):
    INTERACT = auto()
    LEAVE_ROOM = auto()


class ModeTowerDuo(BotMode):
    @staticmethod
    def name() -> str:
        return "Tower Duo"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            allowed_maps = [MapRSE.NAVEL_ROCK_I.value, MapRSE.NAVEL_ROCK_U.value]
        else:
            allowed_maps = [MapFRLG.NAVEL_ROCK_B.value, MapFRLG.NAVEL_ROCK_A.value]
        return get_player_avatar().map_group_and_number in allowed_maps

    def run(self) -> Generator:
        match get_player_avatar().map_group_and_number:
            # Lugia on Emerald
            case MapRSE.NAVEL_ROCK_U.value:
                pokemon_name = "Lugia"
                path = [(11, 19), (14, 19), (4, 5), (5, 5), (11, 14)]
                flag_to_check = "FLAG_CAUGHT_LUGIA"
            # Lugia on FR/LG
            case MapFRLG.NAVEL_ROCK_B.value:
                pokemon_name = "Lugia"
                path = [(10, 20), (13, 20), (3, 4), (4, 4), (10, 16)]
                flag_to_check = "FLAG_CAUGHT_LUGIA"
            # Ho-Oh on Emerald
            case MapRSE.NAVEL_ROCK_I.value:
                pokemon_name = "Ho-Oh"
                path = [(12, 20), (13, 20), (4, 5), (5, 5), (12, 10)]
                flag_to_check = "FLAG_CAUGHT_HO_OH"
            # Ho-Oh on FR/LG
            case MapFRLG.NAVEL_ROCK_A.value:
                pokemon_name = "Ho-Oh"
                path = [(9, 18), (10, 18), (3, 4), (4, 4), (9, 12)]
                flag_to_check = "FLAG_CAUGHT_HO_OH"
            case _:
                raise BotModeError("You are not on the right map.")

        if get_event_flag(flag_to_check):
            raise BotModeError(f"{pokemon_name} has already been caught.")

        if context.config.battle.battle:
            raise BotModeError("This method should not be used with auto-battle enabled.")

        while True:
            yield from follow_path(path)

            while len(get_map_objects()) > 1:
                context.emulator.press_button("A")
                yield

            while "heldMovementActive" not in get_map_objects()[0].flags:
                context.emulator.press_button("B")
                yield
