from enum import Enum
from pathlib import Path

from modules.context import context
from modules.data.map import MapRSE
from modules.gui.multi_select_window import MultiSelector, Selection, MultiSelectWindow
from modules.memory import get_game_state, GameState, get_event_flag, read_symbol
from modules.navigation import follow_path
from modules.trainer import trainer


class ModeAncientLegendariesStates(Enum):
    INTERACT = 0
    LEAVE_ROOM = 1


class ModeAncientLegendaries:
    def __init__(self):
        if not context.selected_pokemon:
            trainer_coords = trainer.get_coords()
            trainer_map = trainer.get_map()
            sprites = Path(__file__).parent.parent.parent / "sprites" / "pokemon" / "normal"

            conditions = {
                "Kyogre": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and not get_event_flag("FLAG_DEFEATED_KYOGRE")
                        and trainer_map == MapRSE.MARINE_CAVE_A.value
                        and not trainer_coords == (9, 26)  # Tile that triggers Kyogre to initiate battle
                        and 5 <= trainer_coords[0] <= 14
                        and 26 <= trainer_coords[1] <= 27
                    )
                ),
                "Groudon": bool(
                    (
                        context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP", "POKEMON EMER"]
                        and not get_event_flag("FLAG_DEFEATED_GROUDON")
                        and trainer_map == MapRSE.TERRA_CAVE_A.value
                        and not trainer_coords == (17, 26)  # Tile that triggers Groudon to initiate battle
                        and 11 <= trainer_coords[0] <= 20
                        and 26 <= trainer_coords[1] <= 27
                    )
                ),
                "Rayquaza": bool(
                    (
                        context.rom.game_title == "POKEMON EMER"
                        and not get_event_flag("FLAG_DEFEATED_RAYQUAZA")
                        and trainer_map == MapRSE.SKY_PILLAR_G.value
                        and trainer_coords == (14, 7)
                        and trainer.get_facing_direction() == "Up"
                    )
                ),
            }

            selections = [
                Selection(
                    "Kyogre",
                    conditions["Kyogre"],
                    "Select Kyogre"
                    if conditions["Kyogre"]
                    else (
                        "Invalid location:\n"
                        "Place the trainer anywhere on the platform in Marine Cave, in front of Kyogre"
                    ),
                    sprites / "Kyogre.png",
                ),
                Selection(
                    "Groudon",
                    conditions["Groudon"],
                    "Select Groudon"
                    if conditions["Groudon"]
                    else (
                        "Invalid location:\n"
                        "Place the trainer anywhere on the platform in Terra Cave, in front of Groudon"
                    ),
                    sprites / "Groudon.png",
                ),
                Selection(
                    "Rayquaza",
                    conditions["Rayquaza"],
                    "Select Rayquaza"
                    if conditions["Rayquaza"]
                    else "Invalid location:\nPlace the trainer at the top of Sky Pillar, facing Rayquaza",
                    sprites / "Rayquaza.png",
                ),
            ]

            options = MultiSelector("Select a super-ancient legendary...", selections)
            MultiSelectWindow(context.gui.window, options)

        self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.LEAVE_ROOM

        match context.selected_pokemon:
            case "Kyogre":
                if not get_event_flag("FLAG_HIDE_MARINE_CAVE_KYOGRE"):  # TODO flag is Emerald only
                    self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.INTERACT
            case "Groudon":
                if not get_event_flag("FLAG_HIDE_TERRA_CAVE_GROUDON"):  # TODO flag is Emerald only
                    self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.INTERACT
            case "Rayquaza":
                if not get_event_flag("FLAG_HIDE_SKY_PILLAR_TOP_RAYQUAZA_STILL"):
                    self.state: ModeAncientLegendariesStates = ModeAncientLegendariesStates.INTERACT
            case _:
                return

    def update_state(self, state: ModeAncientLegendariesStates):
        self.state: ModeAncientLegendariesStates = state

    def step(self):
        while True:
            match self.state, context.selected_pokemon:
                case ModeAncientLegendariesStates.INTERACT, "Kyogre":
                    match get_game_state():
                        case GameState.OVERWORLD:
                            if get_event_flag("FLAG_HIDE_MARINE_CAVE_KYOGRE"):
                                self.update_state(ModeAncientLegendariesStates.LEAVE_ROOM)
                                continue
                            else:
                                follow_path(  # TODO follow_path() needs reworking (not a generator)
                                    [(trainer.get_coords()[0], 26), (9, 26)]
                                )
                        case GameState.BATTLE:
                            return

                case ModeAncientLegendariesStates.INTERACT, "Groudon":
                    match get_game_state():
                        case GameState.OVERWORLD:
                            if get_event_flag("FLAG_HIDE_TERRA_CAVE_GROUDON"):
                                self.update_state(ModeAncientLegendariesStates.LEAVE_ROOM)
                                continue
                            else:
                                follow_path(  # TODO follow_path() needs reworking (not a generator)
                                    [(trainer.get_coords()[0], 26), (17, 26)]
                                )
                        case GameState.BATTLE:
                            return

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

                case ModeAncientLegendariesStates.LEAVE_ROOM, "Kyogre":
                    if trainer.get_coords() == (9, 26):
                        context.emulator.hold_button("Down")
                        context.emulator.press_button("B")
                    else:
                        context.emulator.release_button("Down")
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (trainer.get_coords()[0], 27),
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

                case ModeAncientLegendariesStates.LEAVE_ROOM, "Groudon":
                    if trainer.get_coords() == (17, 26):
                        context.emulator.hold_button("Left")
                        context.emulator.press_button("B")
                    else:
                        context.emulator.release_button("Left")
                        follow_path(  # TODO follow_path() needs reworking (not a generator)
                            [
                                (trainer.get_coords()[0], 26),
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
