from typing import Generator

from modules.context import context
from modules.player import get_player_avatar
from modules.battle_state import BattleOutcome
from modules.map_data import MapFRLG, is_safari_map
from modules.player import TileTransitionState, get_player, get_player_avatar
from modules.tasks import task_is_active
from modules.memory import get_game_state, GameState
from modules.modes.util.walking import wait_for_player_avatar_to_be_controllable
from ._interface import BotMode
from ._asserts import assert_player_has_poke_balls
from .util import spin, navigate_to, ensure_facing_direction, wait_for_script_to_start_and_finish, fish
from modules.console import console


class SafariMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Safari"

    @staticmethod
    def is_selectable() -> bool:
        return is_safari_map()

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if not outcome == BattleOutcome.Lost:
            assert_player_has_poke_balls()

    def run(self) -> Generator:
        yield from self.enter_safari_zone()

        while True:
            match get_player_avatar().map_group_and_number:
                case MapFRLG.FUCHSIA_CITY_SAFARI_ZONE_ENTRANCE:
                    yield from self.enter_safari_zone()
                case MapFRLG.SAFARI_ZONE_CENTER:

                    def is_at_entrance_door():
                        return (
                            get_player_avatar().map_group_and_number == MapFRLG.SAFARI_ZONE_CENTER
                            and get_player_avatar().local_coordinates in (26, 30)
                        )

                    if is_at_entrance_door():
                        yield from wait_for_player_avatar_to_be_standing_still()
                    # yield from navigate_to(MapFRLG.SAFARI_ZONE_CENTER, (32, 19))
                    # while True:
                    #     yield from fish()
                    yield from navigate_to(MapFRLG.SAFARI_ZONE_CENTER, (43, 16))
                case MapFRLG.SAFARI_ZONE_EAST:
                    yield from navigate_to(MapFRLG.SAFARI_ZONE_EAST, (8, 9))
                case MapFRLG.SAFARI_ZONE_NORTH:
                    yield from navigate_to(MapFRLG.SAFARI_ZONE_NORTH, (35, 30))
                    yield from spin()

    def enter_safari_zone(self):
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
            console.print("here")
            yield
        yield from wait_for_player_avatar_to_be_controllable()
