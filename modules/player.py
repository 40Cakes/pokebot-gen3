from enum import Enum, IntEnum, IntFlag
from functools import cached_property
from typing import Literal

from modules.context import context
from modules.game import decode_string
from modules.map import MapLocation, ObjectEvent, calculate_targeted_coords, get_player_map_object
from modules.map_data import MapFRLG, MapRSE, get_map_enum
from modules.memory import get_save_block, read_symbol, unpack_uint16, unpack_uint32, get_game_state, GameState
from modules.pokemon import Item, get_item_by_index
from modules.state_cache import state_cache
from modules.tasks import task_is_active


# https://github.com/pret/pokeemerald/blob/104e81b359d287668cee613f6604020a6e7228a3/include/global.fieldmap.h
class AvatarFlags(IntFlag):
    OnFoot = 1 << 0
    OnMachBike = 1 << 1
    OnAcroBike = 1 << 2
    Surfing = 1 << 3
    Underwater = 1 << 4
    Controllable = 1 << 5
    ForcedMove = 1 << 6
    Running = 1 << 7


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
    SIDE_JUMP = 5
    TURN_JUMP = 6


class FacingDirection(Enum):
    Down = 0x11
    Up = 0x22
    Left = 0x33
    Right = 0x44


class PlayerAvatar:
    def __init__(self, object_event: ObjectEvent, player_avatar_data: bytes, map_group_and_number: bytes):
        self._object_event = object_event
        self._player_avatar_data = player_avatar_data
        self._map_group_and_number = map_group_and_number

    def __eq__(self, other):
        if isinstance(other, PlayerAvatar):
            return (
                other._object_event == self._object_event
                and other._player_avatar_data == self._player_avatar_data
                and other._map_group_and_number == self._map_group_and_number
            )
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, PlayerAvatar):
            return (
                other._object_event != self._object_event
                or other._player_avatar_data != self._player_avatar_data
                or other._map_group_and_number == self._map_group_and_number
            )
        else:
            return NotImplemented

    @property
    def map_group_and_number(self) -> tuple[int, int]:
        return self._map_group_and_number[0], self._map_group_and_number[1]

    @cached_property
    def map_location(self) -> MapLocation:
        try:
            map_group_and_number = get_save_block(1, 4, 2)
        except Exception:
            map_group_and_number = self._object_event.map_group, self._object_event.map_num

        return MapLocation(
            read_symbol("gMapHeader"),
            map_group_and_number[0],
            map_group_and_number[1],
            self._object_event.current_coords,
        )

    @property
    def map_location_in_front(self) -> MapLocation | None:
        """
        Returns the map tile in front of the player i.e. the tile the player avatar
        is looking at.
        This only works if that tile is on the same map, otherwise `None` will be
        returned.
        """
        targeted_coordinates = calculate_targeted_coords(self.local_coordinates, self.facing_direction)
        open_map = self.map_location
        if 0 <= targeted_coordinates[0] < open_map.map_size[0] and 0 <= targeted_coordinates[1] < open_map.map_size[1]:
            return MapLocation(read_symbol("gMapHeader"), open_map.map_group, open_map.map_number, targeted_coordinates)

    @property
    def local_coordinates(self) -> tuple[int, int]:
        return self._object_event.current_coords

    @property
    def flags(self) -> AvatarFlags:
        return AvatarFlags(self._player_avatar_data[0])

    @property
    def is_on_bike(self) -> bool:
        return AvatarFlags.OnAcroBike in self.flags or AvatarFlags.OnMachBike in self.flags

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
        flags = {flag.name: flag in self.flags for flag in AvatarFlags}
        return {
            "map_group_and_number": self.map_group_and_number,
            "local_coordinates": self.local_coordinates,
            "running_state": self.running_state.name,
            "tile_transition_state": self.tile_transition_state.name,
            "acro_bike_state": self.acro_bike_state.name,
            "on_bike": self.is_on_bike,
            "facing": self.facing_direction,
            "flags": flags,
        }


