from typing import Generator, Tuple
from collections import Counter

from modules.context import context
from modules.battle_state import BattleOutcome
from modules.map_data import MapFRLG, MapRSE, is_safari_map
from modules.player import get_player, get_player_avatar, TileTransitionState, AvatarFlags
from modules.pokemon_party import get_party
from modules.pokemon import get_species_by_name, get_opponent
from modules.memory import get_event_flag
from modules.menuing import StartMenuNavigator
from modules.modes.util.walking import wait_for_player_avatar_to_be_controllable
from modules.items import get_item_by_name, get_pokeblocks
from modules.modes.util.higher_level_actions import unmount_bicycle, put_pokeblock_in_feeder
from modules.safari_strategy import (
    SafariPokemon,
    SafariPokemonRSE,
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
from modules.runtime import get_sprites_path
from modules.sprites import get_regular_sprite
from modules.gui.multi_select_window import Selection, ask_for_choice_scroll, ask_for_choice
from ._interface import BotMode, BotModeError
from ._asserts import (
    SavedMapLocation,
    assert_item_exists_in_bag,
    assert_save_game_exists,
    assert_saved_on_map,
    assert_boxes_or_party_can_fit_pokemon,
)
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
)


class SafariMode(BotMode):
    def __init__(self):
        self._safari_config = get_safari_zone_config(context.rom)
        self._target_pokemon = None
        self._starting_cash = None
        self._should_reset = False
        self._should_reenter = False
        self._atleast_one_pokemon_catched = False
        self._target_caught = False
        self._use_feeder = False
        self._feeder_direction = None
        self._pokeblock_type_in_feeder = None
        self._use_repel = False
        self._money_spent_limit = 15000  # Since you can only have 30 Pokeblock, running 30 times is more than enough

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

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        """
        Handle the outcome of a battle. If the battle resulted in a catch,
        update flags to manage the re-entry or reset logic.
        """
        if outcome is BattleOutcome.Caught:
            catched_pokemon = get_opponent().species.name
            if catched_pokemon == self._target_pokemon:
                self._target_caught = True
            self._atleast_one_pokemon_catched = True
            assert_boxes_or_party_can_fit_pokemon()
        if get_safari_balls_left() < 30:
            current_cash = get_player().money
            if (self._starting_cash - current_cash > self._money_spent_limit) or (current_cash < 500):
                self._should_reset = True
            else:
                self._should_reenter = True

    def run(self) -> Generator:
        self._starting_cash = get_player().money

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
                    self._starting_cash = get_player().money
                else:
                    if is_safari_map():
                        yield from self._exit_safari_zone()
                    context.message = f"You have hit the money threshold (either you've run out of funds or spent over {self._money_spent_limit}₽), but you managed to catch at least one Pokémon during this cycle. Consider saving your game."
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
            yield from spin(stop_condition=stop_condition)
        elif mode == SafariHuntingMode.FISHING:
            yield from fish(stop_condition=stop_condition, loop=True)
        else:
            raise BotModeError(f"Error: Unknown mode {mode}.")

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
