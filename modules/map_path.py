from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from queue import SimpleQueue, PriorityQueue
from typing import TypeAlias

from modules.context import context
from modules.map import MapLocation, get_map_all_tiles, get_map_data, get_map_objects
from modules.map_data import MapFRLG, MapRSE
from modules.memory import get_event_flag, get_event_flag_by_number, get_event_var_by_number
from modules.pokemon_party import get_party

LocationType: TypeAlias = MapLocation | tuple[tuple[int, int] | MapFRLG | MapRSE, tuple[int, int]]


class Direction(IntEnum):
    North = 0
    East = 1
    South = 2
    West = 3

    def opposite(self):
        return Direction((self.value + 2) % 4)

    def button_name(self):
        if self is Direction.North:
            return "Up"
        elif self is Direction.East:
            return "Right"
        elif self is Direction.South:
            return "Down"
        else:
            return "Left"

    @staticmethod
    def from_string(value: str) -> "Direction":
        match value.lower():
            case "up" | "north":
                return Direction.North
            case "right" | "east":
                return Direction.East
            case "down" | "south":
                return Direction.South
            case "left" | "west":
                return Direction.West
            case _:
                raise RuntimeError(f"Value {value} could not be converted into a direction.")


@dataclass
class PathTile:
    map: "PathMap"
    local_coordinates: tuple[int, int]
    elevation: int
    has_encounters: bool
    accessible_from_direction: list[bool]
    dynamic_collision_flag: int | None
    dynamic_object_id: int | None
    on_enter_event_triggers: dict[int, int]
    warps_to: tuple[tuple[int, int], tuple[int, int], Direction | None] | None
    waterfall_to: tuple[int, int] | None
    muddy_slope_to: tuple[int, int] | None
    forced_movement_to: tuple[tuple[int, int], tuple[int, int], int] | None
    needs_acro_bike: bool
    needs_bunny_hop: bool

    @property
    def global_coordinates(self) -> tuple[int, int]:
        return self.local_coordinates[0] + self.map.offset[0], self.local_coordinates[1] + self.map.offset[1]


