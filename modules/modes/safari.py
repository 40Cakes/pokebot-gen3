import random
from collections import Counter
from typing import Generator, Tuple

from modules.battle_state import BattleOutcome
from modules.context import context
from modules.encounter import EncounterInfo
from modules.files import get_profile_flags, set_profile_flag
from modules.gui.multi_select_window import Selection, ask_for_choice_scroll, ask_for_choice
from modules.items import get_item_by_name, get_pokeblocks
from modules.map_data import MapFRLG, MapRSE, is_safari_map
from modules.memory import get_event_flag
from modules.menuing import StartMenuNavigator
from modules.modes.util.higher_level_actions import unmount_bicycle, put_pokeblock_in_feeder
from modules.modes.util.walking import wait_for_player_avatar_to_be_controllable
from modules.player import get_player, get_player_avatar, TileTransitionState
from modules.pokemon import get_opponent
from modules.pokemon_party import get_party
from modules.runtime import get_sprites_path
from modules.safari_strategy import (
    SafariPokemon,
    SafariHuntingMode,
    SafariHuntingObject,
    RSESafariStrategy,
    get_safari_pokemon,
    get_navigation_path,
    get_safari_balls_left,
    get_safari_zone_config,
    get_pokeblock_type_counts,
    get_lowest_feel_pokeblock_by_type,
)
from modules.sprites import get_regular_sprite
from ._asserts import (
    SavedMapLocation,
    assert_item_exists_in_bag,
    assert_save_game_exists,
    assert_saved_on_map,
    assert_boxes_or_party_can_fit_pokemon,
)
from ._interface import BotMode, BotModeError
from .util import (
    spin,
    fish,
    soft_reset,
    navigate_to,
    apply_repel,
    repel_is_active,
    ensure_facing_direction,
    wait_for_script_to_start_and_finish,
    wait_for_player_avatar_to_be_standing_still,
    wait_for_unique_rng_value,
    apply_white_flute_if_available,
    register_key_item,
    advance_rng_sequence,
    wait_for_n_frames,
)

# See `SafariMode._hesitate()`.
_DELAY_FREE_RUN_FLAG = "safari_delay_free_run_used"

# On Emerald, this mode benefits a lot from not having to soft reset, due
# to RNG shenanigans. Thus, we want to warn the user if they try to start
# the mode without having a lot of cash -- but we don't want to make it
# _mandatory_ to have a lot. After all, it will still work, but the user
# will get lots of duplicate encounters and delays. So once a session we
# may display this warning, but from the second activation of the mode
# onwards we won't say anything.

# That's enough for 20 entries -- should be enough, given that each entry
# _should_ result in either a Shiny, or at least a failed attempt at catching
# a shiny.
_recommended_cash: int = 10_000
_displayed_warning_about_too_little_cash: bool = False


