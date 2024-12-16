import time
from typing import Generator, Iterable, Callable

from modules.context import context
from modules.debug import debug
from modules.map import get_map_data_for_current_position, get_player_map_object
from modules.map_data import MapFRLG, MapRSE
from modules.map_path import calculate_path, Waypoint, PathFindingError, Direction, WaypointAction
from modules.memory import GameState, get_game_state
from modules.player import (
    RunningState,
    AcroBikeState,
    TileTransitionState,
    get_player_avatar,
    player_avatar_is_controllable,
    player_avatar_is_standing_still,
    player_is_at,
    get_player_location,
    AvatarFlags,
)
from modules.tasks import get_global_script_context, task_is_active
from .sleep import wait_for_n_frames
from .._interface import BotModeError
from ...items import get_item_bag, get_item_by_name


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
    last_waypoint = None
    for waypoint in path:
        # For the first waypoint it is possible that the player avatar is not facing the same way as it needs to
        # walk. This leads to the first navigation step to actually become two: Turning around, then doing the step.
        # When in tall grass, that could lead to an encounter starting mid-step which messes up the battle handling.
        # So for the first step, we will add an explicit additional turning step.
        if last_waypoint is None:
            current_facing_direction = Direction.from_string(get_player_avatar().facing_direction)
            if waypoint.direction != current_facing_direction:
                yield from ensure_facing_direction(waypoint.direction)

        last_waypoint = waypoint
        field_effect_is_active = False
        frames_remaining_until_timeout = timeout_in_frames
        if waypoint.is_warp:
            frames_remaining_until_timeout += extra_timeout_in_frames_for_warps
        if waypoint.action is WaypointAction.Surf:
            frames_remaining_until_timeout += 270
        elif waypoint.action is WaypointAction.Waterfall:
            frames_remaining_until_timeout += 195 + (get_player_location()[0][1] - waypoint.coordinates[1]) * 42

        while not player_is_at(waypoint.map, waypoint.coordinates) or field_effect_is_active:
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
                if waypoint.action is WaypointAction.Surf:
                    surf_task = "Task_SurfFieldEffect" if not context.rom.is_rs else "sub_8088954"
                    yield from ensure_facing_direction(waypoint.direction)
                    if not field_effect_is_active:
                        if task_is_active(surf_task):
                            field_effect_is_active = True
                        else:
                            context.emulator.press_button("A")
                    elif not task_is_active(surf_task):
                        field_effect_is_active = False
                elif waypoint.action is WaypointAction.Waterfall:
                    waterfall_task = "Task_UseWaterfall" if not context.rom.is_rs else "sub_8086F64"
                    yield from ensure_facing_direction(waypoint.direction)
                    if not field_effect_is_active:
                        if task_is_active(waterfall_task):
                            field_effect_is_active = True
                        else:
                            context.emulator.press_button("A")
                    elif not task_is_active(waterfall_task):
                        field_effect_is_active = False
                elif (
                    waypoint.action is WaypointAction.AcroBikeMount
                    and AvatarFlags.OnAcroBike not in get_player_avatar().flags
                ):
                    from .higher_level_actions import mount_bicycle

                    yield from mount_bicycle()
                elif waypoint.action is WaypointAction.AcroBikeSideJump:
                    context.emulator.press_button(waypoint.walking_direction)
                    context.emulator.press_button("B")
                elif waypoint.action is WaypointAction.AcroBikeBunnyHop:
                    from .higher_level_actions import mount_bicycle

                    yield from mount_bicycle()
                    if get_player_avatar().acro_bike_state is not AcroBikeState.HOPPING_WHEELIE:
                        context.emulator.release_button("B")
                        yield
                        context.emulator.hold_button("B")
                        while get_player_avatar().acro_bike_state is not AcroBikeState.HOPPING_WHEELIE:
                            yield
                    context.emulator.hold_button(waypoint.walking_direction)
                else:
                    context.emulator.hold_button(waypoint.walking_direction)
                    if run and not AvatarFlags.OnAcroBike in get_player_avatar().flags:
                        context.emulator.hold_button("B")
            else:
                context.emulator.reset_held_buttons()
                if waypoint.action is WaypointAction.AcroBikeBunnyHop:
                    context.emulator.hold_button("B")

            yield

    # Wait for player to come to a full stop.
    context.emulator.reset_held_buttons()
    while not player_avatar_is_standing_still() or get_player_avatar().running_state != RunningState.NOT_MOVING:
        # If we reached the destination tile and the script context is enabled, that probably means
        # that a script has triggered at our destination. In that case, we cease control back to the
        # bot mode immediately.
        if last_waypoint is None or player_is_at(last_waypoint.map, last_waypoint.coordinates):
            if get_global_script_context().is_active:
                break
        yield


