from typing import Generator, Tuple

from modules.context import context
from modules.player import get_player_avatar
from modules.battle_state import BattleOutcome
from modules.map_data import MapFRLG
from modules.player import get_player, get_player_avatar
from modules.pokemon_party import get_party
from modules.memory import get_event_flag
from modules.menuing import StartMenuNavigator
from modules.modes.util.walking import wait_for_player_avatar_to_be_controllable
from modules.items import get_item_by_name
from modules.safari_strategy import (
    SafariPokemon,
    SafariHuntingMode,
    SafariHuntingObject,
    get_safari_pokemon,
    get_navigation_path,
    get_safari_balls_left,
)
from modules.runtime import get_sprites_path
from modules.gui.multi_select_window import Selection, ask_for_choice_scroll, ask_for_choice
from ._interface import BotMode, BotModeError
from ._asserts import (
    SavedMapLocation,
    assert_item_exists_in_bag,
    assert_save_game_exists,
    assert_saved_on_map,
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
        self._target_pokemon = None
        self._starting_cash = None
        self._should_reset = False
        self._should_reenter = False
        self._atleast_one_pokemon_catched = False
        self._use_repel = False
        self._money_spent_limit = 2000

    @staticmethod
    def name() -> str:
        return "Safari"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_group_and_number == MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        """
        Handle the outcome of a battle. If the battle resulted in a catch,
        update flags to manage the re-entry or reset logic.
        """
        if outcome is BattleOutcome.Caught:
            self._atleast_one_pokemon_catched = True
        if get_safari_balls_left() < 30:
            current_cash = get_player().money
            if (self._starting_cash - current_cash > self._money_spent_limit) or (current_cash < 500):
                self._should_reset = True
            else:
                self._should_reenter = True

    def run(self) -> Generator:
        self._starting_cash = get_player().money

        assert_save_game_exists("There is no saved game. Cannot start Safari mode. Please save your game.")
        assert_saved_on_map(
            SavedMapLocation(MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE),
            "In order to start the Safari mode you should save in the entrance building to the Safari Zone.",
        )

        pokemon_choices = []
        for safari_pokemon in SafariPokemon.available_pokemon(context.rom):
            sprite_path = get_sprites_path() / "pokemon/normal" / f"{safari_pokemon.name}.png"
            pokemon_choices.append(Selection(f"{safari_pokemon.value.name}", sprite_path))

        pokemon_choice = ask_for_choice_scroll(
            choices=pokemon_choices,
            window_title="Select a Pokemon to hunt...",
            button_width=172,
            button_height=170,
            options_per_row=3,
        )

        if pokemon_choice is None:
            context.set_manual_mode()
            yield
            return

        self._target_pokemon = get_safari_pokemon(pokemon_choice)
        self._check_mode_requirement(self._target_pokemon.value.mode, self._target_pokemon.value.hunting_object)

        if self._target_pokemon.value.mode != SafariHuntingMode.FISHING:
            mode = ask_for_choice(
                [
                    Selection("Use Repel", get_sprites_path() / "items" / "Repel.png"),
                    Selection("No Repel", get_sprites_path() / "other" / "No Repel.png"),
                ],
                window_title="Use Repel?",
            )

            if mode is None:
                context.set_manual_mode()
                yield
                return

            if mode == "Use Repel":
                self._use_repel = True

        if self._target_pokemon.value.hunting_object:
            yield from register_key_item(get_item_by_name(self._target_pokemon.value.hunting_object))

        while True:
            if self._should_reset:
                if not self._atleast_one_pokemon_catched:
                    yield from self._soft_reset()
                    self._starting_cash = get_player().money
                else:
                    yield from self._exit_safari_zone()
                    context.message = f"You have reached the money threshold (either out of money or have spent over {self._money_spent_limit}₽), but you've caught a Pokémon during this phase. It's recommended to save your game and restart the mode."
                    context.set_manual_mode()
            if self._should_reenter:
                yield from self._re_enter_safari_zone()

            yield from self._start_safari_hunt(self._target_pokemon)

    def _start_safari_hunt(self, safari_pokemon: SafariPokemon) -> Generator:
        current_cash = get_player().money
        if current_cash < 500:
            raise BotModeError("You do not have enough cash to enter the Safari Zone.")

        yield from navigate_to(MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE, (4, 4))
        yield from ensure_facing_direction("Up")
        context.emulator.hold_button("Up")
        for _ in range(10):
            yield
        context.emulator.release_button("Up")
        yield
        yield from wait_for_script_to_start_and_finish(
            "FuchsiaCity_SafariZone_Entrance_EventScript_AskEnterSafariZone", "A"
        )
        yield from wait_for_script_to_start_and_finish(
            "FuchsiaCity_SafariZone_Entrance_EventScript_TryEnterSafariZone", "A"
        )
        yield from wait_for_player_avatar_to_be_controllable()
        yield from self._navigate_and_hunt(
            safari_pokemon.value.map_location, safari_pokemon.value.tile_location, safari_pokemon.value.mode
        )

    def _re_enter_safari_zone(self) -> Generator:
        """Handles re-entry into the Safari Zone."""
        yield from self._exit_safari_zone()
        self._should_reenter = False
        return

    def _exit_safari_zone(self) -> Generator:
        """Handles re-entry into the Safari Zone."""
        yield from StartMenuNavigator("RETIRE").step()
        yield from wait_for_script_to_start_and_finish("FuchsiaCity_SafariZone_Entrance_EventScript_ExitWarpIn", "A")
        yield from wait_for_player_avatar_to_be_standing_still()

    def _navigate_and_hunt(
        self, target_map: MapFRLG, tile_location: Tuple[int, int], mode: SafariHuntingMode
    ) -> Generator:
        def stop_condition():
            return self._should_reset or self._should_reenter

        def is_at_entrance_door():
            return (
                get_player_avatar().map_group_and_number == MapFRLG.SAFARI_ZONE_CENTER
                and get_player_avatar().local_coordinates in (26, 30)
            )

        if is_at_entrance_door():
            yield from wait_for_player_avatar_to_be_standing_still()

        path = get_navigation_path(target_map, tile_location)

        for map_group, coords, warp_direction in path:
            while True:
                if get_player_avatar().map_group_and_number == map_group:
                    if get_player_avatar().local_coordinates == coords:
                        if warp_direction:
                            yield from self._warp(warp_direction)
                        break
                    else:
                        yield from navigate_to(map_group, coords)
                else:
                    yield from navigate_to(map_group, coords)

        if mode in (SafariHuntingMode.SPIN, SafariHuntingMode.SURF):
            if self._use_repel and not repel_is_active():
                yield from apply_repel()
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

    def _warp(self, direction: str) -> Generator:
        yield from ensure_facing_direction(direction)
        context.emulator.hold_button(direction)
        for _ in range(50):
            yield
        context.emulator.release_button(direction)
        yield from wait_for_player_avatar_to_be_controllable()

    def _soft_reset(self) -> Generator:
        """Handles soft resetting if cash difference exceeds the limit."""
        yield from soft_reset()
        yield from wait_for_unique_rng_value()
        self._should_reset = False
        for _ in range(5):
            yield
