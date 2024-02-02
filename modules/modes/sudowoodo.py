from typing import Generator

from modules.data.map import MapRSE

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.player import get_player_avatar
from modules.pokemon import get_opponent
from ._asserts import (
    assert_save_game_exists,
    assert_saved_on_map,
    assert_registered_item,
    SavedMapLocation,
)
from ._interface import BotMode, BattleAction
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
    wait_for_task_to_start_and_finish,
)


def _get_targeted_encounter() -> tuple[tuple[int, int], tuple[int, int], str] | None:
    if context.rom.is_emerald:
        encounters = [
            (MapRSE.BATTLE_FRONTIER_E.value, (54, 62), "Sudowoodo"),
        ]
    else:
        encounters = []

    targeted_tile = get_player_avatar().map_location_in_front
    for entry in encounters:
        if entry[0] == (targeted_tile.map_group, targeted_tile.map_number) and entry[1] == targeted_tile.local_position:
            return entry

    return None


class SudowoodoMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Sudowoodo"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    def on_battle_started(self) -> BattleAction | None:
        return BattleAction.CustomAction

    def run(self) -> Generator:
        encounter = _get_targeted_encounter()

        assert_save_game_exists("This is no saved game. Cannot soft reset.")
        assert_saved_on_map(
            SavedMapLocation(encounter[0], encounter[1], facing=True),
            "The game has not been saved on this tile.",
        )
        assert_registered_item(
            ["Wailmer Pail"],
            "You need to register the Wailmer Pail for the Select button.",
        )

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            # use registered item
            yield from wait_for_task_to_start_and_finish(
                "Task_WateringBerryTreeAnim_Continue", button_to_press="Select"
            )
            yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", button_to_press="B")
            yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", button_to_press="A")
            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")

            encounter_pokemon(get_opponent())