@debug.track
def navigate_to(
    map: tuple[int, int] | MapFRLG | MapRSE,
    coordinates: tuple[int, int],
    run: bool = True,
    avoid_encounters: bool = True,
    avoid_scripted_events: bool = True,
    expecting_script: bool = False,
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
    :param expecting_script: This will accept if a script is triggered during navigation (presumably at the destination)
                             and will not show an error about that.
    """

    def waypoint_generator():
        destination_map = map
        destination_coordinates = coordinates

        while not player_is_at(destination_map, destination_coordinates):
            try:
                waypoints = calculate_path(
                    get_player_location(),
                    (map, coordinates),
                    avoid_encounters=avoid_encounters,
                    avoid_scripted_events=avoid_scripted_events,
                    has_acro_bike=get_item_bag().quantity_of(get_item_by_name("Acro Bike")) > 0,
                )
            except PathFindingError as e:
                raise BotModeError(str(e))

            if len(waypoints) == 0:
                return

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
            # these reasons:
            #
            # (a) For some weird reason the player avatar moved to an unexpected location (for example due to forced
            #     movement, or due to overshooting on the Mach Bike.)
            # (b) Since the path is calculated in the beginning and then just followed, there's a chance that an NPC
            #     moves and gets in our way, in which case we would just keep running into them until they finally move
            #     out of the way again.
            # (c) We have moved over a tile that triggered a script which froze the player avatar.
            #
            # In these cases, the `follow_waypoints()` function will trigger this timeout exception.
            #
            # In the first two  cases, We will just calculate a new path (from the new location, taking into account
            # the new location of obstacles) and try pathing again.
            #
            # In the third case, we consider that an unexpected event and will abort the navigation.
            if get_global_script_context().is_active:
                if expecting_script:
                    return
                else:
                    raise BotModeError(
                        f"We unexpectedly triggered a scripted event while trying to reach {coordinates} @ {map}.\nSwitching to manual mode."
                    )
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
def ensure_facing_direction(facing_direction: str | Direction | tuple[int, int]) -> Generator:
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

    if isinstance(facing_direction, Direction):
        facing_direction = facing_direction.button_name()

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
def run_in_circle(
    on_map: tuple[int, int] | MapRSE | MapFRLG,
    bottom_left: tuple[int, int],
    top_right: tuple[int, int],
    clockwise: bool = True,
    exit_condition: Callable[[], bool] | None = None,
):
    """
    Function name is lying: This actually makes the character run in a _square_

    The entirety of the circle (or, uh, square) needs to be within one map and must
    be free of obstructions.

    :param on_map: Map to run on
    :param bottom_left: Bottom-left (south-west) corner of the circle/square.
    :param top_right: Top-right (north-east) corner of the circle/square.
    :param clockwise: Which direction to run (True = clockwise, False = anti-clockwise)
    :param exit_condition: If set, the running will stop once this callback returns True.
                           Otherwise, it will never stop unless interrupted from the
                           outside.
    """

    if bottom_left[0] >= top_right[0]:
        raise RuntimeError(
            f"Bottom-left corner ({bottom_left}) must be to the west of the top-right corner ({top_right})"
        )

    if bottom_left[1] <= top_right[1]:
        raise RuntimeError(
            f"Bottom-left corner ({bottom_left}) must be to the south of the top-right corner ({top_right})"
        )

    def circle_waypoints_generator():
        if isinstance(on_map, MapRSE) or isinstance(on_map, MapFRLG):
            waypoint_map = on_map.value
        else:
            waypoint_map = on_map

        width = top_right[0] - bottom_left[0]
        height = bottom_left[1] - top_right[1]
        current_location = bottom_left[0], bottom_left[1]

        def north():
            nonlocal current_location
            for _ in range(height):
                current_location = (current_location[0], current_location[1] - 1)
                yield Waypoint(Direction.North, waypoint_map, current_location, False)

        def east():
            nonlocal current_location
            for _ in range(width):
                current_location = (current_location[0] + 1, current_location[1])
                yield Waypoint(Direction.East, waypoint_map, current_location, False)

        def south():
            nonlocal current_location
            for _ in range(height):
                current_location = (current_location[0], current_location[1] + 1)
                yield Waypoint(Direction.South, waypoint_map, current_location, False)

        def west():
            nonlocal current_location
            for _ in range(width):
                current_location = (current_location[0] - 1, current_location[1])
                yield Waypoint(Direction.West, waypoint_map, current_location, False)

        if clockwise:
            waypoint_list = [*north(), *east(), *south(), *west()]
        else:
            waypoint_list = [*east(), *north(), *west(), *south()]

        yield from calculate_path(get_map_data_for_current_position(), (on_map, bottom_left))
        while True:
            for waypoint in waypoint_list:
                if exit_condition is not None and exit_condition():
                    return
                yield waypoint

    yield from follow_waypoints(circle_waypoints_generator())


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
