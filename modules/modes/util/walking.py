import queue
from typing import Generator, Iterable

from modules.context import context
from modules.debug import debug
from modules.map import (
    MapLocation,
    get_map_data_for_current_position,
    get_map_all_tiles,
    get_map_data,
    get_map_objects,
    get_player_map_object,
)
from modules.map_data import MapFRLG, MapRSE
from modules.map_path import calculate_path, Waypoint, PathFindingError
from modules.memory import GameState, get_event_flag_by_number, get_game_state
from modules.player import (
    RunningState,
    AcroBikeState,
    TileTransitionState,
    get_player_avatar,
    player_avatar_is_controllable,
    player_avatar_is_standing_still,
    player_is_at,
)
from modules.tasks import get_global_script_context
from .sleep import wait_for_n_frames
from .._interface import BotModeError


@debug.track
def walk_to(destination_coordinates: tuple[int, int], run: bool = True) -> Generator:
    """
    Moves the player to a set of coordinates on the same map. Does absolutely no
    collision checking and _will_ get stuck all the time.
    This returns control back to the calling functions _while the player is still moving_.
    To prevent this, you might want to use the `follow_path()` utility function instead.
    :param destination_coordinates: Tuple (x, y) of map-local coordinates of the destination
    :param run: Whether the player should run (hold down B)
    """

    if get_game_state() != GameState.OVERWORLD:
        raise BotModeError("Game is not currently in overworld mode. Cannot walk.")

    context.emulator.reset_held_buttons()

    initial_map = get_player_avatar().map_group_and_number
    while True:
        context.emulator.reset_held_buttons()
        if run:
            context.emulator.hold_button("B")

        avatar = get_player_avatar()
        if avatar.local_coordinates == destination_coordinates:
            break
        if avatar.map_group_and_number != initial_map:
            while get_game_state() != GameState.OVERWORLD:
                yield
            break

        if (avatar.running_state == RunningState.NOT_MOVING and avatar.acro_bike_state == AcroBikeState.NORMAL) or (
            context.rom.is_frlg
            and avatar.tile_transition_state in [TileTransitionState.CENTERING, TileTransitionState.NOT_MOVING]
            and "Std_MsgboxSign" in get_global_script_context().stack
        ):
            if destination_coordinates[0] < avatar.local_coordinates[0]:
                context.emulator.hold_button("Left")
            elif destination_coordinates[0] > avatar.local_coordinates[0]:
                context.emulator.hold_button("Right")
            elif destination_coordinates[1] < avatar.local_coordinates[1]:
                context.emulator.hold_button("Up")
            elif destination_coordinates[1] > avatar.local_coordinates[1]:
                context.emulator.hold_button("Down")

        yield

    context.emulator.reset_held_buttons()


@debug.track
def follow_path(waypoints: Iterable[tuple[int, int]], run: bool = True) -> Generator:
    """
    Moves the player along a given path.

    There is no collision checking, so the path needs to be chosen carefully to ensure it
    doesn't get stuck.

    :param waypoints: List of tuples (x, y) of map-local coordinates of the destination
    :param run: Whether the player should run (hold down B)
    """
    if get_game_state() != GameState.OVERWORLD:
        raise RuntimeError("The game is currently not in the overworld. Cannot navigate.")

    # Make sure that the player avatar can actually be controlled/moved right now.
    if not player_avatar_is_controllable():
        raise RuntimeError("The player avatar is currently not controllable. Cannot navigate.")

    for waypoint in waypoints:
        yield from walk_to(waypoint, run)

    # Wait for player to come to a full stop.
    while not player_avatar_is_standing_still() or get_player_avatar().running_state != RunningState.NOT_MOVING:
        yield


