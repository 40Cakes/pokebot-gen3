from typing import Generator

from modules.context import context
from modules.memory import GameState, get_game_state
from modules.player import RunningState, TileTransitionState, get_player_avatar
from ._interface import BotMode
from .util import apply_white_flute_if_available


class SpinMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Spin"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def run(self) -> Generator:
        directions = ["Up", "Right", "Down", "Left"]

        yield from apply_white_flute_if_available()
        while True:
            avatar = get_player_avatar()
            if (
                get_game_state() == GameState.OVERWORLD
                and avatar.tile_transition_state == TileTransitionState.NOT_MOVING
                and avatar.running_state == RunningState.NOT_MOVING
            ):
                direction_index = (directions.index(avatar.facing_direction) + 1) % len(directions)
                context.emulator.press_button(directions[direction_index])
            yield