@dataclass
class PathMap:
    map_group_and_number: tuple[int, int]
    size: tuple[int, int]
    offset: tuple[int, int] | None
    level: int
    connections: list[tuple[tuple[int, int], int] | None]
    _tiles: list[PathTile] | None

    @property
    def tiles(self) -> list[PathTile]:
        if self._tiles is None:
            map_data = get_map_data(self.map_group_and_number, (0, 0))

            def tile_index(x: int, y: int):
                return y * map_data.map_size[0] + x

            self._tiles = []
            all_tiles = get_map_all_tiles(map_data)
            for tile in all_tiles:
                accessible_from_direction = [False, False, False, False]
                waterfall_to = None
                forced_movement_to = None
                muddy_slope_to = None
                needs_acro_bike = False
                needs_bunny_hop = False
                if tile.collision != 0:
                    if (
                        tile.tile_type.startswith("Jump ")
                        or tile.tile_type.startswith("Walk ")
                        or tile.tile_type.startswith("Slide ")
                    ):
                        _, passable_directions = tile.tile_type.replace(" and ", "/").split(" ")
                        for direction in passable_directions.split("/"):
                            dir = Direction[direction]
                            accessible_from_direction[dir] = True
                elif tile.tile_type.startswith("Impassable "):
                    impassable_directions = tile.tile_type[11:].replace(" and ", "/").split("/")
                    for direction in impassable_directions:
                        dir = Direction[direction]
                        accessible_from_direction[dir.opposite()] = True
                elif tile.tile_type == "Waterfall":
                    tile_south = all_tiles[tile_index(tile.local_position[0], tile.local_position[1] + 1)]
                    if tile_south is not None:
                        if tile_south.tile_type != "Waterfall":
                            waterfall_to = tile
                            while waterfall_to.tile_type == "Waterfall":
                                if waterfall_to.local_position[1] == 0:
                                    waterfall_to = None
                                    break
                                else:
                                    waterfall_to = all_tiles[
                                        tile_index(waterfall_to.local_position[0], waterfall_to.local_position[1] - 1)
                                    ]
                    tile_north = all_tiles[tile_index(tile.local_position[0], tile.local_position[1] - 1)]
                    if tile_north is not None:
                        if tile_north.tile_type != "Waterfall":
                            waterfall_to = tile
                            while waterfall_to.tile_type == "Waterfall":
                                if waterfall_to.local_position[1] == map_data.map_size[1] - 1:
                                    waterfall_to = None
                                    break
                                else:
                                    waterfall_to = all_tiles[
                                        tile_index(waterfall_to.local_position[0], waterfall_to.local_position[1] + 1)
                                    ]
                elif tile.tile_type == "Muddy Slope":
                    tile_south = all_tiles[tile_index(tile.local_position[0], tile.local_position[1] + 1)]
                    if tile_south is not None:
                        if tile_south.tile_type != "Muddy Slope":
                            muddy_slope_to = tile
                            while muddy_slope_to.tile_type == "Muddy Slope":
                                if muddy_slope_to.local_position[1] == 0:
                                    muddy_slope_to = None
                                    break
                                else:
                                    muddy_slope_to = all_tiles[
                                        tile_index(
                                            muddy_slope_to.local_position[0], muddy_slope_to.local_position[1] - 1
                                        )
                                    ]
                    tile_north = all_tiles[tile_index(tile.local_position[0], tile.local_position[1] - 1)]
                    if tile_north is not None:
                        if tile_north.tile_type != "Muddy Slope":
                            muddy_slope_to = tile
                            while muddy_slope_to.tile_type == "Muddy Slope":
                                if muddy_slope_to.local_position[1] == map_data.map_size[1] - 1:
                                    muddy_slope_to = None
                                    break
                                else:
                                    muddy_slope_to = all_tiles[
                                        tile_index(
                                            muddy_slope_to.local_position[0], muddy_slope_to.local_position[1] + 1
                                        )
                                    ]
                elif tile.tile_type in ("Horizontal Rail", "Isolated Horizontal Rail"):
                    needs_acro_bike = True
                    accessible_from_direction = [False, True, False, True]
                elif tile.tile_type in ("Vertical Rail", "Isolated Vertical Rail"):
                    needs_acro_bike = True
                    accessible_from_direction = [True, False, True, False]
                elif tile.tile_type == "Bumpy Slope":
                    needs_acro_bike = True
                    needs_bunny_hop = True
                    accessible_from_direction = [True, False, False, False]
                elif tile.tile_type.endswith(" Current"):
                    if tile.tile_type == "Eastward Current":
                        accessible_from_direction = [True, True, True, False]
                    elif tile.tile_type == "Westward Current":
                        accessible_from_direction = [True, False, True, True]
                    elif tile.tile_type == "Northward Current":
                        accessible_from_direction = [True, True, False, True]
                    elif tile.tile_type == "Southward Current":
                        accessible_from_direction = [False, True, True, True]

                    destination = all_tiles[tile_index(tile.local_position[0], tile.local_position[1])]
                    steps = 0
                    while destination.tile_type.endswith(" Current"):
                        current_map = destination.map_group_and_number
                        x, y = destination.local_position
                        if destination.tile_type == "Eastward Current":
                            if x >= destination.map_size[0] - 1:
                                x = 0
                                current_map, offset = _get_connection_for_direction(destination, "East")
                                y += offset
                            else:
                                x += 1
                        elif destination.tile_type == "Westward Current":
                            if x <= 0:
                                current_map, offset = _get_connection_for_direction(destination, "West")
                                y += offset
                                x = get_map_data(current_map, (0, 0)).map_size[0] - 1
                            else:
                                x -= 1
                        elif destination.tile_type == "Southward Current":
                            if y >= destination.map_size[1] - 1:
                                y = 0
                                current_map, offset = _get_connection_for_direction(destination, "South")
                                x += offset
                            else:
                                y += 1
                        elif destination.tile_type == "Northward Current":
                            if y <= 0:
                                current_map, offset = _get_connection_for_direction(destination, "North")
                                x += offset
                                y = get_map_data(current_map, (0, 0)).map_size[1] - 1
                            else:
                                y -= 1
                        next_tile = get_map_data(current_map, (x, y))
                        if next_tile.elevation == 1 and not next_tile.collision:
                            destination = next_tile
                            steps += 1
                        else:
                            break
                    forced_movement_to = destination, steps
                else:
                    accessible_from_direction = [True, True, True, True]

                on_enter_event_triggers = {}
                for event in map_data.coord_events:
                    if event.local_coordinates == tile.local_position and event.type != "weather":
                        on_enter_event_triggers[event.trigger_var_number] = event.trigger_value

                warps_to = None
                for warp in map_data.warps:
                    if warp.local_coordinates == tile.local_position:
                        destination = warp.destination_location
                        extra_warp_direction = None
                        if tile.tile_type.endswith(" Arrow Warp"):
                            match tile.tile_type:
                                case "North Arrow Warp":
                                    extra_warp_direction = Direction.North
                                case "South Arrow Warp" | "Water South Arrow Warp":
                                    extra_warp_direction = Direction.South
                                case "East Arrow Warp":
                                    extra_warp_direction = Direction.East
                                case "West Arrow Warp":
                                    extra_warp_direction = Direction.West
                        warps_to = (
                            (destination.map_group, destination.map_number),
                            destination.local_position,
                            extra_warp_direction,
                        )

                self._tiles.append(
                    PathTile(
                        self,
                        tile.local_position,
                        tile.elevation,
                        tile.has_encounters,
                        accessible_from_direction,
                        None,
                        None,
                        on_enter_event_triggers,
                        warps_to,
                        waterfall_to.local_position if waterfall_to is not None else None,
                        muddy_slope_to.local_position if muddy_slope_to is not None else None,
                        (
                            (
                                forced_movement_to[0].map_group_and_number,
                                forced_movement_to[0].local_position,
                                forced_movement_to[1],
                            )
                            if forced_movement_to is not None and forced_movement_to[1] > 0
                            else None
                        ),
                        needs_acro_bike,
                        needs_bunny_hop,
                    )
                )
            for map_object in map_data.objects:
                try:
                    tile = self._tiles[tile_index(*map_object.local_coordinates)]
                except IndexError:
                    # If loaded map object data is invalid, a map object's coordinates might be out of bounds.
                    # This `except` block catches that case and pretends like the object is not loaded at all.
                    continue
                if map_object.flag_id != 0:
                    tile.dynamic_collision_flag = map_object.flag_id
                tile.dynamic_object_id = map_object.local_id

        return self._tiles

    def get_tile(self, local_coordinates: tuple[int, int]) -> PathTile:
        return self.tiles[local_coordinates[1] * self.size[0] + local_coordinates[0]]

    def get_global_tile(self, global_coordinates: tuple[int, int]) -> PathTile:
        local_coordinates = global_coordinates[0] - self.offset[0], global_coordinates[1] - self.offset[1]
        return self.get_tile(local_coordinates)

    def contains_global_coordinates(self, global_coordinates: tuple[int, int]) -> bool:
        return (
            self.offset[0] <= global_coordinates[0] < self.offset[0] + self.size[0]
            and self.offset[1] <= global_coordinates[1] < self.offset[1] + self.size[1]
        )


