import struct
from typing import Generator

from modules.items import get_item_by_name, get_item_bag, get_pokeblocks
from modules.player import get_player_avatar
from modules.roms import ROMLanguage
from modules.context import context
from . import BotModeError
from ._interface import BotMode
from .util import scroll_to_item_in_bag
from ..gui.multi_select_window import Selection, ask_for_choice_scroll
from ..map_data import MapRSE
from ..memory import get_game_state, GameState, get_game_state_symbol, read_symbol, unpack_uint32, unpack_uint16
from ..runtime import get_sprites_path


class BerryBlendMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Berry Blend"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_frlg:
            return False

        targeted_tile = get_player_avatar().map_location_in_front
        if targeted_tile is None:
            return False

        for map_name, coordinates in _get_berry_blender_locations():
            if targeted_tile.map_group_and_number == map_name and targeted_tile.local_position == coordinates:
                return True

        return False

    def run(self) -> Generator:
        if context.rom.is_frlg:
            raise BotModeError("Pokéblocks do not exist in FR/LG.")

        if get_item_bag().quantity_of(get_item_by_name("Pokéblock Case")) == 0:
            raise BotModeError("Player does not own the Pokéblock Case yet.")

        if len(get_pokeblocks()) >= 40:
            raise BotModeError("The player's Pokéblock case is full.")

        if context.rom.is_rs:
            play_callback_name = "SUB_80501FC"
            data_symbol = "gBerryBlenderData"
            hit_range_symbol = "gUnknown_08216303"

            if context.rom.language == ROMLanguage.Japanese:
                arrow_position_offset = 74
                speed_offset = 76
                number_of_players_offset = 126
                progress_offset = 280
            else:
                arrow_position_offset = 84
                speed_offset = 86
                number_of_players_offset = 136
                progress_offset = 290

        else:
            play_callback_name = "CB2_PLAYBLENDER"
            data_symbol = "sBerryBlender"
            hit_range_symbol = "sArrowHitRangeStart"
            arrow_position_offset = 74
            speed_offset = 76
            number_of_players_offset = 124
            progress_offset = 280

        if get_game_state_symbol() != play_callback_name:
            berry_choices = []
            for berry in get_item_bag().berries:
                sprite_path = get_sprites_path() / "items" / f"{berry.item.name}.png"
                berry_choices.append(Selection(f"{berry.item.name}", sprite_path))

            if len(berry_choices) == 0:
                raise BotModeError("Player does not have any berries.")

            berry_choice = ask_for_choice_scroll(
                berry_choices, window_title="Select a berry to blender...", options_per_row=3
            )

            if berry_choice is None:
                context.set_manual_mode()
                yield
                return

            berry_to_use = get_item_by_name(berry_choice)

            while get_game_state() != GameState.BAG_MENU:
                context.emulator.press_button("A")
                yield

            yield from scroll_to_item_in_bag(berry_to_use)

            while get_game_state_symbol() != play_callback_name:
                context.emulator.press_button("A")
                yield

        self._last_was_a = False
        pointer = unpack_uint32(read_symbol(data_symbol))
        number_of_players = context.emulator.read_bytes(pointer + number_of_players_offset, 1)[0]
        while get_game_state_symbol() == play_callback_name:
            raw_arrow_position = unpack_uint16(context.emulator.read_bytes(pointer + arrow_position_offset, 2))
            speed = struct.unpack("<H", context.emulator.read_bytes(pointer + speed_offset, 2))[0]

            arrow_hit_ranges = read_symbol(hit_range_symbol)

            player_offset = _get_player_offset(number_of_players, context)

            hit_range_start = arrow_hit_ranges[player_offset]
            hit_range_end = arrow_hit_ranges[player_offset] + 48

            position_next_frame = (raw_arrow_position + speed) // 256 + 24
            progress = unpack_uint16(context.emulator.read_bytes(pointer + progress_offset, 2))
            if (progress > 950) ^ (hit_range_start <= position_next_frame < hit_range_end):
                self.press_a()

            yield

        context.set_manual_mode()

    def press_a(self):
        """Alternates between L and A presses to allow for more hits when the L=A setting is on."""
        if self._last_was_a:
            self._last_was_a = False
            context.emulator.press_button("L")
            return
        self._last_was_a = True
        context.emulator.press_button("A")


def _get_berry_blender_locations() -> list[tuple[MapRSE, tuple[int, int]]]:
    if context.rom.is_emerald:
        return [
            (MapRSE.LILYCOVE_CITY_CONTEST_LOBBY, (27, 5)),
            (MapRSE.LILYCOVE_CITY_CONTEST_LOBBY, (23, 9)),
            (MapRSE.LILYCOVE_CITY_CONTEST_LOBBY, (27, 9)),
        ]
    elif context.rom.is_rs:
        return [
            (MapRSE.FALLARBOR_TOWN_BATTLE_TENT_LOBBY, (12, 5)),
            (MapRSE.LILYCOVE_CITY_CONTEST_LOBBY, (18, 9)),
            (MapRSE.SLATEPORT_CITY_BATTLE_TENT_LOBBY, (12, 5)),
            (MapRSE.VERDANTURF_TOWN_BATTLE_TENT_LOBBY, (12, 5)),
        ]
    else:
        return []


def _get_player_offset(number_of_players, context):
    if number_of_players not in [2, 3, 4]:
        raise ValueError("Invalid number of players. Supported values are 2, 3, or 4.")

    offsets = {2: 1, 3: 1, 4: 0}

    return offsets[number_of_players]
