from enum import Enum

from modules.console import console
from modules.context import context
from modules.data.map import MapRSE
from modules.memory import get_game_state, GameState, get_event_flag, read_symbol
from modules.navigation import follow_path
from modules.trainer import trainer


class ModeRayquazaStates(Enum):
    INTERACT_RAYQUAZA = 0
    LEAVE_ROOM = 1
    ERROR = 2


class ModeRayquaza:
    def __init__(self):
        if context.rom.game_title == "POKEMON EMER":
            if not get_event_flag("FLAG_DEFEATED_RAYQUAZA"):
                if (
                    trainer.get_map() == MapRSE.SKY_PILLAR_G.value
                    and trainer.get_coords() == (14, 7)
                    and trainer.get_facing_direction() == "Up"
                ):
                    if get_event_flag("FLAG_HIDE_SKY_PILLAR_TOP_RAYQUAZA_STILL"):
                        self.state: ModeRayquazaStates = ModeRayquazaStates.LEAVE_ROOM
                    else:
                        self.state: ModeRayquazaStates = ModeRayquazaStates.INTERACT_RAYQUAZA
                else:
                    self.state: ModeRayquazaStates = ModeRayquazaStates.ERROR
                    self.error_message = (
                        "Place the trainer directly in front of, and facing Rayquaza at the top of Sky Pillar "
                        "before starting this mode!"
                    )
            else:
                self.state: ModeRayquazaStates = ModeRayquazaStates.ERROR
                self.error_message = "Rayquaza has already been caught/defeated on this save file!"
        else:
            self.state: ModeRayquazaStates = ModeRayquazaStates.ERROR
            self.error_message = f"Rayquaza is not in {context.rom.game_name}!"

    def update_state(self, state: ModeRayquazaStates):
        self.state: ModeRayquazaStates = state

    def step(self):
        if self.state == ModeRayquazaStates.ERROR:
            console.print(f"[red bold]{self.error_message}")
            context.message = self.error_message
            context.bot_mode = "Manual"
            return

        while True:
            match self.state:
                case ModeRayquazaStates.INTERACT_RAYQUAZA:
                    match get_game_state():
                        case GameState.OVERWORLD:
                            if (
                                get_event_flag("FLAG_HIDE_SKY_PILLAR_TOP_RAYQUAZA_STILL")
                                and int.from_bytes(read_symbol("gObjectEvents", 0, 1)) != 1  # TODO look into decoding gObjectEvents properly - https://github.com/pret/pokeemerald/blob/2304283c3ef2675be5999349673b02796db0827d/include/global.fieldmap.h#L168
                            ):
                                self.update_state(ModeRayquazaStates.LEAVE_ROOM)
                                continue
                            else:
                                context.emulator.press_button("A")
                        case GameState.BATTLE:
                            return

                case ModeRayquazaStates.LEAVE_ROOM:
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
