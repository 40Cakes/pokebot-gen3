from enum import Enum, auto
from pathlib import Path

from modules.context import context
from modules.data.map import MapRSE
from modules.gui.multi_select_window import MultiSelector, Selection, MultiSelectWindow
from modules.memory import get_game_state, GameState, get_event_flag
from modules.navigation import follow_path
from modules.player import get_player_avatar


class ModeTowerDuoStates(Enum):
    INTERACT = auto()
    LEAVE_ROOM = auto()


class ModeTowerDuo:
    def __init__(self):
        if context.rom.game_title != "POKEMON EMER":
            context.message("Emerald only, FRLG support coming soon™")
            return  # TODO FRLG

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
                                and player.local_coordinates[0] == 11
                                and 14 <= player.local_coordinates[1] <= 20
                            )
                            or (not get_event_flag("FLAG_FOUGHT_LUGIA") and False)  # TODO FRLG
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
                                and player.local_coordinates[0] == 12
                                and 11 <= player.local_coordinates[1] <= 21
                            )
                            or (not get_event_flag("FLAG_FOUGHT_HO_OH") and False)  # TODO FRLG
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
                    else "Invalid location:\nPlace the player anywhere directly in front of Lugia, in Navel Rock",
                    sprite=sprites / "Lugia.png",
                ),
                Selection(
                    button_label="Ho-Oh",
                    button_enable=conditions["Ho-Oh"],
                    button_tooltip="Select Ho-Oh"
                    if conditions["Ho-Oh"]
                    else "Invalid location:\nPlace the player anywhere directly in front of Ho-Oh, on Navel Rock",
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

    def alternate_buttons(self, buttons: tuple) -> None:
        if context.emulator.get_frame_count() % 2 == 0:
            context.emulator.press_button(buttons[0])
        else:
            context.emulator.press_button(buttons[1])

    def step(self):
        while True:
            player_avatar = get_player_avatar()

            match self.state, context.rom.game_title, context.selected_pokemon:
                case ModeTowerDuoStates.LEAVE_ROOM, "POKEMON EMER", "Lugia":
                    if player_avatar.local_coordinates == (11, 14):
                        self.alternate_buttons(("B", "Down"))
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

                case ModeTowerDuoStates.INTERACT, "POKEMON EMER", "Lugia":
                    if get_game_state() != GameState.BATTLE:
                        context.emulator.press_button("A")
                    else:
                        return

                case ModeTowerDuoStates.LEAVE_ROOM, "POKEMON EMER", "Ho-Oh":
                    if player_avatar.local_coordinates == (12, 10):
                        self.alternate_buttons(("B", "Down"))
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

                case ModeTowerDuoStates.INTERACT, "POKEMON EMER", "Ho-Oh":
                    if get_game_state() != GameState.BATTLE:
                        pass
                    else:
                        return
            yield