@debug.track
def deprecated_navigate_to_on_current_map(x: int, y: int, run: bool = True) -> Generator:
    """
    (This is an older, now deprecated implementation of a pathfinding navigation function.
    For new code, use `navigate_to()` instead.)

    Tries to walk the player to a given location while circumventing obstacles.

    This is a pretty primitive implementation and only works within a map. If you need to cross
    maps, you have to use this to get to the edge of the first map, then use `walk_one_tile()`
    to cross the map border, and then call this function again to navigate within the second map.

    It attempts to avoid tiles that have encounters (tall grass etc.) but does not currently
    avoid trainers.

    It only works _either_ on land _or_ on water, but won't start or stop to surf.

    :param x: Map-local X coordinate of the destination
    :param y: Map-local Y coordinate of the destination
    :param run: Whether the player should run (hold down B)
    """
    tiles = get_map_all_tiles()
    map_width, map_height = tiles[0].map_size

    def is_tile_accessible(destination: MapLocation, source: MapLocation) -> bool:
        if source.local_position[0] < destination.local_position[0]:
            direction = "East"
        elif source.local_position[0] > destination.local_position[0]:
            direction = "West"
        elif source.local_position[1] < destination.local_position[1]:
            direction = "South"
        else:
            direction = "North"

        if destination.collision:
            may_pass = False
            if (
                destination.tile_type.startswith("Jump ")
                or destination.tile_type.startswith("Walk ")
                or destination.tile_type.startswith("Slide ")
            ):
                _, passable_direction = destination.tile_type.split(" ")
                if direction in passable_direction.split("/"):
                    may_pass = True
            if not may_pass:
                return False
        if source.tile_type.startswith("Impassable "):
            impassable_directions = source.tile_type[11:].split(" and ")
            if direction in impassable_directions:
                return False
        if destination.elevation not in (0, 15) and source.elevation != 0 and source.elevation != destination.elevation:
            return False
        if destination.tile_type == "Door Warp":
            return False
        tile_blocked_by_object = False
        object_event_ids = []
        for map_object in get_map_objects():
            object_event_ids.append(map_object.local_id)
            if "player" not in map_object.flags and destination.local_position in (
                map_object.current_coords,
                map_object.previous_coords,
            ):
                tile_blocked_by_object = True
                break
        for object_template in tiles[0].objects:
            if object_template.local_id in object_event_ids:
                continue
            if object_template.flag_id != 0 and get_event_flag_by_number(object_template.flag_id):
                continue
            if object_template.local_coordinates == destination.local_position:
                tile_blocked_by_object = True
                break
        return not tile_blocked_by_object

    def calculate_path(end_point: tuple[int, int], starting_point: tuple[int, int]) -> list[tuple[int, int]]:
        visited_nodes: dict[tuple[int, int], tuple[int, tuple[int, int]]] = {starting_point: (0, starting_point)}
        node_queue = queue.SimpleQueue()
        node_queue.put(starting_point)

        while not node_queue.empty() and end_point not in visited_nodes:
            coords = node_queue.get()
            tile = tiles[coords[1] * map_width + coords[0]]
            potential_neighbours = {
                "North": (coords[0], coords[1] - 1),
                "West": (coords[0] - 1, coords[1]),
                "South": (coords[0], coords[1] + 1),
                "East": (coords[0] + 1, coords[1]),
            }
            for direction in potential_neighbours:
                n_coords = potential_neighbours[direction]
                if 0 <= n_coords[0] < map_width and 0 <= n_coords[1] < map_height:
                    neighbour = tiles[n_coords[1] * map_width + n_coords[0]]
                    if not is_tile_accessible(neighbour, tile):
                        continue

                    if neighbour.has_encounters:
                        distance = visited_nodes[coords][0] + 1000
                    else:
                        distance = visited_nodes[coords][0] + 1

                    if n_coords not in visited_nodes or visited_nodes[n_coords][0] > distance:
                        visited_nodes[n_coords] = (distance, coords)
                        node_queue.put(n_coords)
                        if n_coords == end_point:
                            break

        if end_point not in visited_nodes:
            raise BotModeError(f"Could not find a path to ({end_point[0]}, {end_point[1]}).")

        current_node = visited_nodes[end_point]
        waypoints = [end_point]
        while current_node[1] != starting_point:
            waypoints.append(current_node[1])
            current_node = visited_nodes[current_node[1]]

        return list(reversed(waypoints))

    while get_player_avatar().local_coordinates != (x, y):
        timeout = 60
        last_known_location = get_player_avatar().local_coordinates
        for _ in follow_path(calculate_path((x, y), last_known_location), run):
            timeout -= 1
            if timeout <= 0 and get_game_state() == GameState.OVERWORLD:
                current_location = get_player_avatar().local_coordinates
                if current_location == last_known_location:
                    for __ in range(16):
                        yield
                    break
                else:
                    last_known_location = current_location
                    timeout += 60
            yield

    context.emulator.reset_held_buttons()
    yield from wait_for_player_avatar_to_be_controllable()


class TimedOutTryingToReachWaypointError(BotModeError):
    def __init__(self, waypoint: Waypoint):
        self.waypoint = waypoint
        if context.rom.is_rse:
            map_name = MapRSE(waypoint.map).name
        else:
            map_name = MapFRLG(waypoint.map).name
        message = f"Did not reach waypoint ({waypoint.coordinates}) @ {map_name} in time."
        super().__init__(message)


