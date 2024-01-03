from enum import Enum, auto
from pathlib import Path
from typing import Generator

from ._interface import BotMode
from modules.context import context
from modules.data.map import MapRSE, MapFRLG
from modules.gui.multi_select_window import MultiSelector, Selection, MultiSelectWindow
from modules.memory import get_game_state, GameState, get_event_flag
from modules.navigation import follow_path
from modules.player import get_player_avatar


class ModeTowerDuoStates(Enum):
    INTERACT = auto()
    LEAVE_ROOM = auto()


class ModeTowerDuo(BotMode):
    @staticmethod
    def name() -> str:
        return "Tower Duo"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_rse:
            allowed_maps = [MapRSE.NAVEL_ROCK_I.value, MapRSE.NAVEL_ROCK_U.value]
        else:
            allowed_maps = [MapFRLG.NAVEL_ROCK_B.value, MapFRLG.NAVEL_ROCK_A.value]
        return get_player_avatar().map_group_and_number in allowed_maps

    def setup(self):
        if not context.selected_pokemon:
            player = get_player_avatar()
            sprites = Path(__file__).parent.parent.parent / "sprites" / "pokemon" / "normal"

            conditions = {
                "Lugia": bool(
                    (
                        context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]
                        and (
                            (
                                not get_event_flag("FLAG_CAUGHT_LUGIA")
                                and player.map_group_and_number == MapRSE.NAVEL_ROCK_U.value
                                and player.local_coordinates[0] == 11  # Lugia Y coord
                                and 14 <= player.local_coordinates[1] <= 20  # Anywhere on the Y coord
                            )
                            or (
                                not get_event_flag("FLAG_FOUGHT_LUGIA")
                                and player.map_group_and_number == MapFRLG.NAVEL_ROCK_B.value
                                and player.local_coordinates[0] == 10  # Lugia Y coord
                                and 16 <= player.local_coordinates[1] <= 21  # Anywhere on the Y coord
                            )
                        )
                    )
                ),
                "Ho-Oh": bool(
                    (
                        context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]
                        and (
                            (
                                not get_event_flag("FLAG_CAUGHT_HO_OH")
                                and player.map_group_and_number == MapRSE.NAVEL_ROCK_I.value
                                and player.local_coordinates[0] == 12  # Ho-Oh Y coord
                                and 10 <= player.local_coordinates[1] <= 21  # Anywhere on the Y coord
                            )
                            or (
                                not get_event_flag("FLAG_FOUGHT_HO_OH")
                                and player.map_group_and_number == MapFRLG.NAVEL_ROCK_A.value
                                and player.local_coordinates[0] == 9  # Ho-Oh Y coord
                                and 13 <= player.local_coordinates[1] <= 19  # Anywhere on the Y coord
                            )
                        )
                    )
                ),
            }

            selections = [
                Selection(
                    button_label="Lugia",
                    button_enable=conditions["Lugia"],
                    button_tooltip="Select Lugia"
                    if conditions["Lugia"]
                    else "Invalid location:\nPlace the player directly in front of Lugia, in Navel Rock",
                    sprite=sprites / "Lugia.png",
                ),
                Selection(
                    button_label="Ho-Oh",
                    button_enable=conditions["Ho-Oh"],
                    button_tooltip="Select Ho-Oh"
                    if conditions["Ho-Oh"]
                    else "Invalid location:\nPlace the player directly in front of Ho-Oh, on Navel Rock",
                    sprite=sprites / "Ho-Oh.png",
                ),
            ]

            options = MultiSelector("Select a tower duo legendary...", selections)
            MultiSelectWindow(context.gui.window, options)

        if context.selected_pokemon in ["Lugia", "Ho-Oh"]:
            self.state: ModeTowerDuoStates = ModeTowerDuoStates.LEAVE_ROOM
        else:
            return

    def update_state(self, state: ModeTowerDuoStates) -> None:
        self.state: ModeTowerDuoStates = state

    def run(self) -> Generator:
        self.setup()

        while True:
            player_avatar = get_player_avatar()

            match self.state, context.rom.game_title, context.selected_pokemon:
                case ModeTowerDuoStates.LEAVE_ROOM, "POKEMON EMER", "Lugia":
                    if player_avatar.local_coordinates == (11, 14):
                        context.emulator.press_button("B")
                        context.emulator.press_button("Down")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (11, 19),
                                (99, 19, MapRSE.NAVEL_ROCK_T.value),
                                (4, 5),
                                (99, 5, MapRSE.NAVEL_ROCK_U.value),
                                (11, 19),
                                (11, 14),
                            ]
                        )
                        self.update_state(ModeTowerDuoStates.INTERACT)

                case ModeTowerDuoStates.LEAVE_ROOM, "POKEMON FIRE" | "POKEMON LEAF", "Lugia":
                    if player_avatar.local_coordinates == (10, 16):
                        context.emulator.press_button("B")
                        context.emulator.press_button("Down")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (10, 20),
                                (99, 20, MapFRLG.NAVEL_ROCK_Q.value),
                                (3, 4),
                                (99, 4, MapFRLG.NAVEL_ROCK_B.value),
                                (10, 20),
                                (10, 16),
                            ]
                        )
                        self.update_state(ModeTowerDuoStates.INTERACT)

                case ModeTowerDuoStates.LEAVE_ROOM, "POKEMON EMER", "Ho-Oh":
                    if player_avatar.local_coordinates == (12, 10):
                        context.emulator.press_button("B")
                        context.emulator.press_button("Down")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (12, 20),
                                (99, 20, MapRSE.NAVEL_ROCK_H.value),
                                (4, 5),
                                (99, 5, MapRSE.NAVEL_ROCK_I.value),
                                (12, 20),
                                (12, 10),
                            ]
                        )
                        self.update_state(ModeTowerDuoStates.INTERACT)

                case ModeTowerDuoStates.LEAVE_ROOM, "POKEMON FIRE" | "POKEMON LEAF", "Ho-Oh":
                    if player_avatar.local_coordinates == (9, 12):
                        context.emulator.press_button("B")
                        context.emulator.press_button("Down")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (9, 18),
                                (99, 18, MapFRLG.NAVEL_ROCK_F.value),
                                (3, 4),
                                (99, 4, MapFRLG.NAVEL_ROCK_A.value),
                                (9, 18),
                                (9, 12),
                            ]
                        )
                        self.update_state(ModeTowerDuoStates.INTERACT)

                case ModeTowerDuoStates.INTERACT, "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF", "Lugia" | "Ho-Oh":
                    if get_game_state() != GameState.BATTLE:
                        context.emulator.press_button("A")
                    else:
                        return
            yield
