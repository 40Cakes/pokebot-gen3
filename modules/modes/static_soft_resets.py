from dataclasses import dataclass
from typing import Generator, Optional

from modules.context import context
from modules.encounter import handle_encounter, log_encounter, EncounterInfo
from modules.map_data import MapFRLG, MapRSE
from modules.player import get_player_avatar
from modules.save_data import get_save_data
from ._asserts import SavedMapLocation, assert_save_game_exists, assert_saved_on_map
from ._interface import BattleAction, BotMode, BotModeError
from .util import (
    soft_reset,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
)


@dataclass
class Encounter:
    map: MapRSE | MapFRLG
    coordinates: tuple[int, int]
    name: str
    condition: Optional[callable] = None


def _get_targeted_encounter() -> Encounter | None:
    if context.rom.is_frlg:
        encounters = [
            Encounter(MapFRLG.ROUTE12, (14, 70), "Snorlax"),
            Encounter(MapFRLG.ROUTE16, (31, 13), "Snorlax"),
            Encounter(MapFRLG.SEAFOAM_ISLANDS_B4F, (9, 2), "Articuno"),
            Encounter(MapFRLG.POWER_PLANT, (5, 11), "Zapdos"),
            Encounter(MapFRLG.MT_EMBER_SUMMIT, (9, 6), "Moltres"),
            Encounter(MapFRLG.CERULEAN_CAVE_B1F, (7, 12), "Mewtwo"),
            Encounter(MapFRLG.NAVEL_ROCK_BASE, (10, 15), "Lugia"),
            Encounter(MapFRLG.BIRTH_ISLAND_EXTERIOR, (15, 10), "Deoxys"),
        ]
    elif context.rom.is_emerald:
        encounters = [
            Encounter(MapRSE.NAVEL_ROCK_BOTTOM, (11, 13), "Lugia"),
            Encounter(MapRSE.SKY_PILLAR_TOP, (14, 6), "Rayquaza"),
            Encounter(MapRSE.BIRTH_ISLAND_EXTERIOR, (15, 10), "Deoxys"),
            Encounter(MapRSE.DESERT_RUINS, (8, 7), "Regirock"),
            Encounter(MapRSE.ISLAND_CAVE, (8, 7), "Regice"),
            Encounter(MapRSE.ANCIENT_TOMB, (8, 7), "Registeel"),
        ]
    else:
        encounters = [
            Encounter(MapRSE.SKY_PILLAR_TOP, (14, 6), "Rayquaza"),
            Encounter(MapRSE.DESERT_RUINS, (8, 7), "Regirock"),
            Encounter(MapRSE.ISLAND_CAVE, (8, 7), "Regice"),
            Encounter(MapRSE.ANCIENT_TOMB, (8, 7), "Registeel"),
            Encounter(MapRSE.CAVE_OF_ORIGIN_B1F, (9, 13), "Groudon/Kyogre"),
            Encounter(
                MapRSE.ROUTE119,
                (31, 6),
                "Kecleon",
                lambda: not get_save_data().get_event_flag(
                    "HIDE_ROUTE_119_KECLEON_1" if context.rom.is_emerald else "HIDE_KECLEON_ROUTE119_1"
                ),
            ),
        ]

    targeted_tile = get_player_avatar().map_location_in_front
    if targeted_tile is None:
        return None

    return next(
        (
            entry
            for entry in encounters
            if entry.map == (targeted_tile.map_group, targeted_tile.map_number)
            and entry.coordinates == targeted_tile.local_position
        ),
        None,
    )


class StaticSoftResetsMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Static Soft Resets"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        if encounter.is_of_interest:
            return handle_encounter(encounter, disable_auto_catch=True)
        log_encounter(encounter)
        return BattleAction.CustomAction

    def run(self) -> Generator:
        encounter = _get_targeted_encounter()

        assert_save_game_exists("There is no saved game. Cannot soft reset.")
        assert_saved_on_map(
            SavedMapLocation(encounter.map, encounter.coordinates, facing=True),
            "The game has not been saved on this tile.",
        )

        if encounter.condition is not None and not encounter.condition():
            raise BotModeError(f"This {encounter.name} has already been encountered.")

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            if encounter.name == "Groudon/Kyogre":
                yield from wait_for_task_to_start_and_finish("Task_MapNamePopup")
                context.emulator.press_button("Left")
                yield from wait_for_n_frames(2)
                yield from wait_for_task_to_start_and_finish("Task_BattleStart", "B")
            # The first cry happens before the battle starts.
            yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", button_to_press="A")

            # At the start of the next cry the opponent is fully visible.
            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")
