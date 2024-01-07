from typing import Generator

from modules.data.map import MapRSE, MapFRLG

from modules.context import context
from modules.map import get_map_objects
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from ._asserts import assert_no_auto_battle
from ._interface import BotMode, BotModeError
from ._util import navigate_to, walk_one_tile


class TowerDuoMode(BotMode):
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
        assert_no_auto_battle("This mode should not be used with auto-battle.")

        match get_player_avatar().map_group_and_number:
            # Lugia on Emerald
            case MapRSE.NAVEL_ROCK_U.value:
                pokemon_name = "Lugia"
                flag_to_check = "FLAG_CAUGHT_LUGIA"

                def path():
                    yield from navigate_to(13, 19)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(11, 14)

            # Lugia on FR/LG
            case MapFRLG.NAVEL_ROCK_B.value:
                pokemon_name = "Lugia"
                flag_to_check = "FLAG_CAUGHT_LUGIA"

                def path():
                    yield from navigate_to(12, 20)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(10, 16)

            # Ho-Oh on Emerald
            case MapRSE.NAVEL_ROCK_I.value:
                pokemon_name = "Ho-Oh"
                flag_to_check = "FLAG_CAUGHT_HO_OH"

                def path():
                    yield from navigate_to(12, 20)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(12, 10)

            # Ho-Oh on FR/LG
            case MapFRLG.NAVEL_ROCK_A.value:
                pokemon_name = "Ho-Oh"
                flag_to_check = "FLAG_CAUGHT_HO_OH"

                def path():
                    yield from navigate_to(9, 18)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(9, 12)

            case _:
                raise BotModeError("You are not on the right map.")

        if get_event_flag(flag_to_check):
            raise BotModeError(f"{pokemon_name} has already been caught.")

        while True:
            yield from path()

            while len(get_map_objects()) > 1:
                context.emulator.press_button("A")
                yield

            while "heldMovementActive" not in get_map_objects()[0].flags:
                context.emulator.press_button("B")
                yield