_maps: dict[str, dict[tuple[int, int], PathMap]] = {}


def _get_connection_for_direction(map_data: MapLocation, direction: str) -> tuple[tuple[int, int], int] | None:
    for connection in map_data.connections:
        if connection.direction == direction:
            return (connection.destination_map_group, connection.destination_map_number), connection.offset
    return None


def _get_all_maps_metadata() -> dict[tuple[int, int], PathMap]:
    global _maps

    game_key = context.rom.id
    if game_key in _maps:
        return _maps[game_key]

    _maps[game_key] = {}

    if context.rom.is_rse:
        maps_enum = MapRSE
    else:
        maps_enum = MapFRLG

    # Load basic map data
    for map_address in maps_enum:
        if context.rom.is_rs and not map_address.exists_on_rs:
            continue

        map_data = get_map_data(map_address, (0, 0))
        if context.rom.is_rs and map_address.name.startswith("BATTLE_PYRAMID_"):
            # For some reason, a few Battle Pyramid maps indicate that they are connected to the
            # Hoenn Safari Zone, which confuses pathfinding (particularly for Muddy Slope traversal)
            # in the SZ. So we'll just ignore those connections.
            map_connections = [None, None, None, None]
        else:
            map_connections = [
                _get_connection_for_direction(map_data, "North"),
                _get_connection_for_direction(map_data, "East"),
                _get_connection_for_direction(map_data, "South"),
                _get_connection_for_direction(map_data, "West"),
            ]
        _maps[game_key][map_address.value] = PathMap(
            map_address.value, map_data.map_size, None, -1, map_connections, None
        )

    # For each map, find all connected maps and set an offset for each of them
    current_map_level = 0
    for map_address in reversed(_maps[game_key]):
        map = _maps[game_key][map_address]
        if map.offset is None:
            map.offset = (0, 0)
            map.level = current_map_level

            interconnected_maps: set[tuple[int, int]] = {map_address}
            map_queue: SimpleQueue[tuple[int, int]] = SimpleQueue()
            map_queue.put_nowait(map_address)

            while not map_queue.empty():
                map_to_check = _maps[game_key][map_queue.get_nowait()]
                for direction in Direction:
                    connection = map_to_check.connections[direction]
                    if connection is not None:
                        connection_address, offset = connection
                        if connection_address not in interconnected_maps:
                            interconnected_maps.add(connection_address)
                            map_queue.put_nowait(connection_address)

                            connected_map = _maps[game_key][connection_address]
                            connected_map.level = current_map_level
                            if direction is Direction.North:
                                connected_map.offset = (
                                    map_to_check.offset[0] + offset,
                                    map_to_check.offset[1] - connected_map.size[1],
                                )
                            elif direction is Direction.East:
                                connected_map.offset = (
                                    map_to_check.offset[0] + map_to_check.size[0],
                                    map_to_check.offset[1] + offset,
                                )
                            elif direction is Direction.South:
                                connected_map.offset = (
                                    map_to_check.offset[0] + offset,
                                    map_to_check.offset[1] + map_to_check.size[1],
                                )
                            elif direction is Direction.West:
                                connected_map.offset = (
                                    map_to_check.offset[0] - connected_map.size[0],
                                    map_to_check.offset[1] + offset,
                                )
                            else:
                                raise RuntimeError("Invalid direction")

            current_map_level += 1

    return _maps[game_key]


