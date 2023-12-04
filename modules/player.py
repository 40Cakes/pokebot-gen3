from enum import IntFlag, IntEnum, Enum
from functools import cached_property
from typing import Literal

from modules.game import decode_string
from modules.context import context
from modules.map import MapLocation, ObjectEvent
from modules.memory import get_save_block, read_symbol, unpack_uint16
from modules.state_cache import state_cache
from modules.data.map import MapRSE, MapFRLG


# https://github.com/pret/pokeemerald/blob/104e81b359d287668cee613f6604020a6e7228a3/include/global.fieldmap.h
class AvatarFlags(IntFlag):
    OnFoot = 1 << 0
    OnMachBike = 1 << 1
    OnAcroBike = 1 << 2
    Surfing = 1 << 3
    Underwater = 1 << 4
    Controllable = 1 << 5
    ForciblyMoving = 1 << 6
    Dash = 1 << 7


class RunningState(IntEnum):
    NOT_MOVING = 0
    TURN_DIRECTION = 1
    MOVING = 2


class TileTransitionState(IntEnum):
    NOT_MOVING = 0
    TRANSITIONING = 1  # transition between tiles
    CENTERING = 2  # on the frame in which you have centered on a tile but are about to keep moving,
    # even if changing directions. Used for a ledge hop, since you are transitioning


class AcroBikeState(IntEnum):
    NORMAL = 0
    TURNING = 1
    STANDING_WHEELIE = 2
    HOPPING_WHEELIE = 3
    MOVING_WHEELIE = 4


class FacingDirection(Enum):
    Down = 0x11
    Up = 0x22
    Left = 0x33
    Right = 0x44


class Player:
    def __init__(self, object_event: ObjectEvent, player_avatar_data: bytes):
        self._object_event = object_event
        self._player_avatar_data = player_avatar_data

        if context.rom.game_title in ["POKEMON EMER", "POKEMON RUBY", "POKEMON SAPP"]:
            self._map_data = MapRSE
        else:
            self._map_data = MapFRLG

    def __eq__(self, other):
        if isinstance(other, Player):
            return other._object_event == self._object_event and other._player_avatar_data == self._player_avatar_data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Player):
            return other._object_event != self._object_event or other._player_avatar_data != self._player_avatar_data
        else:
            return NotImplemented

    @property
    def name(self) -> str:
        return decode_string(get_save_block(2, size=8))

    @property
    def gender(self) -> Literal["male", "female"]:
        if get_save_block(2, 0x8, 1) == b'\x00':
            return "male"
        else:
            return "female"

    @property
    def trainer_id(self) -> int:
        return unpack_uint16(get_save_block(2, 0xA, 2))

    @property
    def secret_id(self) -> int:
        return unpack_uint16(get_save_block(2, 0xC, 2))

    @property
    def map_group_and_number(self) -> tuple[int, int]:
        data = get_save_block(1, offset=4, size=2)
        return data[0], data[1]

    @cached_property
    def map_location(self) -> MapLocation:
        return MapLocation(read_symbol("gMapHeader"), self._object_event.map_group, self._object_event.map_num,
                           self._object_event.current_coords)

    @property
    def map_name(self) -> str:
        try:
            if context.rom.game_title in ["POKEMON EMER", "POKEMON RUBY", "POKEMON SAPP"]:
                return MapRSE(self.map_group_and_number).name
            else:
                return MapFRLG(self.map_group_and_number).name
        except ValueError:
            return "UNKNOWN"

    @property
    def local_coordinates(self) -> tuple[int, int]:
        return self._object_event.current_coords

    @property
    def flags(self) -> AvatarFlags:
        return AvatarFlags(self._player_avatar_data[0])

    @property
    def is_on_bike(self) -> bool:
        return AvatarFlags.OnAcroBike in self.flags \
            or AvatarFlags.OnMachBike in self.flags

    @property
    def running_state(self) -> RunningState:
        return RunningState(self._player_avatar_data[2])

    @property
    def tile_transition_state(self) -> TileTransitionState:
        return TileTransitionState(self._player_avatar_data[3])

    @property
    def acro_bike_state(self) -> AcroBikeState:
        return AcroBikeState(self._player_avatar_data[8])

    @property
    def facing_direction(self) -> str:
        return self._object_event.facing_direction

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "tid": self.trainer_id,
            "sid": self.secret_id,
            "map": self.map_group_and_number,
            "map_name": self.map_name,
            "coords": self.local_coordinates,
            "running_state": self.running_state.name,
            "tile_transition_state": self.tile_transition_state.name,
            "acro_bike_state": self.acro_bike_state.name,
            "on_bike": self.is_on_bike,
            "facing": self.facing_direction,
        }


def get_player() -> Player:
    if state_cache.player.age_in_frames == 0:
        return state_cache.player.value

    player_avatar_data = read_symbol("gPlayerAvatar")
    object_event_id = player_avatar_data[5]
    object_event = ObjectEvent(read_symbol("gObjectEvents", object_event_id * 0x24, 0x24))

    player = Player(object_event, player_avatar_data)
    state_cache.player = player

    return player
