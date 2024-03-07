from dataclasses import dataclass
from enum import IntEnum
from queue import SimpleQueue, PriorityQueue
from typing import TypeAlias

from modules.context import context
from modules.map import MapLocation, get_map_all_tiles, get_map_data, get_map_objects
from modules.map_data import MapFRLG, MapRSE
from modules.memory import get_event_flag_by_number, get_event_var_by_number

LocationType: TypeAlias = MapLocation | tuple[tuple[int, int] | MapFRLG | MapRSE, tuple[int, int]]


class Direction(IntEnum):
    North = 0
    East = 1
    South = 2
    West = 3

    def opposite(self):
        return Direction((self.value + 2) % 4)


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
            for tile in get_map_all_tiles(map_data):
                accessible_from_direction = [False, False, False, False]
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
                else:
                    accessible_from_direction = [True, True, True, True]

                on_enter_event_triggers = {}
                for event in map_data.coord_events:
                    if event.local_coordinates == tile.local_position:
                        on_enter_event_triggers[event.trigger_var_number] = event.trigger_value

                warps_to = None
                for warp in map_data.warps:
                    if warp.local_coordinates == tile.local_position:
                        destination = warp.destination_location
                        extra_warp_direction = None
                        if tile.tile_type.endswith(" Arrow Warp"):
                            extra_warp_direction = Direction[tile.tile_type.replace(" Arrow Warp", "")]
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
                    )
                )
            for map_object in map_data.objects:
                tile = self._tiles[tile_index(*map_object.local_coordinates)]
                if map_object.flag_id != 0:
                    tile.dynamic_collision_flag = map_object.flag_id
                else:
                    tile.dynamic_object_id = map_object.local_id

        return self._tiles

    def get_tile(self, local_coordinates: tuple[int, int]) -> PathTile:
        try:
            return self.tiles[local_coordinates[1] * self.size[0] + local_coordinates[0]]
        except IndexError:
            a = 1
            return self.tiles[0]

    def get_global_tile(self, global_coordinates: tuple[int, int]) -> PathTile:
        local_coordinates = global_coordinates[0] - self.offset[0], global_coordinates[1] - self.offset[1]
        return self.get_tile(local_coordinates)

    def contains_global_coordinates(self, global_coordinates: tuple[int, int]) -> bool:
        return (
            self.offset[0] <= global_coordinates[0] < self.offset[0] + self.size[0]
            and self.offset[1] <= global_coordinates[1] < self.offset[1] + self.size[1]
        )


_maps: dict[tuple[int, int], PathMap] = {}


def _get_connection_for_direction(map_data: MapLocation, direction: str) -> tuple[tuple[int, int], int] | None:
    for connection in map_data.connections:
        if map_data.map_group == 0 and map_data.map_number == 32:
            a = 1
        if connection.direction == direction:
            return (connection.destination_map_group, connection.destination_map_number), connection.offset
    return None


def _get_all_maps_metadata() -> dict[tuple[int, int], PathMap]:
    global _maps

    if len(_maps) > 0:
        return _maps

    if context.rom.is_rse:
        maps_enum = MapRSE
    else:
        maps_enum = MapFRLG

    # Load basic map data
    for map_address in maps_enum:
        map_data = get_map_data(map_address, (0, 0))
        map_connections = [
            _get_connection_for_direction(map_data, "North"),
            _get_connection_for_direction(map_data, "East"),
            _get_connection_for_direction(map_data, "South"),
            _get_connection_for_direction(map_data, "West"),
        ]
        _maps[map_address.value] = PathMap(map_address.value, map_data.map_size, None, -1, map_connections, None)

    # For each map, find all connected maps and set an offset for each of them
    current_map_level = 0
    for map_address in reversed(_maps):
        map = _maps[map_address]
        if map.offset is None:
            map.offset = (0, 0)
            map.level = current_map_level

            interconnected_maps: set[tuple[int, int]] = {map_address}
            map_queue: SimpleQueue[tuple[int, int]] = SimpleQueue()
            map_queue.put_nowait(map_address)

            while not map_queue.empty():
                map_to_check = _maps[map_queue.get_nowait()]
                for direction in Direction:
                    connection = map_to_check.connections[direction]
                    if connection is not None:
                        connection_address, offset = connection
                        if connection_address not in interconnected_maps:
                            interconnected_maps.add(connection_address)
                            map_queue.put_nowait(connection_address)

                            connected_map = _maps[connection_address]
                            if connected_map.map_group_and_number in ((0, 2), (0, 32)):
                                a = 1
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

    return _maps


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


