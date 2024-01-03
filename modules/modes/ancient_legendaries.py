from enum import Enum, auto
from pathlib import Path
from typing import Generator

from ._interface import BotMode
from modules.context import context
from modules.data.map import MapRSE
from modules.gui.multi_select_window import MultiSelector, Selection, MultiSelectWindow
from modules.memory import get_game_state, GameState, get_event_flag
from modules.navigation import follow_path
from modules.player import get_player_avatar


class ModeAncientLegendariesStates(Enum):
    LEAVE_ROOM = auto()
    INTERACT = auto()


class ModeAncientLegendaries(BotMode):
    @staticmethod
    def name() -> str:
        return "Ancient Legendaries"

    @staticmethod
    def is_selectable() -> bool:
        player = get_player_avatar()
        allowed_maps = [MapRSE.MARINE_CAVE_A.value, MapRSE.TERRA_CAVE_A.value, MapRSE.SKY_PILLAR_G.value]
        return context.rom.is_rse and player.map_group_and_number in allowed_maps

    def setup(self):
        if context.rom.game_title != "POKEMON EMER":  # TODO add RS support
            context.message("Only Emerald is supported, RS coming soon.")
            return

        if not context.selected_pokemon:
            player = get_player_avatar()
            sprites = Path(__file__).parent.parent.parent / "sprites" / "pokemon" / "normal"

            conditions = {
                "Kyogre": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and not get_event_flag("FLAG_DEFEATED_KYOGRE")
                        and not get_event_flag("FLAG_LEGENDARY_BATTLE_COMPLETED")
                        and player.map_group_and_number == MapRSE.MARINE_CAVE_A.value
                        and 5 <= player.local_coordinates[0] <= 14
                        and 26 <= player.local_coordinates[1] <= 27
                    )
                ),
                "Groudon": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and not get_event_flag("FLAG_DEFEATED_GROUDON")
                        and not get_event_flag("FLAG_LEGENDARY_BATTLE_COMPLETED")
                        and player.map_group_and_number == MapRSE.TERRA_CAVE_A.value
                        and 11 <= player.local_coordinates[0] <= 17
                        and 26 <= player.local_coordinates[1] <= 27
                    )
                ),
                "Rayquaza": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and not get_event_flag("FLAG_DEFEATED_RAYQUAZA")
                        and player.map_group_and_number == MapRSE.SKY_PILLAR_G.value
                        and player.local_coordinates[0] == 14
                        and 4 <= player.local_coordinates[1] <= 12
                    )
                ),
            }

            selections = [
                Selection(
                    button_label="Kyogre",
                    button_enable=conditions["Kyogre"],
                    button_tooltip="Select Kyogre"
                    if conditions["Kyogre"]
                    else "Invalid location:\nPlace the player on the platform in Marine Cave, in front of Kyogre",
                    sprite=sprites / "Kyogre.png",
                ),
                Selection(
                    button_label="Groudon",
                    button_enable=conditions["Groudon"],
                    button_tooltip="Select Groudon"
                    if conditions["Groudon"]
                    else "Invalid location:\nPlace the player on the platform in Terra Cave, in front of Groudon",
                    sprite=sprites / "Groudon.png",
                ),
                Selection(
                    button_label="Rayquaza",
                    button_enable=conditions["Rayquaza"],
                    button_tooltip="Select Rayquaza"
                    if conditions["Rayquaza"]
                    else "Invalid location:\nPlace the player at the top of Sky Pillar, facing Rayquaza",
                    sprite=sprites / "Rayquaza.png",
                ),
            ]

            options = MultiSelector("Select a super-ancient legendary...", selections)
            MultiSelectWindow(context.gui.window, options)

        self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.LEAVE_ROOM

    def update_state(self, state: ModeAncientLegendariesStates) -> None:
        self.state: ModeAncientLegendariesStates = state

    def run(self) -> Generator:
        self.setup()

        while True:
            player_avatar = get_player_avatar()

            match self.state, context.selected_pokemon:
                # Kyogre
                case ModeAncientLegendariesStates.LEAVE_ROOM, "Kyogre":
                    if player_avatar.local_coordinates == (9, 26):
                        context.emulator.press_button("B")
                        context.emulator.press_button("Down")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (player_avatar.local_coordinates[0], 27),
                                (18, 27),
                                (18, 14),
                                (14, 14),
                                (14, 4),
                                (20, 4),
                                (20, 99, MapRSE.MARINE_CAVE.value),
                                (14, -99, MapRSE.MARINE_CAVE_A.value),
                                (14, 4),
                                (14, 14),
                                (18, 14),
                                (18, 27),
                                (14, 27),
                            ]
                        )
                        self.update_state(ModeAncientLegendariesStates.INTERACT)
                        continue

                case ModeAncientLegendariesStates.INTERACT, "Kyogre":
                    match get_game_state():
                        case GameState.OVERWORLD:
                            if get_event_flag("FLAG_HIDE_MARINE_CAVE_KYOGRE"):
                                self.update_state(ModeAncientLegendariesStates.LEAVE_ROOM)
                                continue
                            else:
                                follow_path(  # TODO follow_path() needs reworking (not a generator)
                                    [(player_avatar.local_coordinates[0], 26), (9, 26)]
                                )
                        case GameState.BATTLE:
                            return

                # Groudon
                case ModeAncientLegendariesStates.LEAVE_ROOM, "Groudon":
                    if player_avatar.local_coordinates == (17, 26):
                        context.emulator.press_button("B")
                        context.emulator.press_button("Left")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (player_avatar.local_coordinates[0], 26),
                                (7, 26),
                                (7, 15),
                                (9, 15),
                                (9, 4),
                                (5, 4),
                                (5, 99, MapRSE.TERRA_CAVE.value),
                                (14, -99, MapRSE.TERRA_CAVE_A.value),
                                (9, 4),
                                (9, 15),
                                (7, 15),
                                (7, 26),
                                (11, 26),
                            ]
                        )
                        self.update_state(ModeAncientLegendariesStates.INTERACT)
                        continue

                case ModeAncientLegendariesStates.INTERACT, "Groudon":
                    match get_game_state():
                        case GameState.OVERWORLD:
                            if get_event_flag("FLAG_HIDE_TERRA_CAVE_GROUDON"):
                                self.update_state(ModeAncientLegendariesStates.LEAVE_ROOM)
                                continue
                            else:
                                follow_path(  # TODO follow_path() needs reworking (not a generator)
                                    [(player_avatar.local_coordinates[0], 26), (17, 26)]
                                )
                        case GameState.BATTLE:
                            return

                # Rayquaza
                case ModeAncientLegendariesStates.LEAVE_ROOM, "Rayquaza":
                    if player_avatar.local_coordinates[1] <= 7:
                        context.emulator.press_button("B")
                        context.emulator.press_button("Down")
                    else:
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (14, 11),
                                (12, 11),
                                (12, 15),
                                (16, 15),
                                (16, -99, MapRSE.SKY_PILLAR_F.value),
                                (10, -99, MapRSE.SKY_PILLAR_G.value),
                                (12, 15),
                                (12, 11),
                                (14, 11),
                                (14, 7),
                            ]
                        )
                        self.update_state(ModeAncientLegendariesStates.INTERACT)
                        continue

                case ModeAncientLegendariesStates.INTERACT, "Rayquaza":
                    match get_game_state():
                        case GameState.OVERWORLD:
                            context.emulator.press_button("A")
                        case GameState.BATTLE:
                            return
            yield
