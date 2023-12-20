from typing import Generator

from modules.context import context
from modules.player import get_player_avatar, RunningState, TileTransitionState
from ._interface import BotMode, BotModeError


class SpinMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Spin"

    def run(self) -> Generator:
        avatar = get_player_avatar()
        if not avatar.map_location.has_encounters:
            raise BotModeError("The current tile does not have any encounters, so spinning mode would not do anything.")

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