@dataclass
class Waypoint:
    direction: Direction
    map: tuple[int, int]
    coordinates: tuple[int, int]
    is_warp: bool

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
) -> list[Waypoint]:
    if isinstance(source, MapLocation):
        source_tile = _find_tile_by_location(source)
    else:
        source_tile = _find_tile_by_local_coordinates(source[0], source[1])

    if isinstance(source, MapLocation):
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

    # Get all currently loaded objects so we can use their _actual_ location for obstacle calculations, rather
    # than the initial location of their object templates.
    active_objects: set[tuple[tuple[int, int], int]] = set()
    blocked_coordinates: set[tuple[int, int]] = set()
    for object in get_map_objects():
        if "isPlayer" not in object.flags:
            active_objects.add((object.map_group_and_number, object.local_id))
            current = _find_tile_by_local_coordinates(object.map_group_and_number, object.current_coords)
            previous = _find_tile_by_local_coordinates(object.map_group_and_number, object.previous_coords)
            blocked_coordinates.add(current.global_coordinates)
            blocked_coordinates.add(previous.global_coordinates)

    def cost_heuristic(tile: PathTile) -> int:
        return abs(tile.global_coordinates[0] - destination_tile.global_coordinates[0]) + abs(
            tile.global_coordinates[1] - destination_tile.global_coordinates[1]
        )

    def is_tile_accessible(tile: PathTile, from_direction: Direction, from_elevation: int) -> bool:
        if not tile.accessible_from_direction[from_direction] and not (tile == destination_tile and tile.warps_to):
            return False
        if tile.dynamic_collision_flag is not None and not get_event_flag_by_number(tile.dynamic_collision_flag):
            return False
        if tile.elevation not in (0, 15) and from_elevation != 0 and tile.elevation != from_elevation:
            return False
        if tile.dynamic_object_id and (tile.map.map_group_and_number, tile.dynamic_object_id) not in active_objects:
            return False
        if tile.global_coordinates in blocked_coordinates:
            return False
        return True

    def unroll_path(node: PathNode) -> list[Waypoint]:
        result = []
        while node.came_from is not None:
            if node.came_from.tile.global_coordinates[0] < node.tile.global_coordinates[0]:
                direction = Direction.East
            elif node.came_from.tile.global_coordinates[0] > node.tile.global_coordinates[0]:
                direction = Direction.West
            elif node.came_from.tile.global_coordinates[1] < node.tile.global_coordinates[1]:
                direction = Direction.South
            else:
                direction = Direction.North

            if node.tile.warps_to:
                warp_map, warp_coords, extra_warp_direction = node.tile.warps_to
                if extra_warp_direction is not None:
                    result.append(Waypoint(extra_warp_direction, warp_map, warp_coords, True))
                    waypoint = Waypoint(
                        direction, node.tile.map.map_group_and_number, node.tile.local_coordinates, False
                    )
                else:
                    waypoint = Waypoint(direction, warp_map, warp_coords, True)

            else:
                waypoint = Waypoint(direction, node.tile.map.map_group_and_number, node.tile.local_coordinates, False)
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

        for direction in potential_neighbours:
            neighbour_coordinates = potential_neighbours[direction]
            if tile.map.contains_global_coordinates(neighbour_coordinates):
                neighbour = tile.map.get_global_tile(neighbour_coordinates)
            else:
                neighbour = _find_tile_by_global_coordinates(neighbour_coordinates, map_level)

            if neighbour is None or not is_tile_accessible(neighbour, direction, node.elevation):
                continue

            if avoid_encounters and neighbour.has_encounters:
                cost = node.current_cost + 1000
            else:
                cost = node.current_cost + 1

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
                new_node = PathNode(neighbour, elevation, node, direction, cost, cost + cost_heuristic(neighbour))
                checked_tiles[neighbour_key] = new_node
                open_queue.put(new_node)

    raise PathFindingError("Could not find a path from (%SOURCE%) to (%DESTINATION%).", source, destination)