def _get_map_metadata(map_address: tuple[int, int]) -> PathMap:
    return _get_all_maps_metadata()[map_address]


def _find_tile_by_global_coordinates(global_coordinates: tuple[int, int], map_level: int) -> PathTile | None:
    maps = _get_all_maps_metadata()
    for path_map_address in maps:
        path_map = maps[path_map_address]
        if path_map.level == map_level and path_map.contains_global_coordinates(global_coordinates):
            return path_map.get_global_tile(global_coordinates)
    return None


def _find_tile_by_location(map_location: MapLocation) -> PathTile:
    return _get_map_metadata((map_location.map_group, map_location.map_number)).get_tile(map_location.local_position)


def _find_tile_by_local_coordinates(
    map: tuple[int, int] | MapFRLG | MapFRLG, local_coordinates: tuple[int, int]
) -> PathTile:
    if not isinstance(map, tuple):
        map = map.value
    return _get_map_metadata(map).get_tile(local_coordinates)


class PathFindingError(RuntimeError):

    def __init__(self, message: str, source: LocationType | None = None, destination: LocationType | None = None):
        if source is not None:
            message = message.replace("%SOURCE%", self._debug_tile_name(source))

        if destination is not None:
            message = message.replace("%DESTINATION%", self._debug_tile_name(destination))

        super().__init__(message)

    @staticmethod
    def _debug_tile_name(location: LocationType) -> str:
        if isinstance(location, MapLocation):
            map_group, map_number = location.map_group_and_number
            local_coordinates = location.local_position
        else:
            map_group, map_number = location[0]
            local_coordinates = location[1]

        if context.rom.is_rse:
            map_name = MapRSE((map_group, map_number)).name
        else:
            map_name = MapFRLG((map_group, map_number)).name
        return f"{local_coordinates[0]}/{local_coordinates[1]} @ {map_name}"


