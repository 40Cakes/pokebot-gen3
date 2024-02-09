from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter, judge_encounter, log_encounter
from modules.map_data import MapRSE
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


class SudowoodoMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Sudowoodo"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_emerald:
            targeted_tile = get_player_avatar().map_location_in_front
            return targeted_tile in MapRSE.BATTLE_FRONTIER_OUTSIDE_EAST and targeted_tile.local_position == (54, 62)
        else:
            return False

    def on_battle_started(self) -> BattleAction | None:
        opponent = get_opponent()
        if judge_encounter(opponent).is_of_interest:
            return handle_encounter(get_opponent(), disable_auto_catch=True)
        else:
            log_encounter(opponent)
            return BattleAction.CustomAction

    def run(self) -> Generator:
        assert_save_game_exists("This is no saved game. Cannot soft reset.")
        assert_saved_on_map(
            SavedMapLocation(MapRSE.BATTLE_FRONTIER_OUTSIDE_EAST, (54, 62), facing=True),
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