@debug.track
def follow_waypoints(path: Iterable[Waypoint], run: bool = True) -> Generator:
    """
    Follows a given set of waypoints.

    Since the `path` parameter can also be a generator function, this function can be used to follow
    looping or dynamically calculated paths.

    This function does not check for obstacles, but if it takes too long to reach a waypoint it will
    fire a `TimedOutTryingToReachWaypointError` exception (which is a child class of `BotModeError`,
    so if unhandled it will just show as a message and put the bot back into manual mode.)

    :param path: A list (or generator) of waypoints to follow.
    :param run: Whether to run (hold `B`.) This is ignored when on a bicycle, since it would be either
                meaningless or actively detrimental (Acro Bike, where it would initiate wheelie mode.)
    """

    if get_game_state() != GameState.OVERWORLD:
        raise BotModeError("The game is currently not in the overworld. Cannot navigate.")

    # Make sure that the player avatar can actually be controlled/moved right now.
    if not player_avatar_is_controllable():
        raise BotModeError("The player avatar is currently not controllable. Cannot navigate.")

    # 'Running' means holding B, which on the Acro Bike leads to doing a Wheelie which is actually
    # slower than normal riding. On other bikes it just doesn't do anything, so if we are riding one,
    # this flag will just be ignored.
    if run and get_player_avatar().is_on_bike:
        run = False

    # For each waypoint (i.e. each step of the path) we set a timeout. If the player avatar does not reach the
    # expected location within that time, we stop the walking. The calling code could use that event to
    # recalculate a new path.
    #
    # Regular steps usually take 16 frames, so the 20-frame timeout should be enough. For warps (walking into doors
    # etc.) a 'step' may take a bit longer due to the map transition. Which is why there is an extra allowance for
    # those cases.
    timeout_in_frames = 20
    extra_timeout_in_frames_for_warps = 280

    current_position = get_map_data_for_current_position()
    for waypoint in path:
        timeout_exceeded = False
        frames_remaining_until_timeout = timeout_in_frames
        if waypoint.is_warp:
            frames_remaining_until_timeout += extra_timeout_in_frames_for_warps

        while not timeout_exceeded and not player_is_at(waypoint.map, waypoint.coordinates):
            player_object = get_player_map_object()

            if get_game_state() == GameState.OVERWORLD:
                frames_remaining_until_timeout -= 1

            if frames_remaining_until_timeout <= 0:
                if player_is_at(current_position.map_group_and_number, current_position.local_position):
                    context.emulator.reset_held_buttons()
                    yield from wait_for_n_frames(16)
                    raise TimedOutTryingToReachWaypointError(waypoint)
                else:
                    current_position = get_map_data_for_current_position()
                    frames_remaining_until_timeout += timeout_in_frames

            # Only pressing the direction keys during the frame where movement is actually registered can help
            # preventing weird overshoot issues in cases where a listener handles an event (like a battle, PokeNav
            # call, ...)
            if player_object is not None and "heldMovementFinished" in player_object.flags:
                context.emulator.hold_button(waypoint.walking_direction)
                if run:
                    context.emulator.hold_button("B")
            else:
                context.emulator.reset_held_buttons()

            yield

    # Wait for player to come to a full stop.
    context.emulator.reset_held_buttons()
    while not player_avatar_is_standing_still() or get_player_avatar().running_state != RunningState.NOT_MOVING:
        yield


