from dataclasses import dataclass
from functools import cached_property

from modules.context import context
from modules.game import get_event_flag_offset, get_event_var_offset
from modules.items import ItemBag
from modules.map import ObjectEvent
from modules.memory import get_save_block, unpack_uint16, unpack_uint32
from modules.player import Player
from modules.pokemon import Pokemon, parse_pokemon


def get_last_heal_location() -> tuple[int, int]:
    heal_location = get_save_block(1, offset=0x1C, size=2)
    return heal_location[0], heal_location[1]


@dataclass
class SaveData:
    save_index: int
    block_index: int
    sections: list[bytes]

    def get_player(self):
        if context.rom.is_rse:
            save_block_1_offset = 0x490
            encryption_key_offset = 0xAC
        else:
            save_block_1_offset = 0x290
            encryption_key_offset = 0xF20

        save_block_1 = self.get_save_block(1, offset=save_block_1_offset, size=0x08)
        save_block_2 = self.get_save_block(2, size=0x0E)
        encryption_key = self.get_save_block(2, encryption_key_offset, 4)

        return Player(save_block_1, save_block_2, encryption_key)

    def get_player_map_object(self) -> ObjectEvent | None:
        if context.rom.is_rs:
            object_events_offset = 0x9E0
        elif context.rom.is_emerald:
            object_events_offset = 0xA30
        else:
            object_events_offset = 0x6A0

        data = self.get_save_block(1, object_events_offset, size=0x24)
        if data[0] & 0x01:
            return ObjectEvent(data)
        else:
            return None

    def get_map_group_and_number(self) -> tuple[int, int]:
        return self.sections[1][4], self.sections[1][5]

    def get_map_local_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self.sections[1][:2]), unpack_uint16(self.sections[1][2:4])

    @cached_property
    def _save_block_1(self) -> bytes:
        return self.sections[1] + self.sections[2] + self.sections[3] + self.sections[4]

    def get_save_block(self, num: int = 1, offset: int = 0, size: int = 1) -> bytes:
        if num == 2:
            return self.sections[0][offset : offset + size]
        elif num == 1:
            return self._save_block_1[offset : offset + size]
        else:
            return b""

    def get_event_flag(self, flag_name: str) -> bool:
        try:
            flag_offset = get_event_flag_offset(flag_name)
        except KeyError:
            raise RuntimeError(f"Unknown event flag: '{flag_name}")
        flag_byte = self.get_save_block(1, offset=flag_offset[0], size=1)

        return bool((flag_byte[0] >> (flag_offset[1])) & 1)

    def get_event_var(self, var_name: str) -> int:
        try:
            var_offset = get_event_var_offset(var_name)
        except KeyError:
            raise RuntimeError(f"Unknown event flag: '{var_name}")

        return unpack_uint16(self.get_save_block(1, offset=var_offset, size=2))

    def get_party(self) -> list[Pokemon]:
        party = []
        if context.rom.is_frlg:
            party_count = self.sections[1][0x034]
            party_offset = 0x038
        else:
            party_count = self.sections[1][0x234]
            party_offset = 0x238
        for index in range(party_count):
            offset = party_offset + index * 100
            party.append(parse_pokemon(self.sections[1][offset : offset + 100]))
        return party

    def get_item_bag(self) -> ItemBag:
        if context.rom.is_frlg:
            items_count = 42
            key_items_count = 30
            poke_balls_count = 13
            tms_hms_count = 58
            berries_count = 43
            offset = 0x310
            encryption_key = self.sections[1][0xF20:0xF24]
        elif context.rom.is_emerald:
            items_count = 30
            key_items_count = 30
            poke_balls_count = 16
            tms_hms_count = 64
            berries_count = 46
            offset = 0x560
            encryption_key = self.sections[0][0xAC:0xB0]
        else:
            items_count = 20
            key_items_count = 20
            poke_balls_count = 16
            tms_hms_count = 64
            berries_count = 46
            offset = 0x560
            encryption_key = b"\x00\x00\x00\x00"

        data_size = 4 * (items_count + key_items_count + poke_balls_count + tms_hms_count + berries_count)
        data = self.sections[1][offset : offset + data_size]

        return ItemBag(
            data, items_count, key_items_count, poke_balls_count, tms_hms_count, berries_count, encryption_key
        )


_section_sizes = [3884, 3968, 3968, 3968, 3848, 3968, 3968, 3968, 3968, 3968, 3968, 3968, 3968, 2000]


def get_save_data() -> SaveData | None:
    """
    Extracts and normalises the save game data.
    :return: Save game data, or `None` if the game has not been saved yet.
    """
    save_data = context.emulator.read_save_data()

    def get_save_data_block(block_index: int) -> SaveData | None:
        block_offset = 0xE000 if block_index == 1 else 0x0
        sections = [b"", b"", b"", b"", b"", b"", b"", b"", b"", b"", b"", b"", b"", b""]
        save_index = -1
        for section_index in range(14):
            section_offset = block_offset + 0x1000 * section_index

            section_id = unpack_uint16(save_data[section_offset + 0x0FF4 : section_offset + 0x0FF6])
            if section_id < 0 or section_id >= 14 or sections[section_id] != b"":
                return None

            signature = save_data[section_offset + 0x0FF8 : section_offset + 0x0FFC]
            if signature != b"\x25\x20\x01\x08":
                return None

            checksum = unpack_uint16(save_data[section_offset + 0x0FF6 : section_offset + 0x0FF8])
            data = save_data[section_offset : section_offset + _section_sizes[section_id]]

            cursor = 0
            calculated_checksum = 0
            while cursor < len(data):
                calculated_checksum = (calculated_checksum + unpack_uint32(data[cursor : cursor + 4])) & 0xFFFF_FFFF
                cursor += 4
            calculated_checksum = ((calculated_checksum >> 16) + calculated_checksum) & 0xFFFF

            if calculated_checksum != checksum:
                return None

            sections[section_id] = data

            if section_index == 13:
                save_index = unpack_uint32(save_data[section_offset + 0x0FFC : section_offset + 0x1000])

        return SaveData(save_index, block_index, sections)

    save_block_0 = get_save_data_block(0)
    save_block_1 = get_save_data_block(1)

    if save_block_0 is not None and save_block_1 is None:
        return save_block_0
    elif save_block_1 is not None and save_block_0 is None:
        return save_block_1
    elif save_block_0 is not None and save_block_1 is not None:
        if save_block_0.save_index > save_block_1.save_index:
            return save_block_0
        else:
            return save_block_1
    else:
        return None
