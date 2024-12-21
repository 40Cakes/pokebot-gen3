from typing import Generator, Tuple

from modules.context import context
from modules.player import get_player_avatar
from modules.battle_state import BattleOutcome
from modules.map_data import MapFRLG, is_safari_map
from modules.player import TileTransitionState, get_player, get_player_avatar
from modules.tasks import task_is_active
from modules.pokemon_party import get_party
from modules.memory import get_game_state, GameState, get_event_flag
from modules.modes.util.walking import wait_for_player_avatar_to_be_controllable
from modules.safari_strategy import (
    SafariPokemon,
    get_safari_pokemon,
    get_navigation_path,
    SafariHuntingMode,
    SafariHuntingObject,
)
from modules.runtime import get_sprites_path
from modules.gui.multi_select_window import Selection, ask_for_choice_scroll
from ._interface import BotMode, BotModeError
from ._asserts import assert_player_has_poke_balls, assert_item_exists_in_bag, assert_registered_item
from .util import (
    spin,
    navigate_to,
    ensure_facing_direction,
    wait_for_script_to_start_and_finish,
    fish,
    wait_for_player_avatar_to_be_standing_still,
)


class SafariMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Safari"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_group_and_number == MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        try:
            assert_player_has_poke_balls()
        except BotModeError:
            return

    def run(self) -> Generator:

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

        safari_pokemon = get_safari_pokemon(pokemon_choice)

        self._check_mode_requirement(safari_pokemon.value.mode, safari_pokemon.value.hunting_object)

        yield from self.enter_safari_zone()
        yield from self._navigate_and_hunt(
            safari_pokemon.value.map_location, safari_pokemon.value.tile_location, safari_pokemon.value.mode
        )

    def _navigate_and_hunt(
        self, target_map: MapFRLG, tile_location: Tuple[int, int], mode: SafariHuntingMode
    ) -> Generator:
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
            yield from spin()
        elif mode == SafariHuntingMode.FISHING:
            while True:
                yield from fish()
        else:
            raise BotModeError(f"Error: Unknown mode {mode}.")

    def _warp(self, direction: str):
        yield from ensure_facing_direction(direction)
        context.emulator.hold_button(direction)
        for _ in range(50):
            yield
        context.emulator.release_button(direction)
        yield from wait_for_player_avatar_to_be_controllable()

    def enter_safari_zone(self):
        """Handles entering the Safari Zone."""
        if get_player().money < 500:
            raise BotModeError("You do not have enough cash to re-enter the Safari Zone.")
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

    def _check_mode_requirement(self, mode: SafariHuntingMode, object: SafariHuntingObject):
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
                assert_registered_item(
                    object,
                    error_message=f"You need to register the {object} to SELCT in order to hunt this Pokémon in the Safari Zone.",
                )
            case _:
                return True
