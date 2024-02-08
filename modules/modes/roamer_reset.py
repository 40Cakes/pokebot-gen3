from typing import Generator

from modules.data.map import MapFRLG, MapRSE

from modules.context import context
from modules.encounter import handle_encounter, log_encounter, judge_encounter, EncounterValue
from modules.gui.multi_select_window import ask_for_choice, Selection
from modules.map import get_map_objects
from modules.memory import (
    get_game_state,
    GameState,
    get_event_var,
)
from modules.player import get_player, get_player_avatar
from modules.pokemon import get_move_by_name, get_opponent
from modules.region_map import FlyDestinationRSE, FlyDestinationFRLG
from modules.roamer import get_roamer
from modules.runtime import get_sprites_path
from modules.save_data import get_save_data
from modules.tasks import get_global_script_context
from ._asserts import assert_save_game_exists, assert_saved_on_map, SavedMapLocation
from ._interface import BotMode, BotModeError, BattleAction
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    navigate_to,
    follow_path,
    ensure_facing_direction,
    walk_one_tile,
    wait_until_task_is_active,
    apply_repel,
    replenish_repel,
    RanOutOfRepels,
    fly_to,
)


def _get_allowed_starting_map() -> tuple[int, int]:
    if context.rom.is_frlg:
        return MapFRLG.ONE_ISLAND_A.value
    elif context.rom.is_emerald:
        if get_player().gender == "female":
            return MapRSE.LITTLEROOT_TOWN_D.value
        else:
            return MapRSE.LITTLEROOT_TOWN_B.value
    else:
        # No R/S yet
        return -1, -1


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
        opponent = get_opponent()
        # This excludes `EncounterValue.Roamer` which should not lead to a notification being
        # triggered. _All_ encounters in this mode should be roamers.
        if judge_encounter(opponent) in (EncounterValue.Shiny, EncounterValue.CustomFilterMatch):
            return handle_encounter(opponent, disable_auto_catch=True)
        else:
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
                f"The first Pokémon in your party has to be at least level {highest_encounter_level + 1} in order for Repel to work."
            )

        if save_data.get_item_bag().number_of_repels == 0:
            raise BotModeError("You do not have any repels in your item bag. Go and get some first!")

        flying_pokemon_index = None
        move_fly = get_move_by_name("Fly")
        for index in range(len(saved_party)):
            for learned_move in saved_party[index].moves:
                if learned_move is not None and learned_move.move == move_fly:
                    flying_pokemon_index = index
                    break
        if flying_pokemon_index is None:
            raise BotModeError("None of your party Pokémon know the move Fly. Please teach it to someone.")

        has_good_ability = not saved_party[0].is_egg and saved_party[0].ability.name in ("Illuminate", "Arena Trap")

        if context.rom.is_frlg:
            yield from self.run_frlg(flying_pokemon_index, has_good_ability)
        elif context.rom.is_emerald:
            yield from self.run_emerald(flying_pokemon_index, has_good_ability)
        else:
            context.message = "Ruby/Sapphire are not supported by this mode."
            context.set_manual_mode()

    def run_emerald(self, flying_pokemon_index: int, has_good_ability: bool):
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

            while "heldMovementFinished" not in get_map_objects()[0].flags:
                yield

            if get_player().gender == "female":
                yield from navigate_to(1, 2)
            else:
                yield from navigate_to(7, 2)

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

            while "heldMovementFinished" not in get_map_objects()[0].flags or "frozen" in get_map_objects()[0].flags:
                yield

            if get_player().gender == "female":
                yield from navigate_to(2, 8)
            else:
                yield from navigate_to(8, 8)

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
                yield from navigate_to(6, 12)
                yield from walk_one_tile("Down")

            # Fly to Slateport City, as the most efficient place to do this seems to be between
            # there and Route 110
            yield from fly_to(FlyDestinationRSE.SlateportCity)

            # Walk to Slateport's border with Route 110
            yield from navigate_to(15, 0)

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
                context.message = "Soft resetting after running out of repels."
                continue

            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry")

    def run_frlg(self, flying_pokemon_index: int, has_good_ability: bool):
        while True:
            self._should_reset = False
            self._ran_out_of_repels = False
            context.emulator.reset_held_buttons()

            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            while "heldMovementFinished" not in get_map_objects()[0].flags:
                yield

            yield from navigate_to(14, 6)
            yield from ensure_facing_direction("Right")

            yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")

            while get_roamer() is None:
                context.emulator.press_button("B")
                yield

            # Leave the building
            while get_player_avatar().map_group_and_number != MapFRLG.ONE_ISLAND.value:
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
            yield from navigate_to(12, 0)

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
                context.message = "Soft resetting after running out of repels."
                continue

            yield from wait_until_task_is_active("Task_DuckBGMForPokemonCry")
