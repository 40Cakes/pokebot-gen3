from dataclasses import dataclass

from modules.context import context
from modules.items import ItemBag
from modules.memory import get_save_block, unpack_uint16, unpack_uint32
from modules.pokemon import Pokemon, parse_pokemon


@dataclass
class SaveData:
    save_index: int
    block_index: int
    sections: list[bytes]

    def get_map_group_and_number(self) -> tuple[int, int]:
        return self.sections[1][4], self.sections[1][5]

    def get_map_local_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self.sections[1][0:2]), unpack_uint16(self.sections[1][2:4])

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

    def get_last_heal_location(self) -> tuple[int, int]:
        return get_save_block(1, offset=0x1C, size=2)


_section_sizes = [3884, 3968, 3968, 3968, 3848, 3968, 3968, 3968, 3968, 3968, 3968, 3968, 3968, 2000]


def get_save_data() -> SaveData | None:
    """
    Extracts and normalises the save game data.
    :return: Save game data, or `None` if the game has not been saved yet.
    """
    save_data = context.emulator.read_save_data()

    def get_save_data_block(block_index: int) -> SaveData | None:
        if block_index == 1:
            block_offset = 0xE000
        else:
            block_offset = 0x0

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
