import random
from typing import Generator

from modules.data.map import MapFRLG, MapRSE

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.menuing import StartMenuNavigator, PokemonPartyMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon import get_party
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from ._asserts import assert_save_game_exists, assert_saved_on_map, SavedMapLocation
from ._interface import BotMode, BotModeError, BattleAction
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    wait_for_task_to_start_and_finish,
    wait_until_task_is_not_active,
    wait_until_task_is_active,
    ensure_facing_direction,
)


class StartersMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Starters"

    @staticmethod
    def is_selectable() -> bool:
        player_avatar = get_player_avatar()
        if context.rom.is_frlg:
            return player_avatar.map_group_and_number == (4, 3)
        if context.rom.is_rse:
            return player_avatar.map_group_and_number in [(0, 16), (1, 4)]

    def on_battle_started(self) -> BattleAction | None:
        return BattleAction.CustomAction

    def run(self) -> Generator:
        assert_save_game_exists("There is no saved game. Cannot soft reset.")

        if context.rom.is_frlg:
            assert_saved_on_map(
                [
                    SavedMapLocation(MapFRLG.PALLET_TOWN_D, (8, 4), facing=True),
                    SavedMapLocation(MapFRLG.PALLET_TOWN_D, (9, 4), facing=True),
                    SavedMapLocation(MapFRLG.PALLET_TOWN_D, (10, 4), facing=True),
                ],
                error_message="The game has not been saved while standing in front of one of the starter Poké balls.",
            )
            yield from self.run_frlg()
        elif context.rom.is_rse:
            assert_saved_on_map(
                [
                    # Hoenn Starter Bag
                    SavedMapLocation(MapRSE.ROUTE_101, (7, 14), facing=True),
                    # Johto Starters (on table)
                    SavedMapLocation(MapRSE.LITTLEROOT_TOWN_E, (8, 4), facing=True),
                    SavedMapLocation(MapRSE.LITTLEROOT_TOWN_E, (9, 4), facing=True),
                    SavedMapLocation(MapRSE.LITTLEROOT_TOWN_E, (10, 4), facing=True),
                ],
                error_message="The game has not been saved in front of the starter Pokémon bag (for Hoenn starters) or in front of one of the starter Poké balls (for Johto starters.)",
            )

            if get_save_data().get_map_group_and_number() == MapRSE.ROUTE_101.value:
                yield from self.run_rse_hoenn()
            else:
                yield from self.run_rse_johto()

    def run_frlg(self) -> Generator:
        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            yield from ensure_facing_direction("Up")

            # Wait for and confirm the first question (the 'Do you choose ...')
            while len(get_party()) == 0:
                context.emulator.press_button("A")
                yield

            # Wait for and say no to the second question (the 'Do you want to give ... a nickname')
            yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", button_to_press="B")

            # If the respective 'cheat' is enabled, check the Pokemon immediately instead of 'genuinely' looking
            # at the summary screen
            if context.config.cheats.fast_check_starters:
                encounter_pokemon(get_party()[0])
                continue

            # Wait for the rival to pick up their starter
            yield from wait_until_task_is_active("Task_Fanfare", button_to_press="B")

            # Wait for the main menu to pop up
            yield from wait_until_task_is_active("Task_StartMenuHandleInput", button_to_press="Start")

            # Spam 'A' until we see the summary screen
            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")

            encounter_pokemon(get_party()[0])

    def run_rse_hoenn(self) -> Generator:
        # Set up: Ask for starter choice because we cannot deduce that from the player location.
        starter_choice = ask_for_choice(
            [
                Selection("Treecko", get_sprites_path() / "pokemon" / "normal" / "Treecko.png"),
                Selection("Torchic", get_sprites_path() / "pokemon" / "normal" / "Torchic.png"),
                Selection("Mudkip", get_sprites_path() / "pokemon" / "normal" / "Mudkip.png"),
                Selection("Random", get_sprites_path() / "pokemon" / "normal" / "Unown.png"),
            ],
            window_title="Select a starter...",
        )
        if starter_choice is None:
            return

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)

            # Starter bag can be accessed from the right or from the bottom, make sure we are looking
            # at it in either case.
            avatar = get_player_avatar()
            if avatar.local_coordinates == (8, 14):
                yield from ensure_facing_direction("Left")
            else:
                yield from ensure_facing_direction("Up")

            # Open bag
            if context.rom.is_rs:
                yield from wait_until_task_is_active("Task_StarterChoose2", "A")
            else:
                yield from wait_until_task_is_active("Task_HandleStarterChooseInput", "A")

            starter = starter_choice
            if starter == "Random":
                starter = random.choice(["Treecko", "Torchic", "Mudkip"])

            # Select the correct starter
            if starter == "Treecko":
                yield
                context.emulator.press_button("Left")
                yield
            elif starter == "Mudkip":
                yield
                context.emulator.press_button("Right")
                yield

            yield from wait_for_unique_rng_value()

            # Wait for Pokemon cry in selection menu
            yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", "A")

            # Wait for Pokemon cry of opponent Poochyena
            yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", "A")

            # Wait for Pokemon cry of starter Pokemon (after which the sprite is fully visible)
            yield from wait_for_task_to_start_and_finish("Task_DuckBGMForPokemonCry", "A")

            encounter_pokemon(get_party()[0])

    def run_rse_johto(self):
        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)

            if len(get_party()) >= 6:
                raise BotModeError("This mode requires at least one empty party slot, but your party is full.")

            yield from wait_for_unique_rng_value()

            yield from ensure_facing_direction("Up")

            # Wait for and confirm the first question (the 'Do you choose ...')
            yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", button_to_press="A")

            # Wait for and say no to the second question (the 'Do you want to give ... a nickname')
            yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", button_to_press="B")

            # If the respective 'cheat' is enabled, check the Pokemon immediately instead of 'genuinely' looking
            # at the summary screen
            if context.config.cheats.fast_check_starters:
                encounter_pokemon(get_party()[len(get_party()) - 1])
                continue

            # Wait for the rival to pick up their starter
            yield from wait_until_task_is_not_active("ScriptMovement_MoveObjects", button_to_press="B")

            # Navigate to the summary screen to check for shininess
            yield from StartMenuNavigator("POKEMON").step()
            yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

            encounter_pokemon(get_party()[len(get_party()) - 1])
