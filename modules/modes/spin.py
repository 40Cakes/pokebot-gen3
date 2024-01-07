from typing import Generator

from modules.context import context
from modules.player import get_player_avatar, RunningState, TileTransitionState
from ._interface import BotMode


class SpinMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Spin"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def run(self) -> Generator:
        avatar = get_player_avatar()
        directions = ["Up", "Right", "Down", "Left"]
        direction_index = directions.index(avatar.facing_direction)

        while True:
            avatar = get_player_avatar()
            if (
                avatar.tile_transition_state == TileTransitionState.NOT_MOVING
                and avatar.running_state == RunningState.NOT_MOVING
            ):
                direction_index += 1
                direction_index %= len(directions)
                context.emulator.press_button(directions[direction_index])
            yield
