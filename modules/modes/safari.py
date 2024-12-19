from typing import Generator

from modules.context import context
from modules.player import get_player_avatar
from modules.battle_state import BattleOutcome
from modules.map_data import MapFRLG, is_safari_map
from modules.player import TileTransitionState, get_player, get_player_avatar
from modules.tasks import task_is_active
from modules.memory import get_game_state, GameState
from modules.modes.util.walking import wait_for_player_avatar_to_be_controllable
from modules.safari_strategy import SafariPokemon, get_safari_pokemon
from modules.runtime import get_sprites_path
from modules.gui.multi_select_window import Selection, ask_for_choice_scroll
from ._interface import BotMode
from ._asserts import assert_player_has_poke_balls
from .util import (
    spin,
    navigate_to,
    ensure_facing_direction,
    wait_for_script_to_start_and_finish,
    fish,
    wait_for_player_avatar_to_be_standing_still,
)
from modules.console import console


class SafariMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Safari"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_group_and_number == MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if not outcome == BattleOutcome.Lost:
            assert_player_has_poke_balls()

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

        yield from self.enter_safari_zone()
        yield from self._navigate_and_hunt(safari_pokemon.value.map_location, safari_pokemon.value.mode)

    def _navigate_and_hunt(self, target_map, mode) -> Generator:
        """Navigates to the target map and performs the desired hunting mode."""

        def is_at_entrance_door():
            return (
                get_player_avatar().map_group_and_number == MapFRLG.SAFARI_ZONE_CENTER
                and get_player_avatar().local_coordinates in (26, 30)
            )

        if is_at_entrance_door():
            yield from wait_for_player_avatar_to_be_standing_still()

        navigation_paths = {
            MapFRLG.SAFARI_ZONE_NORTH: [
                (MapFRLG.SAFARI_ZONE_CENTER, (42, 16), "Right"),
                (MapFRLG.SAFARI_ZONE_EAST, (9, 9), "Left"),
                (MapFRLG.SAFARI_ZONE_NORTH, (35, 30), None),
            ]
        }

        path = navigation_paths.get(target_map)
        if not path:
            console.print(f"Error: No navigation path defined for {target_map}.")
            return

        for map_group, coords, warp_direction in path:
            while True:
                console.print(f"Current map: {get_player_avatar().map_group_and_number}, Target map: {map_group}")
                console.print(
                    f"Current coordinates: {get_player_avatar().local_coordinates}, Target coordinates: {coords}"
                )

                if get_player_avatar().map_group_and_number == map_group:
                    if get_player_avatar().local_coordinates == coords:
                        console.print(f"Arrived at destination {map_group}, {coords}.")
                        if warp_direction:
                            console.print(f"Warping to {map_group} in direction {warp_direction}.")
                            yield from self._warp(warp_direction)
                        break
                    else:
                        console.print(f"Navigating within {map_group} to {coords}.")
                        yield from navigate_to(map_group, coords)
                else:
                    console.print(f"Navigating to map group {map_group}, coordinates {coords}.")
                    yield from navigate_to(map_group, coords)

        if mode == "spin":
            yield from spin()
        elif mode == "fish":
            while True:
                yield from fish()
        else:
            console.print(f"Error: Unknown mode {mode}.")

    def _warp(self, direction):
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
        while (
            get_player_avatar().local_coordinates != (26, 30)
            or task_is_active("Task_RunMapPreviewScreenForest")
            or get_game_state() == GameState.CHANGE_MAP
        ):
            yield
        yield from wait_for_player_avatar_to_be_controllable()
