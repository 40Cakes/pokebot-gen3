from typing import Generator

from modules.data.map import MapRSE, MapFRLG

from modules.context import context
from modules.map import get_map_objects
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from ._interface import BotMode, BotModeError, BattleAction
from ._util import (
    wait_for_task_to_start_and_finish,
    navigate_to,
    walk_one_tile,
    follow_path,
    wait_for_script_to_start_and_finish,
)


class StaticRunAway(BotMode):
    @staticmethod
    def name() -> str:
        return "Static Run Away"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            allowed_maps = [
                MapRSE.NAVEL_ROCK_I.value,
                MapRSE.NAVEL_ROCK_U.value,
                MapRSE.ISLAND_CAVE.value,
                MapRSE.ANCIENT_TOMB.value,
                MapRSE.DESERT_RUINS.value,
                MapRSE.SOUTHERN_ISLAND_A.value,
                MapRSE.MARINE_CAVE_A.value,
                MapRSE.TERRA_CAVE_A.value,
                MapRSE.SKY_PILLAR_G.value,
                MapRSE.FARAWAY_ISLAND.value,
            ]
        else:
            allowed_maps = [MapFRLG.NAVEL_ROCK_B.value, MapFRLG.NAVEL_ROCK_A.value]
        return get_player_avatar().map_group_and_number in allowed_maps

    def on_battle_started(self) -> BattleAction | None:
        return BattleAction.RunAway

    def run(self) -> Generator:
        match get_player_avatar().map_group_and_number:
            # Lugia on Emerald
            case MapRSE.NAVEL_ROCK_U.value:
                pokemon_name = "Lugia"
                flag_to_check = "CAUGHT_LUGIA"

                def path():
                    yield from navigate_to(13, 19)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(11, 14)

            # Lugia on FR/LG
            case MapFRLG.NAVEL_ROCK_B.value:
                pokemon_name = "Lugia"
                flag_to_check = "CAUGHT_LUGIA"

                def path():
                    yield from navigate_to(12, 20)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(10, 16)

            # Ho-Oh on Emerald
            case MapRSE.NAVEL_ROCK_I.value:
                pokemon_name = "Ho-Oh"
                flag_to_check = "CAUGHT_HO_OH"

                def path():
                    yield from navigate_to(12, 20)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(12, 10)

            # Ho-Oh on FR/LG
            case MapFRLG.NAVEL_ROCK_A.value:
                pokemon_name = "Ho-Oh"
                flag_to_check = "CAUGHT_HO_OH"

                def path():
                    yield from navigate_to(9, 18)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from navigate_to(9, 12)

            # Regice on Emerald
            case MapRSE.ISLAND_CAVE.value:
                pokemon_name = "Regice"
                flag_to_check = "DEFEATED_REGICE"

                def path():
                    yield from navigate_to(8, 11)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(8, 8)

            # Registeel on Emerald
            case MapRSE.ANCIENT_TOMB.value:
                pokemon_name = "Registeel"
                flag_to_check = "DEFEATED_REGISTEEL"

                def path():
                    yield from navigate_to(8, 11)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(8, 8)

            # Regirock on Emerald
            case MapRSE.DESERT_RUINS.value:
                pokemon_name = "Regirock"
                flag_to_check = "DEFEATED_REGIROCK"

                def path():
                    yield from navigate_to(8, 11)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(8, 8)

            # Lati@s on Emerald
            case MapRSE.SOUTHERN_ISLAND_A.value:
                pokemon_name = "Lati@s"
                flag_to_check = "DEFEATED_LATIAS_OR_LATIOS"

                def path():
                    yield from navigate_to(13, 18)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(13, 12)
                    context.emulator.press_button("A")
                    yield from wait_for_script_to_start_and_finish("Common_EventScript_LegendaryFlewAway", "B")

            # Kyorge in Emerald
            case MapRSE.MARINE_CAVE_A.value:
                pokemon_name = "Kyogre"
                flag_to_check = "DEFEATED_KYOGRE"

                def path():
                    yield from navigate_to(20, 4)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(9, 26)

            # Groudon in Emerald
            case MapRSE.TERRA_CAVE_A.value:
                pokemon_name = "Groudon"
                flag_to_check = "DEFEATED_GROUDON"

                def path():
                    yield from navigate_to(5, 4)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(17, 26)

            # Rayquaza on Emerald
            case MapRSE.SKY_PILLAR_G.value:
                pokemon_name = "Rayquaza"
                flag_to_check = "DEFEATED_RAYQUAZA"

                def path():
                    yield from navigate_to(16, 15)
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from navigate_to(14, 7)

            # Mew on Emerald
            case MapRSE.FARAWAY_ISLAND.value:
                pokemon_name = "Mew"
                flag_to_check = "DEFEATED MEW"

                def path():
                    yield from walk_one_tile("Up")
                    yield from follow_path([(12, 16), (16, 16), (16, 13)])
                    context.emulator.press_button("A")
                    yield from wait_for_task_to_start_and_finish("Task_WaitForFadeAndEnableScriptCtx", "B")
                    yield from wait_for_script_to_start_and_finish("Common_EventScript_LegendaryFlewAway", "B")
                    yield from walk_one_tile("Down")
                    yield from follow_path([(16, 16), (12, 16), (12, 19)])
                    yield from walk_one_tile("Down")

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
