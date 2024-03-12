from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.map_data import MapFRLG
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon import get_party
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from modules.tasks import task_is_active
from ._asserts import SavedMapLocation, assert_save_game_exists, assert_saved_on_map, assert_empty_slot_in_party
from ._interface import BotMode, BotModeError
from .util import (
    soft_reset,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
)


class GameCornerMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Game Corner"

    @staticmethod
    def is_selectable() -> bool:
        if not context.rom.is_frlg:
            return False
        targeted_tile = get_player_avatar().map_location_in_front
        return targeted_tile in MapFRLG.CELADON_CITY_GAME_CORNER_PRIZE_ROOM and targeted_tile.local_position == (
            4,
            3,
        )

    def run(self) -> Generator:
        assert_save_game_exists("There is no saved game. Cannot soft reset.")

        if context.rom.is_fr:
            choices = [("Abra", 180), ("Clefairy", 500), ("Dratini", 2800), ("Scyther", 5500), ("Porygon", 9999)]
        elif context.rom.is_lg:
            choices = [("Abra", 120), ("Clefairy", 750), ("Pinsir", 2500), ("Dratini", 4600), ("Porygon", 6500)]
        else:
            raise BotModeError("This mode is not supported on RSE.")

        coins_owned = get_save_data().get_player().coins
        if coins_owned < choices[0][1]:
            raise BotModeError("In your saved game, you don't have enough coins to buy anything.")

        available_options = []
        for pokemon, price_in_coins in choices:
            selection = Selection(
                pokemon,
                get_sprites_path() / "pokemon" / "normal" / f"{pokemon}.png",
                coins_owned >= price_in_coins,
            )
            available_options.append(selection)
        game_corner_choice = ask_for_choice(
            available_options,
            window_title="Select which one to buy...",
        )
        if game_corner_choice is None:
            return

        assert_saved_on_map(
            SavedMapLocation(MapFRLG.CELADON_CITY_GAME_CORNER_PRIZE_ROOM, (4, 3), facing=True),
            "Please save in-game, facing the counter before starting this mode.",
        )

        assert_empty_slot_in_party("This mode requires at least one empty party slot, but your party is full.")

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            # Spam A until choice appears
            if not task_is_active("Task_MultichoiceMenu_HandleInput"):
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "A")
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "A")
                yield from wait_until_task_is_active("Task_MultichoiceMenu_HandleInput")
                yield from wait_for_n_frames(5)

            match game_corner_choice:
                case "Abra":
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Clefairy":
                    for _ in range(1):
                        context.emulator.press_button("Down")
                        yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Pinsir":
                    for _ in range(2):
                        context.emulator.press_button("Down")
                        yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Dratini":
                    if context.rom.is_fr:
                        for _ in range(2):
                            context.emulator.press_button("Down")
                            yield from wait_for_n_frames(2)
                    if context.rom.is_lg:
                        for _ in range(3):
                            context.emulator.press_button("Down")
                            yield from wait_for_n_frames(2)
                case "Scyther":
                    for _ in range(3):
                        context.emulator.press_button("Down")
                        yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                case "Porygon":
                    for _ in range(4):
                        context.emulator.press_button("Down")
                        yield from wait_for_n_frames(2)
                    yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")

            # Accept the Pokémon
            yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "A")
            # don't rename pokemon
            yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "B")

            # log the encounter
            yield from StartMenuNavigator("POKEMON").step()
            yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

            handle_encounter(get_party()[-1], disable_auto_catch=True, do_not_log_battle_action=True)