class Player:
    def __init__(self, save_block_1: bytes, save_block_2: bytes, encryption_key: bytes):
        self._save_block_1 = save_block_1
        self._save_block_2 = save_block_2
        self._encryption_key = encryption_key

    def __eq__(self, other):
        if isinstance(other, Player):
            return other._save_block_1 == self._save_block_1 and other._save_block_2 == self._save_block_2
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Player):
            return other._save_block_1 != self._save_block_1 or other._save_block_2 != self._save_block_2
        else:
            return NotImplemented

    @property
    def name(self) -> str:
        return decode_string(self._save_block_2[:8])

    @property
    def gender(self) -> Literal["male", "female"]:
        return "male" if self._save_block_2[8] == 0 else "female"

    @property
    def trainer_id(self) -> int:
        return unpack_uint16(self._save_block_2[0x0A:0x0C])

    @property
    def secret_id(self) -> int:
        return unpack_uint16(self._save_block_2[0x0C:0x0E])

    @property
    def money(self) -> int:
        return unpack_uint32(self._save_block_1[:4]) ^ unpack_uint32(self._encryption_key)

    @property
    def coins(self) -> int:
        return unpack_uint16(self._save_block_1[4:6]) ^ (unpack_uint32(self._encryption_key) & 0xFFFF)

    @property
    def registered_item(self) -> Item | None:
        item_index = unpack_uint16(self._save_block_1[6:8])
        if item_index == 0 or item_index > 376:
            return None
        else:
            return get_item_by_index(item_index)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "gender": self.gender,
            "trainer_id": self.trainer_id,
            "secret_id": self.secret_id,
            "money": self.money,
            "coins": self.coins,
            "registered_item": self.registered_item.name if self.registered_item is not None else None,
        }


def get_player() -> Player:
    if state_cache.player.age_in_frames == 0:
        return state_cache.player.value

    if context.rom.is_rse:
        save_block_1_offset = 0x490
        encryption_key_offset = 0xAC
    else:
        save_block_1_offset = 0x290
        encryption_key_offset = 0xF20

    save_block_1 = get_save_block(1, offset=save_block_1_offset, size=0x08)
    save_block_2 = get_save_block(2, size=0x0E)
    encryption_key = get_save_block(2, encryption_key_offset, 4)

    player = Player(save_block_1, save_block_2, encryption_key)
    state_cache.player = player
    return player


def get_player_avatar() -> PlayerAvatar:
    if state_cache.player_avatar.age_in_frames == 0:
        return state_cache.player_avatar.value

    player_avatar_data = read_symbol("gPlayerAvatar")
    object_event_id = player_avatar_data[5]
    object_event = ObjectEvent(read_symbol("gObjectEvents", object_event_id * 0x24, 0x24))
    map_group_and_number = get_save_block(1, offset=4, size=2)

    player_avatar = PlayerAvatar(object_event, player_avatar_data, map_group_and_number)
    state_cache.player_avatar = player_avatar

    return player_avatar


def player_avatar_is_controllable() -> bool:
    if get_game_state() != GameState.OVERWORLD:
        return False

    player_map_object = get_player_map_object()
    if player_map_object is None:
        return False

    player_map_object_flags = player_map_object.flags
    if (
        "heldMovementActive" not in player_map_object_flags
        or "frozen" in player_map_object_flags
        or AvatarFlags.ForcedMove in get_player_avatar().flags
    ):
        return False

    # When exiting a door in RSE, there is a single frame where the game erroneously reports
    # the player as controllable even though it's still in the exiting animation.
    if task_is_active("Task_ExitDoor") or task_is_active("sub_8080B9C"):
        return False

    return True


def player_avatar_is_standing_still() -> bool:
    return player_avatar_is_controllable() and "heldMovementFinished" in get_player_map_object().flags


def get_player_location() -> tuple[MapFRLG | MapRSE, tuple[int, int]]:
    def get_location_or_raise_runtime_error() -> tuple[MapFRLG | MapRSE, tuple[int, int]]:
        avatar = get_player_avatar()
        if avatar is None:
            raise RuntimeError("Could not figure out the player's location because the player avatar is not active.")

        try:
            map_enum = get_map_enum(avatar.map_group_and_number)
        except ValueError:
            raise RuntimeError(f"The game reported the player to be on an invalid map ({avatar.map_group_and_number})")

        return map_enum, avatar.local_coordinates

    try:
        location = get_location_or_raise_runtime_error()
    except RuntimeError:
        # Very occasionally, the player avatar's location data might be corrupt during a map change.
        # As far as I have been able to observe it, the data has been correct again in the next frame,
        # so in those rare circumstances we just peek ahead by one frame and try again, rather than
        # throwing the error immediately.
        #
        # If the location in the peek-ahead frame is still invalid, the error would be propagated to
        # the bot mode.
        with context.emulator.peek_frame():
            location = get_location_or_raise_runtime_error()

    return location


def player_is_at(map: tuple[int, int] | MapFRLG | MapRSE, coordinates: tuple[int, int]) -> bool:
    location = get_player_location()
    return location[0] == map and location[1] == coordinates