@dataclass
class PathNode:
    tile: PathTile
    elevation: int
    came_from: "PathNode | None"
    previous_direction: Direction | None
    current_cost: int
    estimated_total_cost: int
    is_waterfall: bool = False
    is_diving: bool = False
    is_emerging: bool = False
    is_acro_bike_side_jump: bool = False
    is_mach_bike_slope: bool = False

    def __eq__(self, other):
        if isinstance(other, PathNode):
            return self.estimated_total_cost == other.estimated_total_cost
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, PathNode):
            return self.estimated_total_cost != other.estimated_total_cost
        else:
            return NotImplemented

    def __lt__(self, other):
        if isinstance(other, PathNode):
            return self.estimated_total_cost < other.estimated_total_cost
        else:
            return NotImplemented

    def __le__(self, other):
        if isinstance(other, PathNode):
            return self.estimated_total_cost <= other.estimated_total_cost
        else:
            return NotImplemented

    def __gt__(self, other):
        if isinstance(other, PathNode):
            return self.estimated_total_cost > other.estimated_total_cost
        else:
            return NotImplemented

    def __ge__(self, other):
        if isinstance(other, PathNode):
            return self.estimated_total_cost >= other.estimated_total_cost
        else:
            return NotImplemented


class WaypointAction(Enum):
    Surf = auto()
    Waterfall = auto()
    Dive = auto()
    Emerge = auto()
    AcroBikeMount = auto()
    AcroBikeSideJump = auto()
    AcroBikeBunnyHop = auto()
    MachBikeMount = auto()
    MachBikeSlope = auto()


@dataclass
class Waypoint:
    direction: Direction
    map: tuple[int, int]
    coordinates: tuple[int, int]
    is_warp: bool
    action: WaypointAction | None = None

    @property
    def walking_direction(self) -> str:
        return {
            Direction.North: "Up",
            Direction.East: "Right",
            Direction.South: "Down",
            Direction.West: "Left",
        }[self.direction]