class SafariMode(BotMode):
    def __init__(self):
        self._safari_config = get_safari_zone_config(context.rom)
        self._target_pokemon = None
        self._should_reset = False
        self._should_reenter = False
        self._atleast_one_pokemon_catched = False
        self._target_caught = False
        self._use_feeder = False
        self._feeder_direction = None
        self._pokeblock_type_in_feeder = None
        self._use_repel = False

        # See `_hesitate()`.
        self._should_hesitate = False
        self._is_delay_free_run = False
        self._has_battled_since_last_hesitation = False

    @staticmethod
    def name() -> str:
        return "Safari"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_group_and_number in (
            MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE,
            MapRSE.ROUTE121_SAFARI_ZONE_ENTRANCE,
        )

    def on_safari_zone_timeout(self):
        return True

    def on_battle_started(self, encounter: EncounterInfo | None) -> None:
        if self._is_delay_free_run:
            # The next run will no longer be delay-free, so that it cannot end up repeating this run's encounters.
            set_profile_flag(_DELAY_FREE_RUN_FLAG)
        return None

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        """
        Handle the outcome of a battle. If the battle resulted in a catch,
        update flags to manage the re-entry or reset logic.
        """
        self._has_battled_since_last_hesitation = True
        if outcome is BattleOutcome.Caught:
            catched_pokemon = get_opponent().species.name
            if catched_pokemon == self._target_pokemon:
                self._target_caught = True
            self._atleast_one_pokemon_catched = True
            assert_boxes_or_party_can_fit_pokemon()
        if get_safari_balls_left() < 30:
            current_cash = get_player().money
            if current_cash < 500:
                self._should_reset = True
            else:
                self._should_reenter = True

    def run(self) -> Generator:
        assert_save_game_exists("There is no saved game. Cannot start Safari mode. Please save your game.")

        assert_boxes_or_party_can_fit_pokemon()
        assert_boxes_or_party_can_fit_pokemon(check_in_saved_game=True)

        assert_saved_on_map(
            SavedMapLocation(self._safari_config["map"]),
            self._safari_config["save_message"],
        )

        pokemon_choices = []
        safari_pokemon_list = self._safari_config["safari_pokemon_list"]

        pokemon_choice = self._select_pokemon(safari_pokemon_list)
        if pokemon_choice is None:
            context.set_manual_mode()
            yield
            return

        target = get_safari_pokemon(pokemon_choice)
        self._target_pokemon = target.value.species.name
        self._check_mode_requirement(target.value.mode, target.value.hunting_object)
        self._check_map_requirement(target.value.map_location)

        global _displayed_warning_about_too_little_cash
        if (
            context.rom.is_emerald
            and not _displayed_warning_about_too_little_cash
            and get_player().money < _recommended_cash
        ):
            _displayed_warning_about_too_little_cash = True
            raise BotModeError(
                f"You don't have a lot of cash. We recommend you carry at least ${_recommended_cash:,} for best performance. Select mode again to continue anyway."
            )
        else:
            context.message = ""

        pokeblocks = get_pokeblocks()
        type_counts = Counter(p.type for p in pokeblocks)

        if any(count >= 2 for count in type_counts.values()):
            feeder_direction = RSESafariStrategy.get_facing_direction_for_position(target.value.tile_location)
            self._feeder_direction = feeder_direction
            if feeder_direction:
                yield from self._ask_use_feeder()
                if self._use_feeder:
                    yield from self._select_pokeblock_type()

        if target.value.mode != SafariHuntingMode.FISHING:
            if not self._ask_use_repel():
                context.set_manual_mode()
                yield
                return

        if target.value.hunting_object:
            yield from register_key_item(get_item_by_name(target.value.hunting_object))

        # See `_hesitate()`.
        if context.rom.is_emerald:
            self._should_hesitate = True
            self._is_delay_free_run = _DELAY_FREE_RUN_FLAG not in get_profile_flags()

        while True:
            if self._target_caught:
                if is_safari_map():
                    yield from self._exit_safari_zone()
                if not context.config.battle.save_after_catching:
                    context.message = f"{self._target_pokemon} has been caught ! Save your game !"
                else:
                    context.message = f"{self._target_pokemon} has been caught !"
                context.set_manual_mode()
                break
            elif self._should_reset:
                if not self._atleast_one_pokemon_catched:
                    yield from self._soft_reset()
                else:
                    if is_safari_map():
                        yield from self._exit_safari_zone()
                    context.message = f"You have run out of funds, but you managed to catch at least one Pokémon during this cycle. Consider saving your game."
                    context.set_manual_mode()
                    break
            elif self._should_reenter:
                yield from self._re_enter_safari_zone()

            yield from self._start_safari_hunt(target)

    def _start_safari_hunt(self, safari_pokemon: SafariPokemon) -> Generator:
        current_cash = get_player().money
        if current_cash < 500:
            raise BotModeError("You do not have enough cash to enter the Safari Zone.")

        yield from navigate_to(self._safari_config["map"], self._safari_config["entrance_tile"])
        yield from ensure_facing_direction(self._safari_config["facing_direction"])

        context.emulator.hold_button(self._safari_config["facing_direction"])
        for _ in range(10):
            yield
        context.emulator.release_button(self._safari_config["facing_direction"])
        yield
        yield from wait_for_script_to_start_and_finish(self._safari_config["ask_script"], "A")
        yield from wait_for_script_to_start_and_finish(self._safari_config["enter_script"], "A")

        if context.rom.is_frlg:
            yield from wait_for_player_avatar_to_be_controllable()
        else:
            while (
                get_player_avatar().local_coordinates != (32, 35)
                or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
            ):
                yield

        yield from self._navigate_and_hunt(
            safari_pokemon.value.map_location, safari_pokemon.value.tile_location, safari_pokemon.value.mode
        )

    def _re_enter_safari_zone(self) -> Generator:
        """Handles re-entry into the Safari Zone."""
        if is_safari_map():
            yield from self._exit_safari_zone()
        self._should_reenter = False
        return

    def _exit_safari_zone(self) -> Generator:
        """Handles re-entry into the Safari Zone."""
        yield from StartMenuNavigator("RETIRE").step()
        yield from wait_for_script_to_start_and_finish(self._safari_config["exit_script"], "A")
        yield from wait_for_player_avatar_to_be_standing_still()

    def _navigate_and_hunt(
        self, target_map: MapFRLG | MapRSE, tile_location: Tuple[int, int], mode: SafariHuntingMode
    ) -> Generator:

        def stop_condition():
            return self._should_reset or self._should_reenter

        def is_at_entrance_door():
            return self._safari_config["is_at_entrance_door"]()

        if is_at_entrance_door():
            yield from wait_for_player_avatar_to_be_standing_still()
        elif context.rom.is_rse and self._safari_config.get("is_script_active", lambda: False)():
            while is_at_entrance_door() or self._safari_config["is_script_active"]():
                yield
            yield from wait_for_player_avatar_to_be_standing_still()

        yield from self._hesitate(255)

        path = get_navigation_path(target_map, tile_location)

        for map_group, coords in path:
            yield from navigate_to(map_group, coords)

        if self._use_feeder:
            index, pokeblock = get_lowest_feel_pokeblock_by_type(self._pokeblock_type_in_feeder)
            if pokeblock is not None:
                yield from ensure_facing_direction(self._feeder_direction)
                yield from put_pokeblock_in_feeder(pokeblock)

        if mode in (SafariHuntingMode.SPIN, SafariHuntingMode.SURF):
            if self._use_repel and not repel_is_active():
                yield from apply_repel()
            yield from unmount_bicycle()
            yield from apply_white_flute_if_available()
        elif mode != SafariHuntingMode.FISHING:
            raise BotModeError(f"Error: Unknown mode {mode}.")

        yield from self._hesitate(255)

        def stop_condition_or_battle_ended() -> bool:
            return stop_condition() or (self._should_hesitate and self._has_battled_since_last_hesitation)

        while not stop_condition():
            if self._has_battled_since_last_hesitation:
                yield from self._hesitate(15)
            if mode == SafariHuntingMode.FISHING:
                yield from fish(stop_condition=stop_condition_or_battle_ended, loop=True)
            else:
                yield from spin(stop_condition=stop_condition_or_battle_ended)

    def _hesitate(self, maximum_frames: int) -> Generator:
        """
        Emerald seeds its RNG with 0 on every boot, so after a soft reset the RNG always starts out
        within a narrow range of values (depending on how long it took to get back into the overworld.)

        While walking or spinning, and in battles, the game makes a varying number of RNG calls that
        depend on the RNG's current value (for example, a Pokémon that is generated and then blocked by
        Repel.) Because of that, two runs that start a few values apart tend to drift into _the exact
        same_ RNG state after a while. As the bot's inputs only depend on what happens in the game, the
        two runs are identical from then on, and every encounter is a 'clone' of one from an earlier run.

        To prevent that, we hesitate for a random number of frames at a few points, like a human player
        would: a long hesitation after entering the Safari Zone and again when arriving at the hunting
        spot, and a short one after each battle (because battles and, with Repel, spinning could make two
        runs converge again.) The long hesitations only happen once per entry, which lasts a long time
        because neither spinning nor fishing uses up steps.

        None of this is necessary if there is nothing that we could converge with:

        - Ruby, Sapphire and FR/LG seed their RNG differently, so runs are not limited to a narrow range.
        - The very first run has no previous run to repeat. So it stays delay-free until the next soft
          reset. Its first encounter sets a profile flag, so that no later run is delay-free (it might
          start from the same RNG range and could end up repeating this one.)

        :param maximum_frames: Maximum number of frames to wait.
        """
        self._has_battled_since_last_hesitation = False
        if not self._should_hesitate or self._is_delay_free_run:
            return

        hesitation = random.randint(0, maximum_frames)
        if context.config.cheats.random_soft_reset_rng:
            advance_rng_sequence(hesitation)
        else:
            yield from wait_for_n_frames(hesitation)

    def _check_mode_requirement(self, mode: SafariHuntingMode, object: SafariHuntingObject) -> bool:
        match mode:
            case SafariHuntingMode.SURF:
                if not (get_event_flag("BADGE05_GET") and get_party().has_pokemon_with_move("Surf")):
                    raise BotModeError(
                        f"Cannot start mode {mode.value}. You're missing Badge 05 or you don't have any Pokémon with Surf"
                    )
            case SafariHuntingMode.FISHING:
                assert_item_exists_in_bag(
                    object,
                    error_message=f"You need to own the {object} in order to hunt this Pokémon in the Safari Zone.",
                    check_in_saved_game=True,
                )
            case _:
                return True

    def _check_map_requirement(self, map: MapFRLG | MapRSE) -> bool:
        match map:
            case MapRSE.SAFARI_ZONE_NORTHWEST:
                assert_item_exists_in_bag(
                    "Mach Bike",
                    error_message=f"You need to own the Mach Bike in order to hunt this Pokémon in the Safari Zone.",
                    check_in_saved_game=True,
                )
            case MapRSE.SAFARI_ZONE_NORTH:
                assert_item_exists_in_bag(
                    "Acro Bike",
                    error_message=f"You need to own the Acro Bike in order to hunt this Pokémon in the Safari Zone.",
                    check_in_saved_game=True,
                )
            case _:
                return True

    def _soft_reset(self) -> Generator:
        """Handles soft resetting if cash difference exceeds the limit."""
        yield from soft_reset()
        yield from wait_for_unique_rng_value()
        self._should_reset = False
        # From now on, we might end up repeating an earlier run. See `_hesitate()`.
        self._is_delay_free_run = False
        for _ in range(5):
            yield

    def _select_pokemon(self, safari_pokemon_list):
        pokemon_choices = [
            Selection(safari_pokemon.value.species.name, get_regular_sprite(safari_pokemon.value.species))
            for safari_pokemon in safari_pokemon_list.available_pokemon()
        ]

        return ask_for_choice_scroll(
            choices=pokemon_choices,
            window_title="Select a Pokemon to hunt...",
            button_width=172,
            button_height=170,
            options_per_row=3,
        )

    def _ask_use_feeder(self) -> Generator:
        feeder_mode = ask_for_choice(
            [
                Selection("Use Feeder", get_sprites_path() / "other" / "Feeder.png"),
                Selection("No Feeder", get_sprites_path() / "other" / "Feeder.png"),
            ],
            window_title="Use feeder?",
        )

        if feeder_mode is None:
            context.set_manual_mode()
            yield
            return

        if feeder_mode == "Use Feeder":
            self._use_feeder = True
        yield

    def _select_pokeblock_type(self) -> Generator:
        type_counts = get_pokeblock_type_counts()
        pokeblock_choices = [
            Selection(f"{type_name} ×{count}", get_sprites_path() / "pokeblocks" / f"{type_name.lower()}.png")
            for type_name, count in type_counts
        ]

        pokeblock_type_choice = ask_for_choice_scroll(
            choices=pokeblock_choices,
            window_title="Select a Pokéblock Type...",
            button_width=172,
            button_height=170,
            options_per_row=3,
        )

        if pokeblock_type_choice is None:
            context.set_manual_mode()
            yield
            return

        self._pokeblock_type_in_feeder = pokeblock_type_choice.split()[0]
        yield

    def _ask_use_repel(self) -> bool:
        choice = ask_for_choice(
            [
                Selection("Use Repel", get_sprites_path() / "items" / "Repel.png"),
                Selection("No Repel", get_sprites_path() / "other" / "No Repel.png"),
            ],
            window_title="Use Repel?",
        )
        if choice == "Use Repel":
            self._use_repel = True
        return choice is not None
