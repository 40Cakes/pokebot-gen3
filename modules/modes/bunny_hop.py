from typing import Generator

from ._interface import BotMode, BotModeError
from modules.context import context
from modules.memory import get_game_state, GameState
from modules.player import get_player, get_player_avatar, TileTransitionState, AcroBikeState


class BunnyHopMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Bunny Hop"

    def run(self) -> Generator:
        registered_item = get_player().registered_item
        if registered_item is None or registered_item.name != "Acro Bike":
            raise BotModeError("You need to register the Acro Bike for the Select button.")

        while True:
            player = get_player_avatar()
            match (player.acro_bike_state, player.tile_transition_state, player.is_on_bike):
                case (AcroBikeState.NORMAL, TileTransitionState.NOT_MOVING, False):
                    context.emulator.press_button("Select")
                case (AcroBikeState.HOPPING_WHEELIE, TileTransitionState.CENTERING, True):
                    if get_game_state() == GameState.BATTLE:
                        context.emulator.release_button("B")
                        return
                case (AcroBikeState.STANDING_WHEELIE, TileTransitionState.NOT_MOVING, True):
                    context.emulator.hold_button("B")
                case _:
                    context.emulator.press_button("B")
            yield
