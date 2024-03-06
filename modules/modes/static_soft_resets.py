from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter, judge_encounter, log_encounter
from modules.map_data import MapFRLG, MapRSE
from modules.player import get_player_avatar
from modules.pokemon import get_opponent
from ._asserts import SavedMapLocation, assert_save_game_exists, assert_saved_on_map
from ._interface import BattleAction, BotMode
from .util import (
    soft_reset,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
)


def _get_targeted_encounter() -> tuple[MapFRLG | MapRSE, tuple[int, int], str] | None:
    if context.rom.is_frlg:
        encounters = [
            (MapFRLG.ROUTE12, (14, 70), "Snorlax"),
            (MapFRLG.ROUTE16, (31, 13), "Snorlax"),
            (MapFRLG.SEAFOAM_ISLANDS_B4F, (9, 2), "Articuno"),
            (MapFRLG.POWER_PLANT, (5, 11), "Zapdos"),
            (MapFRLG.MT_EMBER_SUMMIT, (9, 6), "Moltres"),
            (MapFRLG.CERULEAN_CAVE_B1F, (7, 12), "Mewtwo"),
            (MapFRLG.NAVEL_ROCK_BASE, (10, 15), "Lugia"),
            (MapFRLG.BIRTH_ISLAND_EXTERIOR, (15, 10), "Deoxys"),
        ]
    elif context.rom.is_emerald:
        encounters = [
            (MapRSE.NAVEL_ROCK_BOTTOM, (11, 13), "Lugia"),
            (MapRSE.SKY_PILLAR_TOP, (14, 6), "Rayquaza"),
            (MapRSE.BIRTH_ISLAND_EXTERIOR, (15, 10), "Deoxys"),
            (MapRSE.DESERT_RUINS, (8, 7), "Regirock"),
            (MapRSE.ISLAND_CAVE, (8, 7), "Regice"),
            (MapRSE.ANCIENT_TOMB, (8, 7), "Registeel"),
        ]
    else:
        encounters = [
            (MapRSE.SKY_PILLAR_TOP, (14, 6), "Rayquaza"),
            (MapRSE.DESERT_RUINS, (8, 7), "Regirock"),
            (MapRSE.ISLAND_CAVE, (8, 7), "Regice"),
            (MapRSE.ANCIENT_TOMB, (8, 7), "Registeel"),
            (MapRSE.CAVE_OF_ORIGIN_B1F, (9, 13), "Groudon/Kyogre"),
        ]

    targeted_tile = get_player_avatar().map_location_in_front
    if targeted_tile is None:
        return None

    return next(
        (
            entry
            for entry in encounters
            if entry[0] == (targeted_tile.map_group, targeted_tile.map_number)
            and entry[1] == targeted_tile.local_position
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

    def on_battle_started(self) -> BattleAction | None:
        opponent = get_opponent()
        if judge_encounter(opponent).is_of_interest:
            return handle_encounter(opponent, disable_auto_catch=True)
        log_encounter(opponent)
        return BattleAction.CustomAction

    def run(self) -> Generator:
        encounter = _get_targeted_encounter()

        assert_save_game_exists("There is no saved game. Cannot soft reset.")
        assert_saved_on_map(
            SavedMapLocation(encounter[0], encounter[1], facing=True), "The game has not been saved on this tile."
        )

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            if encounter[2] == "Groudon/Kyogre":
                yield from wait_for_task_to_start_and_finish("Task_MapNamePopup")
                context.emulator.press_button("Left")
                yield from wait_for_n_frames(2)
                yield from wait_for_task_to_start_and_finish("Task_BattleStart", "B")
            # The first cry happens before the battle starts.
            yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", button_to_press="A")

            # At the start of the next cry the opponent is fully visible.
            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")
