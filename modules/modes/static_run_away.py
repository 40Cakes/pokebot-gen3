from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter
from modules.map import get_map_objects
from modules.map_data import MapFRLG, MapRSE
from modules.memory import get_event_flag
from modules.player import get_player_avatar
from modules.pokemon import get_opponent
from ._interface import BattleAction, BotMode, BotModeError
from .util import (
    follow_path,
    deprecated_navigate_to_on_current_map,
    wait_for_player_avatar_to_be_controllable,
    wait_for_script_to_start_and_finish,
    wait_for_task_to_start_and_finish,
    walk_one_tile,
)


class StaticRunAway(BotMode):
    @staticmethod
    def name() -> str:
        return "Static Run Away"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            allowed_maps = [
                MapRSE.NAVEL_ROCK_TOP,
                MapRSE.NAVEL_ROCK_BOTTOM,
                MapRSE.ISLAND_CAVE,
                MapRSE.ANCIENT_TOMB,
                MapRSE.DESERT_RUINS,
                MapRSE.SOUTHERN_ISLAND_INTERIOR,
                MapRSE.MARINE_CAVE_END,
                MapRSE.TERRA_CAVE_END,
                MapRSE.SKY_PILLAR_TOP,
                MapRSE.FARAWAY_ISLAND_ENTRANCE,
            ]
        else:
            allowed_maps = [MapFRLG.NAVEL_ROCK_BASE, MapFRLG.NAVEL_ROCK_SUMMIT]
        return get_player_avatar().map_group_and_number in allowed_maps

    def on_battle_started(self) -> BattleAction | None:
        return handle_encounter(get_opponent(), disable_auto_catch=True, disable_auto_battle=True)

    def run(self) -> Generator:
        match get_player_avatar().map_group_and_number:
            # Lugia on Emerald
            case MapRSE.NAVEL_ROCK_BOTTOM:
                pokemon_name = "Lugia"
                flag_to_check = "CAUGHT_LUGIA"

                def path():
                    yield from deprecated_navigate_to_on_current_map(13, 19)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from deprecated_navigate_to_on_current_map(11, 14)

            # Lugia on FR/LG
            case MapFRLG.NAVEL_ROCK_BASE:
                pokemon_name = "Lugia"
                flag_to_check = "CAUGHT_LUGIA"

                def path():
                    yield from deprecated_navigate_to_on_current_map(12, 20)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from deprecated_navigate_to_on_current_map(10, 16)

            # Ho-Oh on Emerald
            case MapRSE.NAVEL_ROCK_TOP:
                pokemon_name = "Ho-Oh"
                flag_to_check = "CAUGHT_HO_OH"

                def path():
                    yield from deprecated_navigate_to_on_current_map(12, 20)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from deprecated_navigate_to_on_current_map(12, 10)

            # Ho-Oh on FR/LG
            case MapFRLG.NAVEL_ROCK_SUMMIT:
                pokemon_name = "Ho-Oh"
                flag_to_check = "CAUGHT_HO_OH"

                def path():
                    yield from deprecated_navigate_to_on_current_map(9, 18)
                    yield from walk_one_tile("Right")
                    yield from walk_one_tile("Left")
                    yield from walk_one_tile("Right")
                    yield from deprecated_navigate_to_on_current_map(9, 12)

            # Regice on Emerald
            case MapRSE.ISLAND_CAVE:
                pokemon_name = "Regice"
                flag_to_check = "DEFEATED_REGICE"

                def path():
                    yield from deprecated_navigate_to_on_current_map(8, 11)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(8, 8)

            # Registeel on Emerald
            case MapRSE.ANCIENT_TOMB:
                pokemon_name = "Registeel"
                flag_to_check = "DEFEATED_REGISTEEL"

                def path():
                    yield from deprecated_navigate_to_on_current_map(8, 11)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(8, 8)

            # Regirock on Emerald
            case MapRSE.DESERT_RUINS:
                pokemon_name = "Regirock"
                flag_to_check = "DEFEATED_REGIROCK"

                def path():
                    yield from deprecated_navigate_to_on_current_map(8, 11)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(8, 8)

            # Lati@s on Emerald
            case MapRSE.SOUTHERN_ISLAND_INTERIOR:
                pokemon_name = "Lati@s"
                flag_to_check = "DEFEATED_LATIAS_OR_LATIOS"

                def path():
                    yield from deprecated_navigate_to_on_current_map(13, 18)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(13, 12)
                    yield from wait_for_script_to_start_and_finish("SouthernIsland_Interior_EventScript_Lati", "A")

            # Kyorge in Emerald
            case MapRSE.MARINE_CAVE_END:
                pokemon_name = "Kyogre"
                flag_to_check = "DEFEATED_KYOGRE"

                def path():
                    yield from deprecated_navigate_to_on_current_map(20, 4)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(9, 26)

            # Groudon in Emerald
            case MapRSE.TERRA_CAVE_END:
                pokemon_name = "Groudon"
                flag_to_check = "DEFEATED_GROUDON"

                def path():
                    yield from deprecated_navigate_to_on_current_map(5, 4)
                    yield from walk_one_tile("Down")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(17, 26)

            # Rayquaza on Emerald
            case MapRSE.SKY_PILLAR_TOP:
                pokemon_name = "Rayquaza"
                flag_to_check = "DEFEATED_RAYQUAZA"

                def path():
                    yield from deprecated_navigate_to_on_current_map(16, 15)
                    yield from walk_one_tile("Up")
                    yield from walk_one_tile("Up")
                    yield from deprecated_navigate_to_on_current_map(14, 7)

            # Mew on Emerald
            case MapRSE.FARAWAY_ISLAND_ENTRANCE:
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

            yield from wait_for_player_avatar_to_be_controllable("B")
