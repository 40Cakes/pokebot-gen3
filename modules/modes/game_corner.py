from typing import Generator

from modules.data.map import MapFRLG
from modules.context import context
from modules.encounter import encounter_pokemon
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from modules.pokemon import get_party
from modules.player import get_player, get_player_avatar
from modules.tasks import task_is_active
from ._interface import BotMode, BotModeError
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
    wait_for_task_to_start_and_finish,
    wait_for_n_frames,
)


def _get_targeted_encounter() -> tuple[tuple[int, int], tuple[int, int], str] | None:
    encounters = [
        (MapFRLG.CELADON_CITY_P.value, (4, 3), "Game Corner"),
    ]

    targeted_tile = get_player_avatar().map_location_in_front

    for entry in encounters:
        if entry[0] == (targeted_tile.map_group, targeted_tile.map_number) and entry[1] == targeted_tile.local_position:
            return entry

    return None


class GameCornerMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Game Corner"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    def run(self) -> Generator:
        coincase = get_player().coins
        if coincase < 180:
            raise BotModeError("You don't have enough coins to buy anything.")

        game_corner_choice = ask_for_choice(
            [
                Selection(
                    "Abra",
                    get_sprites_path() / "pokemon" / "normal" / "Abra.png",
                    coincase >= 180,
                ),
                Selection(
                    "Clefairy",
                    get_sprites_path() / "pokemon" / "normal" / "Clefairy.png",
                    coincase >= 500,
                ),
                Selection(
                    "Dratini",
                    get_sprites_path() / "pokemon" / "normal" / "Dratini.png",
                    coincase >= 2800,
                ),
                Selection(
                    "Scyther",
                    get_sprites_path() / "pokemon" / "normal" / "Scyther.png",
                    coincase >= 5500,
                ),
                Selection(
                    "Porygon",
                    get_sprites_path() / "pokemon" / "normal" / "Porygon.png",
                    coincase >= 9999,
                ),
            ],
            window_title="Select which one to buy...",
        )
        if game_corner_choice is None:
            return

        encounter = _get_targeted_encounter()

        save_data = get_save_data()
        if save_data is None:
            raise BotModeError("There is no saved game. Cannot soft reset.")

        if encounter[0] != (save_data.sections[1][4], save_data.sections[1][5]):
            raise BotModeError("The targeted encounter is not in the current map. Cannot soft reset.")

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            if len(get_party()) >= 6:
                raise BotModeError("This mode requires at least one empty party slot, but your party is full.")

            # spam A until choice appears
            if task_is_active("Task_MultichoiceMenu_HandleInput") == False:
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "A")
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "A")
                yield from wait_until_task_is_active("Task_MultichoiceMenu_HandleInput")
                yield from wait_for_n_frames(5)

            match game_corner_choice:
                case "Abra":
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Clefairy":
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Dratini":
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Scyther":
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Porygon":
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    context.emulator.press_button("Down")
                    yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")

            # accept the pokemon
            yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "A")
            # don't rename pokemon
            yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "B")

            # log the encounter
            if context.config.cheats.fast_check_starters:
                encounter_pokemon(get_party()[len(get_party()) - 1])
            else:
                yield from StartMenuNavigator("POKEMON").step()
                yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

                encounter_pokemon(get_party()[len(get_party()) - 1])
