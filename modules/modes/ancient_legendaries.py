from enum import Enum, auto
from pathlib import Path

from modules.context import context
from modules.data.map import MapRSE
from modules.gui.multi_select_window import MultiSelector, Selection, MultiSelectWindow
from modules.memory import get_game_state, GameState, get_event_flag, read_symbol
from modules.navigation import follow_path
from modules.player import get_player_avatar


class ModeAncientLegendariesStates(Enum):
    INTERACT = auto()
    LEAVE_ROOM = auto()


class ModeAncientLegendaries:
    def __init__(self):
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
                        and not player.local_coordinates == (9, 26)  # Tile that triggers Kyogre to initiate battle
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
                        and not player.local_coordinates == (17, 26)  # Tile that triggers Groudon to initiate battle
                        and 11 <= player.local_coordinates[0] <= 20
                        and 26 <= player.local_coordinates[1] <= 27
                    )
                ),
                "Rayquaza": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and not get_event_flag("FLAG_DEFEATED_RAYQUAZA")
                        and player.map_group_and_number == MapRSE.SKY_PILLAR_G.value
                        and player.local_coordinates == (14, 7)
                        and player.facing_direction == "Up"
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

        match context.selected_pokemon:
            case "Kyogre":
                if not get_event_flag("FLAG_HIDE_MARINE_CAVE_KYOGRE") and not get_event_flag(
                    "FLAG_LEGENDARY_BATTLE_COMPLETED"
                ):
                    self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.INTERACT
            case "Groudon":
                if not get_event_flag("FLAG_HIDE_TERRA_CAVE_GROUDON") and not get_event_flag(
                    "FLAG_LEGENDARY_BATTLE_COMPLETED"
                ):
                    self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.INTERACT
            case "Rayquaza":
                if not get_event_flag("FLAG_HIDE_SKY_PILLAR_TOP_RAYQUAZA_STILL"):
                    self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.INTERACT
            case _:
                return

    def update_state(self, state: ModeAncientLegendariesStates) -> None:
        self.state: ModeAncientLegendariesStates = state

    def step(self):
        while True:
            player_avatar = get_player_avatar()

            # Kyogre
            match self.state, context.selected_pokemon:
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

                case ModeAncientLegendariesStates.LEAVE_ROOM, "Kyogre":
                    if player_avatar.local_coordinates == (9, 26):
                        context.emulator.hold_button("Down")
                        context.emulator.press_button("B")
                    else:
                        context.emulator.release_button("Down")
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
                        return

                # Groudon
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
                case ModeAncientLegendariesStates.LEAVE_ROOM, "Groudon":
                    if player_avatar.local_coordinates == (17, 26):
                        context.emulator.hold_button("Left")
                        context.emulator.press_button("B")
                    else:
                        context.emulator.release_button("Left")
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
                        return

                # Rayquaza
                case ModeAncientLegendariesStates.INTERACT, "Rayquaza":
                    match get_game_state():
                        case GameState.OVERWORLD:
                            if (
                                get_event_flag("FLAG_HIDE_SKY_PILLAR_TOP_RAYQUAZA_STILL")
                                and int.from_bytes(read_symbol("gObjectEvents", 0, 1))
                                != 1  # TODO look into decoding gObjectEvents properly - https://github.com/pret/pokeemerald/blob/2304283c3ef2675be5999349673b02796db0827d/include/global.fieldmap.h#L168
                            ):
                                self.update_state(ModeAncientLegendariesStates.LEAVE_ROOM)
                                continue
                            else:
                                context.emulator.press_button("A")
                        case GameState.BATTLE:
                            return

                case ModeAncientLegendariesStates.LEAVE_ROOM, "Rayquaza":
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
                    return
            yield
