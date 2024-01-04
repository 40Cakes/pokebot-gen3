from typing import Generator

from modules.data.map import MapRSE, MapFRLG

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.player import get_player_avatar
from modules.pokemon import get_opponent
from modules.save_data import get_save_data
from ._interface import BotMode, BotModeError
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    wait_until_task_is_no_longer_active,
    wait_until_task_is_active,
)


def _get_targeted_encounter() -> tuple[tuple[int, int], tuple[int, int], str] | None:
    if context.rom.is_frlg:
        encounters = [
            (MapFRLG.ROUTE_12.value, (14, 70), "Snorlax"),
            (MapFRLG.ROUTE_16.value, (31, 13), "Snorlax"),
            (MapFRLG.SEAFOAM_ISLANDS_D.value, (9, 2), "Articuno"),
            (MapFRLG.POWER_PLANT.value, (5, 11), "Zapdos"),
            (MapFRLG.MT_EMBER_E.value, (9, 6), "Moltres"),
            (MapFRLG.CERULEAN_CAVE_B.value, (7, 12), "Mewtwo"),
            (MapFRLG.NAVEL_ROCK_B.value, (10, 15), "Lugia"),
            (MapFRLG.BIRTH_ISLAND.value, (15, 10), "Deoxys"),
        ]
    elif context.rom.is_emerald:
        encounters = [
            (MapRSE.NAVEL_ROCK_U.value, (11, 13), "Lugia"),
            (MapRSE.SKY_PILLAR_G.value, (14, 6), "Rayquaza"),
            (MapRSE.BIRTH_ISLAND.value, (15, 10), "Deoxys"),
            (MapRSE.DESERT_RUINS.value, (8, 7), "Regirock"),
            (MapRSE.ISLAND_CAVE.value, (8, 7), "Regice"),
            (MapRSE.ANCIENT_TOMB.value, (8, 7), "Registeel"),
        ]
    else:
        encounters = [
            (MapRSE.SKY_PILLAR_G.value, (14, 6), "Rayquaza"),
            (MapRSE.DESERT_RUINS.value, (8, 7), "Regirock"),
            (MapRSE.ISLAND_CAVE.value, (8, 7), "Regice"),
            (MapRSE.ANCIENT_TOMB.value, (8, 7), "Registeel"),
        ]

    targeted_tile = get_player_avatar().map_location_in_front
    for entry in encounters:
        if entry[0] == (targeted_tile.map_group, targeted_tile.map_number) and entry[1] == targeted_tile.local_position:
            return entry

    return None


class StaticSoftResetsMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Static Soft Resets"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    def disable_default_battle_handler(self) -> bool:
        return True

    def run(self) -> Generator:
        encounter = _get_targeted_encounter()

        save_data = get_save_data()
        if save_data is None:
            raise BotModeError("There is no saved game. Cannot soft reset.")

        # Verify that the game has been saved in the right location.
        if encounter[0] != (save_data.sections[1][4], save_data.sections[1][5]):
            raise BotModeError("The game has not been saved on the correct map.")

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            # The first cry happens before the battle starts.
            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")
            yield from wait_until_task_is_no_longer_active("Task_DuckBGMForPokemonCry", "A")

            # At the start of the next cry the opponent is fully visible.
            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")

            encounter_pokemon(get_opponent())
