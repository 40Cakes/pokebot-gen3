from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.map import get_map_objects
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from ._interface import BotMode, BotModeError
from ._util import follow_path


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
        if not context.rom.is_emerald:  # TODO add RS support
            raise BotModeError("Only Emerald is supported, RS coming soon.")

        match get_player_avatar().map_group_and_number:
            case MapRSE.MARINE_CAVE_A.value:
                pokemon_name = "Kyogre"
                flags_to_check = ("FLAG_DEFEATED_KYOGRE", "FLAG_LEGENDARY_BATTLE_COMPLETED")
                allowed_coordinates_rect = ((5, 26), (17, 27))
                path = [
                    (14, 27),
                    (18, 27),
                    (18, 14),
                    (14, 14),
                    (14, 4),
                    (20, 4),
                    (20, 5),  # Door outside
                    (14, 2),
                    (14, 1),  # Door back inside
                    (14, 4),
                    (14, 14),
                    (18, 14),
                    (18, 27),
                    (9, 27),
                    (9, 26),
                ]
            case MapRSE.TERRA_CAVE_A.value:
                pokemon_name = "Groudon"
                flags_to_check = ("FLAG_DEFEATED_GROUDON", "FLAG_LEGENDARY_BATTLE_COMPLETED")
                allowed_coordinates_rect = ((11, 24), (20, 27))
                path = [
                    (11, 26),
                    (7, 26),
                    (7, 12),
                    (9, 12),
                    (9, 4),
                    (5, 4),
                    (5, 5),  # Door outside
                    (14, 2),
                    (14, 1),  # Door back inside
                    (9, 4),
                    (9, 15),
                    (7, 15),
                    (7, 26),
                    (17, 26),
                ]
            case MapRSE.SKY_PILLAR_G.value:
                pokemon_name = "Rayquaza"
                flags_to_check = ("FLAG_DEFEATED_RAYQUAZA",)
                allowed_coordinates_rect = ((13, 7), (15, 12))
                path = [
                    (14, 11),
                    (12, 11),
                    (12, 15),
                    (16, 15),
                    (16, 14),  # Door outside
                    (10, 2),
                    (10, 1),  # Door back inside
                    (12, 15),
                    (12, 11),
                    (14, 11),
                    (14, 7),
                ]
            case _:
                raise BotModeError("You are not on the right map.")

        for flag in flags_to_check:
            if get_event_flag(flag):
                raise BotModeError(f"{pokemon_name} has already been caught or defeated.")

        x, y = get_player_avatar().local_coordinates
        if (
            allowed_coordinates_rect[0][0] > x
            or allowed_coordinates_rect[1][0] < x
            or allowed_coordinates_rect[0][1] > y
            or allowed_coordinates_rect[1][1] < y
        ):
            raise BotModeError(f"You are too far away from {pokemon_name}. Get a bit closer.")

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
