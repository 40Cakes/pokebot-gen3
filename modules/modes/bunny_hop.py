from typing import Generator

from ._interface import BotMode, BotModeError
from modules.context import context
from modules.player import get_player, get_player_avatar, TileTransitionState, AcroBikeState


class BunnyHopMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Bunny Hop"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def run(self) -> Generator:
        registered_item = get_player().registered_item
        if registered_item is None or registered_item.name != "Acro Bike":
            raise BotModeError("You need to register the Acro Bike for the Select button.")

        while True:
            player = get_player_avatar()

            if not player.is_on_bike:
                context.emulator.press_button("Select")
            elif (
                player.acro_bike_state == AcroBikeState.HOPPING_WHEELIE
                and player.tile_transition_state == TileTransitionState.CENTERING
            ):
                context.emulator.release_button("B")
            elif (
                player.acro_bike_state == AcroBikeState.STANDING_WHEELIE
                and player.tile_transition_state == TileTransitionState.NOT_MOVING
            ):
                context.emulator.hold_button("B")
            else:
                context.emulator.press_button("B")

            yield