def calculate_path(
    source: LocationType,
    destination: LocationType,
    avoid_encounters: bool = True,
    avoid_scripted_events: bool = True,
    no_surfing: bool = False,
    has_acro_bike: bool = False,
    has_mach_bike: bool = False,
) -> list[Waypoint]:
    """
    Attempts to calculate the best path from one tile to another.

    This function supports paths across several maps, but only if they are connected. It is not
    able to use warps or fly.

    :param source: Map and coordinates of the source tile.
    :param destination: Map and coordinates of the destination tile. If this tile is a warp tile,
                        it will follow the warp. So setting a door as the destination will lead
                        to the path leading to the map that door connects to.
    :param avoid_encounters: If `True`, the pathfinding algorithm will _try_ to avoid tiles that
                             may have encounters such as tall grass and water. But if there is no
                             other way, it will still use those tiles. Also, it does not check for
                             Repel or any other condition that might mean we wouldn't actually get
                             any encounters on these tiles.
    :param avoid_scripted_events: If `True`, the pathfinding algorithm will _try_ to avoid tiles
                                  that might trigger scripted events. But if there is no other way,
                                  it will still use those tiles.
    :param no_surfing: If `True`, the pathfinding algorithm will not use any path that would
                       require using surf, even if that is the only way. If the source tile is a
                       water tile (i.e. the player is already surfing), it will still exit the
                       water just fine, but not re-enter it.
    :param has_acro_bike: If `True`, the pathfinding algorithm will try to traverse the rails that
                          can only be accessed by Acro Bike.
    :param has_mach_bike: If `True`, the pathfinding algorithm will traverse Muddy Slopes using the
                          Mach Bike.
    :return: A list of waypoints describing the best path to take. If no valid path could be found,
             a `PathFindingError` is raised.
    """

    if isinstance(source, MapLocation):
        source_tile = _find_tile_by_location(source)
    else:
        source_tile = _find_tile_by_local_coordinates(source[0], source[1])

    if isinstance(destination, MapLocation):
        destination_tile = _find_tile_by_location(destination)
    else:
        destination_tile = _find_tile_by_local_coordinates(destination[0], destination[1])

    if source_tile.map.level != destination_tile.map.level:
        raise PathFindingError(
            "Source (%SOURCE%) and destination (%DESTINATION%) are not on connected maps (note that warps don't count.)",
            source,
            destination,
        )

    map_level = source_tile.map.level

    # Helper variables that are only used for caching in `can_surf()`, `can_dive()` and
    # `can_waterfall()` so we don't have to do all the lookups for each tile.
    _can_surf = None
    _can_dive = None
    _can_waterfall = None

    def can_surf():
        nonlocal _can_surf
        if _can_surf is None:
            _can_surf = not no_surfing and get_event_flag("BADGE05_GET") and get_party().has_pokemon_with_move("Surf")
        return _can_surf

    def can_dive():
        nonlocal _can_dive
        if _can_dive is None:
            _can_dive = (
                context.rom.is_rse and get_event_flag("BADGE07_GET") and get_party().has_pokemon_with_move("Dive")
            )
        return _can_dive

    def can_waterfall():
        nonlocal _can_waterfall
        if _can_waterfall is None:
            _can_waterfall = (
                context.rom.is_rse and get_event_flag("BADGE08_GET") and get_party().has_pokemon_with_move("Waterfall")
            )
        return _can_waterfall

    # Get all currently loaded objects so we can use their _actual_ location for obstacle calculations, rather
    # than the initial location of their object templates.
    active_objects: set[tuple[tuple[int, int], int]] = set()
    blocked_coordinates: set[tuple[int, int]] = set()
    for object in get_map_objects():
        if "isPlayer" not in object.flags:
            try:
                current = _find_tile_by_local_coordinates(object.map_group_and_number, object.current_coords)
                previous = _find_tile_by_local_coordinates(object.map_group_and_number, object.previous_coords)
                active_objects.add((object.map_group_and_number, object.local_id))
                blocked_coordinates.add(current.global_coordinates)
                blocked_coordinates.add(previous.global_coordinates)
            except (KeyError, IndexError):
                # If there is an object with invalid data (which could happen if it's being processed while we
                # are querying the data), we simply ignore it. Instead, the object template will be used and
                # in the event that we run into the object, a timeout will trigger and the route recalculated.
                pass

    def cost_heuristic(tile: PathTile) -> int:
        return abs(tile.global_coordinates[0] - destination_tile.global_coordinates[0]) + abs(
            tile.global_coordinates[1] - destination_tile.global_coordinates[1]
        )

    def is_tile_accessible(tile: PathTile, from_direction: Direction, from_elevation: int) -> bool:
        if tile.waterfall_to is not None and from_direction is Direction.North and can_waterfall():
            return True
        elif tile.waterfall_to is not None and from_direction is Direction.South:
            return True
        if tile.needs_acro_bike:
            if not tile.needs_bunny_hop or from_direction is Direction.North:
                if not has_acro_bike:
                    return False
        elif tile.muddy_slope_to:
            if from_direction is Direction.North and not has_mach_bike:
                return False
        elif not tile.accessible_from_direction[from_direction] and not (tile == destination_tile and tile.warps_to):
            return False
        if tile.dynamic_collision_flag is not None and not get_event_flag_by_number(tile.dynamic_collision_flag):
            if (
                tile.dynamic_object_id is None
                or (tile.map.map_group_and_number, tile.dynamic_object_id) not in active_objects
            ):
                return False
        if tile.elevation == 1 and from_elevation == 3 and can_surf():
            return True
        if tile.elevation == 3 and from_elevation == 1:
            return True
        if tile.elevation not in (0, 15) and from_elevation != 0 and tile.elevation != from_elevation:
            return False
        if (
            tile.dynamic_collision_flag is None
            and tile.dynamic_object_id
            and (tile.map.map_group_and_number, tile.dynamic_object_id) not in active_objects
        ):
            return False
        if tile.global_coordinates in blocked_coordinates:
            return False
        return True

    def unroll_path(node: PathNode) -> list[Waypoint]:
        result = []
        while node.came_from is not None:
            direction = node.previous_direction
            if node.tile.warps_to and len(result) == 0:
                warp_map, warp_coords, extra_warp_direction = node.tile.warps_to
                if extra_warp_direction is not None:
                    result.append(Waypoint(extra_warp_direction, warp_map, warp_coords, True))
                    waypoint = Waypoint(
                        direction, node.tile.map.map_group_and_number, node.tile.local_coordinates, False
                    )
                else:
                    waypoint = Waypoint(direction, warp_map, warp_coords, True)

            else:
                if node.came_from.elevation == 3 and node.elevation == 1:
                    action = WaypointAction.Surf
                elif node.is_waterfall and direction is Direction.North:
                    action = WaypointAction.Waterfall
                elif len(result) > 0 and result[-1].action is WaypointAction.MachBikeSlope:
                    action = WaypointAction.MachBikeMount
                elif node.is_mach_bike_slope:
                    action = WaypointAction.MachBikeSlope
                elif node.tile.needs_bunny_hop:
                    action = WaypointAction.AcroBikeBunnyHop
                elif node.tile.needs_acro_bike and not node.came_from.tile.needs_acro_bike:
                    action = WaypointAction.AcroBikeMount
                elif node.tile.needs_acro_bike and not node.tile.accessible_from_direction[direction.value]:
                    action = WaypointAction.AcroBikeSideJump
                else:
                    action = None

                waypoint = Waypoint(
                    direction, node.tile.map.map_group_and_number, node.tile.local_coordinates, False, action
                )
            result.append(waypoint)

            node = node.came_from
        return list(reversed(result))

    checked_tiles: dict[tuple[int, int, int], PathNode] = {}
    open_queue: PriorityQueue[PathNode] = PriorityQueue()
    open_queue.put(PathNode(source_tile, source_tile.elevation, None, None, 0, cost_heuristic(source_tile)))

    while not open_queue.empty():
        node = open_queue.get()
        tile = node.tile
        coords = tile.global_coordinates

        if coords == destination_tile.global_coordinates:
            return unroll_path(node)

        potential_neighbours = {
            Direction.North: (coords[0], coords[1] - 1),
            Direction.East: (coords[0] + 1, coords[1]),
            Direction.South: (coords[0], coords[1] + 1),
            Direction.West: (coords[0] - 1, coords[1]),
        }

        # There is a 2-tile gap in global coordinates between Route 104 and Rustboro City
        # because some other maps in the global map space are slightly longer. This makes
        # them connect anyway.
        if context.rom.is_rse and tile.map.map_group_and_number == MapRSE.ROUTE104 and tile.local_coordinates[1] == 0:
            potential_neighbours[Direction.North] = (
                potential_neighbours[Direction.North][0],
                potential_neighbours[Direction.North][1] - 2,
            )
        elif (
            context.rom.is_rse
            and tile.map.map_group_and_number == MapRSE.RUSTBORO_CITY
            and tile.local_coordinates[1] == 59
        ):
            potential_neighbours[Direction.South] = (
                potential_neighbours[Direction.South][0],
                potential_neighbours[Direction.South][1] + 2,
            )

        for direction in potential_neighbours:
            neighbour_coordinates = potential_neighbours[direction]
            if tile.map.contains_global_coordinates(neighbour_coordinates):
                neighbour = tile.map.get_global_tile(neighbour_coordinates)
            else:
                neighbour = _find_tile_by_global_coordinates(neighbour_coordinates, map_level)

            if neighbour is None or not is_tile_accessible(neighbour, direction, node.elevation):
                continue

            if neighbour.warps_to is not None and neighbour.global_coordinates != destination_tile.global_coordinates:
                cost = 1000000
            else:
                cost = node.current_cost + 1

            # This handles the case where beginning to surf is required. The dialogue and animation
            # take around 267 frames (depending on the length of the Pokémon's name), whereas a
            # regular step takes 16 frames. So starting to surf is around 17× more expensive than
            # just walking.
            if tile.elevation == 3 and neighbour.elevation == 1:
                cost += 16

            # This handles the opposite case, i.e. jumping from water to land. This takes 33 frames,
            # so about twice as much as a regular step.
            if tile.elevation == 1 and neighbour.elevation == 3:
                cost += 1

            # This handles cases where we need to surf up a waterfall. Enabling the Waterfall move
            # takes around 195 frames (depending on the length of the Pokémon's name) and another
            # 41 frames for each tile climbed.
            is_waterfall = False
            if neighbour.waterfall_to is not None:
                waterfall_height = abs(neighbour.local_coordinates[1] - neighbour.waterfall_to[1])
                cost += int(round((195 + 41 * waterfall_height) / 16))
                neighbour = tile.map.get_tile(neighbour.waterfall_to)
                neighbour_coordinates = neighbour.global_coordinates
                is_waterfall = True

            is_muddy_slope = False
            if neighbour.muddy_slope_to is not None and direction is Direction.North:
                muddy_slope_to = neighbour.map.get_tile(neighbour.muddy_slope_to)
                muddy_slope_height = abs(neighbour.local_coordinates[1] - neighbour.muddy_slope_to[1])
                cost += muddy_slope_height
                neighbour = _find_tile_by_global_coordinates(
                    (muddy_slope_to.global_coordinates[0], muddy_slope_to.global_coordinates[1] - 2), map_level
                )
                neighbour_coordinates = neighbour.global_coordinates
                is_muddy_slope = True

            if neighbour.forced_movement_to is not None:
                cost += neighbour.forced_movement_to[2]
                if neighbour.forced_movement_to[2] < 0:
                    raise RuntimeError(
                        f"Encountered a negative-length forced movement from {neighbour.local_coordinates} to {neighbour.forced_movement_to}."
                    )
                neighbour = _find_tile_by_local_coordinates(
                    neighbour.forced_movement_to[0], neighbour.forced_movement_to[1]
                )
                neighbour_coordinates = neighbour.global_coordinates

            if neighbour.needs_bunny_hop:
                cost += 1

            if neighbour.has_encounters and avoid_encounters:
                cost += 1000

            # Prefer walking in a straight line if possible.
            if node.previous_direction != direction:
                cost += 0.1

            if avoid_scripted_events:
                for var_number in neighbour.on_enter_event_triggers:
                    if get_event_var_by_number(var_number) == neighbour.on_enter_event_triggers[var_number]:
                        cost += 10000

            if neighbour.elevation == 15:
                elevation = node.elevation
            else:
                elevation = neighbour.elevation

            neighbour_key = neighbour_coordinates[0], neighbour_coordinates[1], elevation
            if neighbour_key not in checked_tiles or checked_tiles[neighbour_key].current_cost > cost:
                new_node = PathNode(
                    neighbour,
                    elevation,
                    node,
                    direction,
                    cost,
                    cost + cost_heuristic(neighbour),
                    is_waterfall,
                    is_mach_bike_slope=is_muddy_slope,
                )
                checked_tiles[neighbour_key] = new_node
                open_queue.put(new_node)

    raise PathFindingError("Could not find a path from (%SOURCE%) to (%DESTINATION%).", source, destination)
