from typing import Generator

from modules.context import context
from modules.encounter import EncounterValue, handle_encounter, judge_encounter, log_encounter
from modules.gui.multi_select_window import Selection, ask_for_choice
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_event_var, get_game_state
from modules.player import get_player, get_player_avatar
from modules.pokemon import get_opponent
from modules.region_map import FlyDestinationFRLG, FlyDestinationRSE
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from modules.tasks import get_global_script_context
from ._asserts import SavedMapLocation, assert_save_game_exists, assert_saved_on_map
from ._interface import BattleAction, BotMode, BotModeError
from ._util import (
    RanOutOfRepels,
    apply_repel,
    ensure_facing_direction,
    fly_to,
    follow_path,
    deprecated_navigate_to_on_current_map,
    replenish_repel,
    soft_reset,
    wait_for_player_avatar_to_be_standing_still,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
    walk_one_tile,
)


def _get_allowed_starting_map() -> MapFRLG | MapRSE | None:
    if context.rom.is_frlg:
        return MapFRLG.ONE_ISLAND_POKEMON_CENTER_1F
    elif context.rom.is_emerald:
        if get_player().gender == "female":
            return MapRSE.LITTLEROOT_TOWN_MAYS_HOUSE_2F
        else:
            return MapRSE.LITTLEROOT_TOWN_BRENDANS_HOUSE_2F
    else:
        # No R/S yet
        return None


def _get_repel_steps_remaining():
    return get_event_var("REPEL_STEP_COUNT")


class RoamerResetMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Roamer (Reset)"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_emerald and get_event_var("LITTLEROOT_HOUSES_STATE_MAY") != 3:
            return False

        return get_player_avatar().map_group_and_number == _get_allowed_starting_map()

    def __init__(self):
        super().__init__()
        self._should_reset = False
        self._ran_out_of_repels = False

    def on_repel_effect_ended(self) -> None:
        try:
            replenish_repel()
        except RanOutOfRepels:
            self._ran_out_of_repels = True

    def on_battle_started(self) -> BattleAction | None:
        # This excludes `EncounterValue.Roamer` which should not lead to a notification being
        # triggered. _All_ encounters in this mode should be roamers.
        opponent = get_opponent()
        if judge_encounter(opponent) in (EncounterValue.Shiny, EncounterValue.CustomFilterMatch):
            return handle_encounter(opponent, disable_auto_catch=True)
        self._should_reset = True
        log_encounter(opponent)
        return BattleAction.CustomAction

    def run(self) -> Generator:
        assert_save_game_exists("There is no saved game. Cannot soft reset.")

        if context.rom.is_frlg:
            location_error = "The game has not been saved while standing in the Pokemon Net Center on One Island."
            roamer_level = 50
            highest_encounter_level = 6
        else:
            location_error = "The game has not been saved while standing on the top floor of the player's house."
            roamer_level = 40
            highest_encounter_level = 13
        assert_saved_on_map(SavedMapLocation(_get_allowed_starting_map()), error_message=location_error)

        save_data = get_save_data()
        saved_party = save_data.get_party()

        if saved_party[0].is_egg:
            raise BotModeError("The first Pokémon in your party must not be an egg in order for Repel to work.")

        if saved_party[0].level > roamer_level:
            raise BotModeError(
                f"The first Pokémon in your party has to be level {roamer_level} or lower in order for Repel to work."
            )

        if saved_party[0].level <= highest_encounter_level:
            raise BotModeError(
                "The first Pokémon in your party has to be at least level "
                f"{highest_encounter_level + 1} in order for Repel to work."
            )

        if save_data.get_item_bag().number_of_repels == 0:
            raise BotModeError("You do not have any repels in your item bag. Go and get some first!")

        has_good_ability = not saved_party[0].is_egg and saved_party[0].ability.name in ("Illuminate", "Arena Trap")

        if context.rom.is_frlg:
            yield from self.run_frlg(has_good_ability)
        elif context.rom.is_emerald:
            yield from self.run_emerald(has_good_ability)
        else:
            context.message = "Ruby/Sapphire are not supported by this mode."
            context.set_manual_mode()

    def run_emerald(self, has_good_ability: bool):
        roamer_choice = ask_for_choice(
            [
                Selection("Latias", get_sprites_path() / "pokemon" / "normal" / "Latias.png"),
                Selection("Latios", get_sprites_path() / "pokemon" / "normal" / "Latios.png"),
            ],
            window_title="Select a Pokémon...",
        )
        if roamer_choice is None:
            return

        while True:
            self._should_reset = False
            self._ran_out_of_repels = False
            context.emulator.reset_held_buttons()

            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            yield from wait_for_player_avatar_to_be_standing_still()

            if get_player().gender == "female":
                yield from deprecated_navigate_to_on_current_map(1, 2)
            else:
                yield from deprecated_navigate_to_on_current_map(7, 2)

            yield from walk_one_tile("Up")

            yield from wait_until_task_is_active("Task_HandleMultichoiceInput", "B")
            if roamer_choice == "Latios":
                yield
                context.emulator.press_button("Down")
                yield
                yield

            while get_global_script_context().is_active:
                context.emulator.press_button("A")
                yield

            yield from wait_for_player_avatar_to_be_standing_still()

            if get_player().gender == "female":
                yield from deprecated_navigate_to_on_current_map(2, 8)
            else:
                yield from deprecated_navigate_to_on_current_map(8, 8)

            yield from walk_one_tile("Down")

            # Cut scene where you get the National Dex
            if get_event_var("DEX_UPGRADE_JOHTO_STARTER_STATE") == 1:
                script_name = "LittlerootTown_ProfessorBirchsLab_EventScript_UpgradeToNationalDex"
                while script_name not in get_global_script_context().stack:
                    context.emulator.press_button("B")
                    yield
                while script_name in get_global_script_context().stack:
                    context.emulator.press_button("B")
                    yield
                yield
                yield
                yield from deprecated_navigate_to_on_current_map(6, 12)
                yield from walk_one_tile("Down")

            # Fly to Slateport City, as the most efficient place to do this seems to be between
            # there and Route 110
            yield from fly_to(FlyDestinationRSE.SlateportCity)

            # Walk to Slateport's border with Route 110
            yield from deprecated_navigate_to_on_current_map(15, 0)

            def inner_loop():
                if _get_repel_steps_remaining() <= 0:
                    yield from apply_repel()

                # Walk up to tall grass, spin, return
                yield from walk_one_tile("Up")
                yield from follow_path([(15, 97), (14, 97)])
                directions = ["Down", "Right", "Up", "Left"]
                for index in range(42 if has_good_ability else 62):
                    yield from ensure_facing_direction(directions[index % 4])
                yield from follow_path([(15, 97), (15, 99)])
                yield from walk_one_tile("Down")

                # Run to Battle Tent, enter, leave, go back to Route 110
                # This is necessary because the game saves the last 3 locations the player
                # has been in and avoids them, so we need additional map transitions.
                yield from follow_path([(17, 0), (17, 13), (10, 13)])
                yield from walk_one_tile("Up")
                yield from walk_one_tile("Down")
                yield from follow_path([(17, 13), (17, 0), (15, 0)])

            while not self._should_reset and not self._ran_out_of_repels:
                for _ in inner_loop():
                    if self._should_reset or self._ran_out_of_repels:
                        break
                    yield
            if self._ran_out_of_repels:
                context.message = "Soft resetting after running out of repels..."
                continue

            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry")

    def run_frlg(self, has_good_ability: bool):
        while True:
            self._should_reset = False
            self._ran_out_of_repels = False
            context.emulator.reset_held_buttons()

            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            yield from wait_for_player_avatar_to_be_standing_still()

            yield from deprecated_navigate_to_on_current_map(14, 6)
            yield from ensure_facing_direction("Right")

            yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")

            while get_global_script_context().is_active:
                context.emulator.press_button("B")
                yield
            yield

            # Leave the building
            while get_player_avatar().map_group_and_number != MapFRLG.ONE_ISLAND:
                yield from follow_path([(14, 9), (9, 9)])
                yield from walk_one_tile("Down")

            # Walk to the ferry terminal and up to the sailor
            yield from follow_path([(14, 12), (12, 12), (12, 18)])
            yield from walk_one_tile("Down")
            yield from follow_path([(8, 5)])

            # Talk to the sailor
            while get_game_state() == GameState.OVERWORLD:
                context.emulator.press_button("A")
                yield

            # Wait for the ferry cutscene to finish
            while get_game_state() != GameState.OVERWORLD:
                yield

            # Fly to Pallet Town, as the most efficient place to do this seems to be between there
            # and Route 1
            yield from fly_to(FlyDestinationFRLG.PalletTown)

            # Go to the north of the map, just before Route 1 starts
            yield from walk_one_tile("Right")
            yield from deprecated_navigate_to_on_current_map(12, 0)

            def inner_loop():
                if _get_repel_steps_remaining() <= 0:
                    yield from apply_repel()

                yield from walk_one_tile("Up")
                directions = ["Left", "Down", "Right", "Up"]
                for index in range(18 if has_good_ability else 36):
                    yield from ensure_facing_direction(directions[index % 4])
                yield from walk_one_tile("Down")

                yield from follow_path([(12, 8), (15, 8)])
                yield from walk_one_tile("Up")
                yield from walk_one_tile("Down")
                yield from follow_path([(12, 8), (12, 0)])

            while not self._should_reset and not self._ran_out_of_repels:
                for _ in inner_loop():
                    if self._should_reset or self._ran_out_of_repels:
                        break
                    yield
            if self._ran_out_of_repels:
                context.message = "Soft resetting after running out of repels..."
                continue

            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry")
