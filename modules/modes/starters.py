import random
from typing import Generator

from modules.context import context
from modules.encounter import handle_encounter, EncounterInfo
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.map_data import MapFRLG, MapRSE
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.modes.util.walking import navigate_to
from modules.player import get_player_avatar
from modules.pokemon import get_party
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from ._asserts import SavedMapLocation, assert_save_game_exists, assert_saved_on_map
from ._interface import BattleAction, BotMode, BotModeError
from .util import (
    ensure_facing_direction,
    soft_reset,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
    wait_until_task_is_not_active,
)
from ..battle_state import battle_is_active, get_main_battle_callback, EncounterType


def run_frlg() -> Generator:
    starter_choice = ask_for_choice(
        [
            Selection("Bulbasaur", get_sprites_path() / "pokemon" / "normal" / "Bulbasaur.png"),
            Selection("Charmander", get_sprites_path() / "pokemon" / "normal" / "Charmander.png"),
            Selection("Squirtle", get_sprites_path() / "pokemon" / "normal" / "Squirtle.png"),
            Selection("Random", get_sprites_path() / "pokemon" / "normal" / "Unown (qm).png"),
        ],
        window_title="Select a starter...",
    )
    if starter_choice is None:
        return

    while context.bot_mode != "Manual":
        yield from soft_reset(mash_random_keys=True)
        starter = starter_choice
        if starter == "Random":
            starter = random.choice(["Bulbasaur", "Charmander", "Squirtle"])
        match starter:
            case "Bulbasaur":
                yield from navigate_to(map=MapFRLG.PALLET_TOWN_PROFESSOR_OAKS_LAB, coordinates=(8, 5))
            case "Charmander":
                yield from navigate_to(map=MapFRLG.PALLET_TOWN_PROFESSOR_OAKS_LAB, coordinates=(10, 5))
            case "Squirtle":
                yield from navigate_to(map=MapFRLG.PALLET_TOWN_PROFESSOR_OAKS_LAB, coordinates=(9, 5))
        yield from ensure_facing_direction("Up")
        yield from wait_for_unique_rng_value()

        # Wait for and confirm the first question (the 'Do you choose ...')
        while len(get_party()) == 0:
            context.emulator.press_button("A")
            yield

        # Wait for and say no to the second question (the 'Do you want to give ... a nickname')
        yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", button_to_press="B")

        # Wait for the rival to pick up their starter
        yield from wait_until_task_is_active("Task_Fanfare", button_to_press="B")

        # Wait for the main menu to pop up
        yield from wait_until_task_is_active("Task_StartMenuHandleInput", button_to_press="Start")

        # Spam 'A' until we see the summary screen
        yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry", button_to_press="A")

        handle_encounter(
            EncounterInfo.create(get_party()[0], EncounterType.Gift),
            disable_auto_catch=True,
            do_not_log_battle_action=True,
        )


def run_rse_hoenn() -> Generator:
    # Set up: Ask for starter choice because we cannot deduce that from the player location.
    starter_choice = ask_for_choice(
        [
            Selection("Treecko", get_sprites_path() / "pokemon" / "normal" / "Treecko.png"),
            Selection("Torchic", get_sprites_path() / "pokemon" / "normal" / "Torchic.png"),
            Selection("Mudkip", get_sprites_path() / "pokemon" / "normal" / "Mudkip.png"),
            Selection("Random", get_sprites_path() / "pokemon" / "normal" / "Unown (qm).png"),
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

        # Wait until the starter Pokémon has been sent out into battle before resetting.
        # The Pokémon is already generated as soon as the battle starts, but to make it
        # more like a real person is playing, we wait until the Pokémon is actually
        # _visible_.
        first_turn_callback = "TryDoEventsBeforeFirstTurn" if context.rom.is_emerald else "BattleBeginFirstTurn"
        battle_has_begun = False
        while True:
            if not battle_has_begun and get_main_battle_callback() == first_turn_callback:
                battle_has_begun = True
            elif battle_has_begun and get_main_battle_callback() != first_turn_callback:
                break

            context.emulator.press_button("A")
            yield

        handle_encounter(
            EncounterInfo.create(get_party()[0], EncounterType.Gift),
            do_not_log_battle_action=True,
            disable_auto_catch=True,
        )


def run_rse_johto():
    starter_choice = ask_for_choice(
        [
            Selection("Chikorita", get_sprites_path() / "pokemon" / "normal" / "Chikorita.png"),
            Selection("Cyndaquil", get_sprites_path() / "pokemon" / "normal" / "Cyndaquil.png"),
            Selection("Totodile", get_sprites_path() / "pokemon" / "normal" / "Totodile.png"),
            Selection("Random", get_sprites_path() / "pokemon" / "normal" / "Unown (qm).png"),
        ],
        window_title="Select a starter...",
    )
    if starter_choice is None:
        return

    while context.bot_mode != "Manual":
        yield from soft_reset(mash_random_keys=True)
        starter = starter_choice
        if starter == "Random":
            starter = random.choice(["Chikorita", "Cyndaquil", "Totodile"])
        match starter:
            case "Chikorita":
                yield from navigate_to(map=MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB, coordinates=(10, 5))
            case "Cyndaquil":
                yield from navigate_to(map=MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB, coordinates=(8, 5))
            case "Totodile":
                yield from navigate_to(map=MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB, coordinates=(9, 5))

        if len(get_party()) >= 6:
            raise BotModeError("This mode requires at least one empty party slot, but your party is full.")

        yield from ensure_facing_direction("Up")

        yield from wait_for_unique_rng_value()

        # Wait for and confirm the first question (the 'Do you choose ...')
        yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", button_to_press="A")

        # Wait for and say no to the second question (the 'Do you want to give ... a nickname')
        yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", button_to_press="B")

        yield from wait_until_task_is_not_active("Task_Fanfare", "B")
        yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "A")

        yield from wait_for_n_frames(2)
        context.emulator.press_button("A")

        # Navigate to the summary screen to check for shininess
        yield from StartMenuNavigator("POKEMON").step()
        yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

        handle_encounter(
            EncounterInfo.create(get_party()[-1], EncounterType.Gift),
            disable_auto_catch=True,
            do_not_log_battle_action=True,
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

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | None:
        return BattleAction.CustomAction

    def run(self) -> Generator:
        assert_save_game_exists("There is no saved game. Cannot soft reset.")

        if context.rom.is_frlg:
            assert_saved_on_map(
                [SavedMapLocation(MapFRLG.PALLET_TOWN_PROFESSOR_OAKS_LAB)],
                error_message="The game has not been saved while standing in front of one of the starter Poké balls.",
            )
            yield from run_frlg()
        elif context.rom.is_rse:
            assert_saved_on_map(
                [
                    # Hoenn Starter Bag
                    SavedMapLocation(MapRSE.ROUTE101, (7, 14), facing=True),
                    # Johto Starters (on table)
                    SavedMapLocation(MapRSE.LITTLEROOT_TOWN_PROFESSOR_BIRCHS_LAB),
                ],
                error_message=(
                    "The game has not been saved in front of the starter Pokémon bag (for Hoenn starters) "
                    "or in front of one of the starter Poké balls (for Johto starters.)"
                ),
            )

            if get_save_data().get_map_group_and_number() == MapRSE.ROUTE101:
                yield from run_rse_hoenn()
            else:
                yield from run_rse_johto()
