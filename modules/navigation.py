from math import sqrt

from modules.context import context
from modules.encounter import encounter_pokemon
from modules.map import MapLocation
from modules.memory import get_game_state, GameState
from modules.pokemon import opponent_changed, get_opponent
from modules.tasks import task_is_active
from modules.temp import temp_run_from_battle
from modules.player import get_player, TileTransitionState

class Node():
    """A node class for A* Pathfinding"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position

        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position
    

def follow_path(coords: list, run: bool = True) -> bool:  # TODO needs a rework
    """
    Function to walk/run the trianer through a list of coords.
    TODO check if trainer gets stuck, re-attempt previous tuple of coords in the list

    :param coords: coords (tuple) (`posX`, `posY`)
    :param run: Trainer will hold B (run) if True, otherwise trainer will walk
    :return: True if trainer (`posX`, `posY`) = the final coord of the list, otherwise False (bool)
    """
    for x, y, *map_data in coords:
        while True and context.bot_mode != "Manual":
            if run:
                context.emulator.hold_button("B")

            if get_game_state() == GameState.BATTLE:
                if opponent_changed():
                    encounter_pokemon(get_opponent())
                context.emulator.release_button("B")
                temp_run_from_battle()

            # Check if PokeNav is active every n frames (get_task is expensive)
            if context.emulator.get_frame_count() % 60 == 0 and task_is_active("Task_SpinPokenavIcon"):
                context.emulator.release_button("B")

                while task_is_active("Task_SpinPokenavIcon"):
                    context.emulator.press_button("B")
                    context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)

            player = get_player()
            if player.tile_transition_state == TileTransitionState.NOT_MOVING:
                trainer_coords = player.local_coordinates
                # Check if map changed to desired map
                if map_data:
                    trainer_map = player.map_group_and_number
                    if trainer_map[0] == map_data[0][0] and trainer_map[1] == map_data[0][1]:
                        context.emulator.release_button("B")
                        break

                if trainer_coords[0] > x:
                    direction = "Left"
                elif trainer_coords[0] < x:
                    direction = "Right"
                elif trainer_coords[1] < y:
                    direction = "Down"
                elif trainer_coords[1] > y:
                    direction = "Up"
                else:
                    context.emulator.release_button("B")
                    break

                context.emulator.press_button(direction)
                context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
            context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)
        context.emulator.run_single_frame()  # TODO bad (needs to be refactored so main loop advances frame)

    return True

def get_adjacents_tiles(position: tuple[int, int], current_map: MapLocation) -> list[MapLocation]:
    """
        Get all adjacent tile from a position that can be walkable
        TODO Consider surf, bike, objects in the future
    """
    x, y = position
    map_width, map_height = current_map.map_size
    adjacent_tiles = []
    
    def valid_position(x1, y1) -> bool:
        return x1 >= 0 and y1 >= 0 and x1 < map_width and y1 < map_height
    
    tiles = current_map.all_tiles

    #North
    if valid_position(x, y-1) and not tiles[x][y-1].collision:
        adjacent_tiles.append(tiles[x][y-1])
    
    # South
    if valid_position(x, y+1) and not tiles[x][y+1].collision:
        adjacent_tiles.append(tiles[x][y+1])

    # West
    if valid_position(x-1, y) and not tiles[x-1][y].collision:
        adjacent_tiles.append(tiles[x-1][y])

    # East
    if valid_position(x+1, y) and not tiles[x+1][y].collision:
        adjacent_tiles.append(tiles[x+1][y])


    return adjacent_tiles

def calc_heuristic_cost(goal: tuple[int, int], tile: tuple[int, int]) -> float:
    """
        Heurist cost calculated with cartesian distance formula
    """
    xG, yG = goal
    xP, yP = tile
    return sqrt(((xG - xP)**2) + ((yG - yP)**2))

def calc_cost(tile: tuple[int, int], current_map: MapLocation) -> float:
    """
        Calculate cost by tile type
    """
    x, y = tile

    if current_map.all_tiles[x][y].is_running_possible:
        return 0.5
    if current_map.all_tiles[x][y].has_encounters:
        return 1.5
    if current_map.all_tiles[x][y].is_surfable:
        return 2
    
    return 1


def pathfinding(start: tuple[int, int], end: tuple[int, int], current_map: MapLocation) -> list[tuple[int, int]]:

    # Create start and end node
    start_node = Node(None, start)
    start_node.g = start_node.h = start_node.f = 0
    end_node = Node(None, end)
    end_node.g = end_node.h = end_node.f = 0

    # Initialize both open and closed list
    open_list = []
    closed_list = []

    # Add the start node
    open_list.append(start_node)

    # Loop until you find the end
    while len(open_list) > 0:

        # Get the current node
        current_node = open_list[0]
        current_index = 0
        for index, item in enumerate(open_list):
            if item.f < current_node.f:
                current_node = item
                current_index = index

        # Pop current off open list, add to closed list
        open_list.pop(current_index)
        closed_list.append(current_node)

        # Found the goal
        if current_node == end_node:
            path = []
            current = current_node
            while current is not None:
                path.append(current.position)
                current = current.parent
            return path[::-1] # Return reversed path

        # Generate children
        children = []
        for tile in get_adjacents_tiles(current_node.position, current_map): # Adjacent squares

            # Get node position
            node_position = tile.local_position

            # Create new node
            new_node = Node(current_node, node_position)

            # Append
            children.append(new_node)

        # Loop through children
        for child in children:

            # Child is on the closed list
            for closed_child in closed_list:
                if child == closed_child:
                    continue

            # Create the f, g, and h values
            child.g = current_node.g + calc_cost(child.position, current_map)
            child.h = calc_heuristic_cost(goal=end, tile=child.position)
            child.f = child.g + child.h

            # Child is already in the open list
            for open_node in open_list:
                if child == open_node and child.g > open_node.g:
                    continue

            # Add the child to the open list
            open_list.append(child)