@debug.track
def navigate_to(
    map: tuple[int, int] | MapFRLG | MapRSE,
    coordinates: tuple[int, int],
    run: bool = True,
    avoid_encounters: bool = True,
    avoid_scripted_events: bool = True,
) -> Generator:
    """
    Tries to walk the player to a given location while circumventing obstacles.

    It works across different maps, but only if they are directly connected. Warps (doors, cave entrances, ...) will not
    be used automatically -- but a door can be used as a destination.

    It will also not attempt to start or stop surfing, i.e. transitions between land and water need to be handled
    separately.

    :param map: Destination map. This can either be a `MapFRLG`/`MapRSE` instance, or a map group/number tuple.
    :param coordinates: Local coordinates on the destination map that should be navigated to.
    :param run: Whether to sprint (hold B.) This is ignored when riding a bicycle.
    :param avoid_encounters: Prefer navigating via tiles that do not have encounters (i.e. try to avoid tall grass etc.)
                             This will still navigate via tiles with encounters if there is no other option.
                             It will also not avoid the activation range of unbattled trainers.
    :param avoid_scripted_events: Try to avoid tiles that would trigger a scripted event when moving onto them. It will
                                  still navigate via those tiles of there is no other option.
    """

    def waypoint_generator():
        destination_map = map
        destination_coordinates = coordinates

        while not player_is_at(destination_map, destination_coordinates):
            current_position = get_map_data_for_current_position()
            try:
                waypoints = calculate_path(
                    current_position,
                    get_map_data(map, coordinates),
                    avoid_encounters=avoid_encounters,
                    avoid_scripted_events=avoid_scripted_events,
                )
            except PathFindingError as e:
                raise BotModeError(str(e))

            # If the final destination turns out to be a warp, we are not going to end up in the place specified by
            # the `map` and `coordinates` parameters, but rather on another map. Because that would lead to this
            # function thinking we've missed the target, we will override the destination with the warp destination
            # in those cases.
            if waypoints[-1].is_warp:
                destination_map = waypoints[-1].map
                destination_coordinates = waypoints[-1].coordinates

            yield from waypoints

    while True:
        try:
            yield from follow_waypoints(waypoint_generator(), run)
            break
        except TimedOutTryingToReachWaypointError:
            # If we run into a timeout while trying to follow the waypoints, this is likely because of either of
            # these two reasons:
            #
            # (a) For some weird reason the player avatar moved to an unexpected location (for example due to forced
            #     movement, or due to overshooting on the Mach Bike.)
            # (b) Since the path is calculated in the beginning and then just followed, there's a chance that an NPC
            #     moves and gets in our way, in which case we would just keep running into them until they finally move
            #     out of the way again.
            #
            # In these cases, the `follow_waypoints()` function will trigger this timeout exception. We will just
            # calculate a new path (from the new location, or taking into account the new location of obstacles) and
            # try pathing again.
            pass


@debug.track
def walk_one_tile(direction: str, run: bool = True) -> Generator:
    """
    Moves the player one tile in a given direction, and then waiting for the movement
    to finish and any map transitions to complete before returning.

    Note that this will not check whether the destination tile is actually accessible
    so making sure of that is the responsibility of the calling code. It will create
    an endless loop if trying to run into a wall because the player's coordinates will
    never change.

    :param direction: One of "Up", "Down", "Left", "Right"
    :param run: Whether the player should run (hold down B)
    """
    if direction not in ("Up", "Down", "Left", "Right"):
        raise ValueError(f"'{direction}' is not a valid direction.")

    if run:
        context.emulator.hold_button("B")

    starting_position = get_player_avatar().local_coordinates
    context.emulator.hold_button(direction)
    while get_player_avatar().local_coordinates == starting_position:
        yield
    context.emulator.release_button(direction)
    context.emulator.release_button("B")

    # Wait for player to come to a full stop.
    while (
        not player_avatar_is_standing_still()
        or get_player_avatar().running_state != RunningState.NOT_MOVING
        or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
    ):
        yield


@debug.track
def ensure_facing_direction(facing_direction: str | tuple[int, int]) -> Generator:
    """
    If the player avatar is not already facing a certain direction this will make it turn
    around, so that afterwards it definitely faces the desired direction.
    :param facing_direction: One of "Up", "Down", "Left", or "Right"
    """
    if isinstance(facing_direction, tuple):
        x, y = get_player_avatar().local_coordinates
        if (x - 1, y) == facing_direction:
            facing_direction = "Left"
        elif (x + 1, y) == facing_direction:
            facing_direction = "Right"
        elif (x, y - 1) == facing_direction:
            facing_direction = "Up"
        elif (x, y + 1) == facing_direction:
            facing_direction = "Down"
        else:
            raise BotModeError(f"Tile ({x}, {y}) is not adjacent to the player.")

    while True:
        avatar = get_player_avatar()
        if avatar.facing_direction == facing_direction:
            return

        if (
            get_game_state() == GameState.OVERWORLD
            and avatar.tile_transition_state == TileTransitionState.NOT_MOVING
            and avatar.running_state == RunningState.NOT_MOVING
        ):
            context.emulator.press_button(facing_direction)

        yield


@debug.track
def wait_for_player_avatar_to_be_controllable(button_to_press: str | None = None) -> Generator:
    while not player_avatar_is_controllable():
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield


@debug.track
def wait_for_player_avatar_to_be_standing_still(button_to_press: str | None = None) -> Generator:
    while not player_avatar_is_standing_still():
        if button_to_press is not None:
            context.emulator.press_button(button_to_press)
        yield
