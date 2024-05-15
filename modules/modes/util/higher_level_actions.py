from enum import Enum
from typing import Generator, Union

from modules.context import context
from modules.debug import debug
from modules.map_data import PokemonCenter
from modules.memory import get_event_flag, get_game_state_symbol
from modules.menu_parsers import CursorOptionEmerald, CursorOptionFRLG, CursorOptionRS
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon import get_party
from modules.region_map import FlyDestinationFRLG, FlyDestinationRSE, get_map_cursor, get_map_region
from modules.tasks import get_task
from ._util_helper import isolate_inputs
from .tasks_scripts import wait_for_task_to_start_and_finish, wait_for_yes_no_question, wait_for_no_script_to_run
from .walking import navigate_to, wait_for_player_avatar_to_be_standing_still
from .._interface import BotModeError


@isolate_inputs
@debug.track
def fly_to(destination: Union[FlyDestinationRSE, FlyDestinationFRLG]) -> Generator:
    if context.rom.is_frlg:
        has_necessary_badge = get_event_flag("BADGE03_GET")
        menu_index = CursorOptionFRLG.FLY
    else:
        has_necessary_badge = get_event_flag("BADGE03_GET")
        if context.rom.is_rs:
            menu_index = CursorOptionRS.FLY
        else:
            menu_index = CursorOptionEmerald.FLY

    if not has_necessary_badge:
        raise BotModeError("Player does not have the badge required for flying.")

    if not get_event_flag(destination.get_flag_name()):
        raise BotModeError(f"Player cannot fly to {destination.name} because that location is not yet available.")

    flying_pokemon_index = -1
    for index in range(len(get_party())):
        pokemon = get_party()[index]
        for learned_move in pokemon.moves:
            if learned_move is not None and learned_move.move.name == "Fly":
                flying_pokemon_index = index
                break
        if flying_pokemon_index > -1:
            break
    if flying_pokemon_index == -1:
        raise BotModeError("Player does not have any Pokémon that knows Fly in their party.")

    # Select field move FLY
    yield from StartMenuNavigator("POKEMON").step()
    yield from PokemonPartyMenuNavigator(flying_pokemon_index, "", menu_index).step()

    # Wait for region map to load.
    while (
        get_game_state_symbol() not in ("CB2_FLYMAP", "CB2_REGIONMAP", "CB2_FLYREGIONMAP") or get_map_cursor() is None
    ):
        yield

    destination_region = destination.get_map_region()
    if get_map_region() != destination_region:
        raise BotModeError(f"Player cannot fly to {destination.name} because they are in the wrong region.")

    # Select destination on the region map
    x, y = destination.value
    while get_map_cursor() != (x, y):
        context.emulator.reset_held_buttons()
        if get_map_cursor()[0] < x:
            context.emulator.hold_button("Right")
        elif get_map_cursor()[0] > x:
            context.emulator.hold_button("Left")
        elif get_map_cursor()[1] < y:
            context.emulator.hold_button("Down")
        elif get_map_cursor()[1] > y:
            context.emulator.hold_button("Up")
        yield
    context.emulator.reset_held_buttons()

    # Wait for journey to finish
    if context.rom.is_rs:
        yield from wait_for_task_to_start_and_finish("Task_MapNamePopup", "A")
    else:
        yield from wait_for_task_to_start_and_finish("Task_FlyIntoMap", "A")

    yield


class TaskFishing(Enum):
    INIT = 0
    GET_ROD_OUT = 1
    WAIT_BEFORE_DOTS = 2
    INIT_DOTS = 3
    SHOW_DOTS = 4
    CHECK_FOR_BITE = 5
    GOT_BITE = 6
    WAIT_FOR_A = 7
    CHECK_MORE_DOTS = 8
    MON_ON_HOOK = 9
    START_ENCOUNTER = 10
    NOT_EVEN_NIBBLE = 11
    GOT_AWAY = 12
    NO_MON = 13
    PUT_ROD_AWAY = 14
    END_NO_MON = 15


@debug.track
def fish() -> Generator:
    task_fishing = get_task("Task_Fishing")
    if task_fishing is not None:
        match task_fishing.data[0]:
            case TaskFishing.WAIT_FOR_A.value | TaskFishing.END_NO_MON.value:
                context.emulator.press_button("A")
            case TaskFishing.NOT_EVEN_NIBBLE.value:
                context.emulator.press_button("B")
            case TaskFishing.START_ENCOUNTER.value:
                context.emulator.press_button("A")
    else:
        context.emulator.press_button("Select")
    yield


@debug.track
def heal_in_pokemon_center(pokemon_center_door_location: PokemonCenter) -> Generator:
    # Walk to and enter the Pokémon centre
    yield from navigate_to(pokemon_center_door_location.value[0], pokemon_center_door_location.value[1])

    # Walk up to the nurse and talk to her
    yield from navigate_to(get_player_avatar().map_group_and_number, (7, 4))
    context.emulator.press_button("A")
    yield from wait_for_yes_no_question("Yes")
    yield from wait_for_no_script_to_run("B")
    yield from wait_for_player_avatar_to_be_standing_still("B")

    # Get out
    yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
