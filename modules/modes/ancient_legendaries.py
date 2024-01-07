from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.map import get_map_objects
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from ._asserts import assert_no_auto_battle
from ._interface import BotMode, BotModeError
from ._util import follow_path, navigate_to, walk_one_tile


class AncientLegendariesMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Ancient Legendaries"

    @staticmethod
    def is_selectable() -> bool:
        player = get_player_avatar()
        allowed_maps = [MapRSE.MARINE_CAVE_A.value, MapRSE.TERRA_CAVE_A.value, MapRSE.SKY_PILLAR_G.value]
        return context.rom.is_rse and player.map_group_and_number in allowed_maps

    def run(self) -> Generator:
        assert_no_auto_battle("This mode should not be used with auto-battle.")

        if not context.rom.is_emerald:  # TODO add RS support
            raise BotModeError("Only Emerald is supported, RS coming soon.")

        match get_player_avatar().map_group_and_number:
            case MapRSE.MARINE_CAVE_A.value:
                pokemon_name = "Kyogre"
                flags_to_check = ("FLAG_DEFEATED_KYOGRE", "FLAG_LEGENDARY_BATTLE_COMPLETED")
                def path():
                    yield from navigate_to(20, 4)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(9, 26)
            case MapRSE.TERRA_CAVE_A.value:
                pokemon_name = "Groudon"
                flags_to_check = ("FLAG_DEFEATED_GROUDON", "FLAG_LEGENDARY_BATTLE_COMPLETED")
                def path():
                    yield from navigate_to(5, 4)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(17, 26)
            case MapRSE.SKY_PILLAR_G.value:
                pokemon_name = "Rayquaza"
                flags_to_check = ("FLAG_DEFEATED_RAYQUAZA",)
                def path():
                    yield from navigate_to(16, 15)
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(14, 7)
            case _:
                raise BotModeError("You are not on the right map.")

        for flag in flags_to_check:
            if get_event_flag(flag):
                raise BotModeError(f"{pokemon_name} has already been caught or defeated.")

        while True:
            yield from path()

            while len(get_map_objects()) > 1:
                context.emulator.press_button("A")
                yield

            while "heldMovementActive" not in get_map_objects()[0].flags:
                context.emulator.press_button("B")
                yield
