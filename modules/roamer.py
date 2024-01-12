from typing import Literal

from modules.context import context
from modules.map import get_map_data
from modules.memory import unpack_uint16, unpack_uint32, get_save_block, read_symbol, write_symbol
from modules.pokemon import (
    StatsValues,
    ContestConditions,
    Nature,
    get_nature_by_index,
    Species,
    get_species_by_index,
    StatusCondition,
    get_type_by_name,
    Type,
    HIDDEN_POWER_MAP,
)


class Roamer:
    def __init__(self, data: bytes, location: bytes, trainer_id: int = 0, trainer_secret_id: int = 0):
        self._data = data
        self._location = location
        self._trainer_id = trainer_id
        self._trainer_secret_id = trainer_secret_id

    @property
    def map_group_and_number(self) -> tuple[int, int]:
        return self._location[0], self._location[1]

    @property
    def map_name(self):
        return get_map_data(self._location[0], self._location[1], (0, 0)).map_name

    @property
    def species(self) -> Species:
        return get_species_by_index(unpack_uint16(self._data[8:10]))

    @property
    def ivs(self) -> StatsValues:
        packed_data = unpack_uint32(self._data[0:4])
        return StatsValues(
            hp=(packed_data >> 0) & 0b11111,
            attack=(packed_data >> 5) & 0b11111,
            defence=(packed_data >> 10) & 0b11111,
            speed=(packed_data >> 15) & 0b11111,
            special_attack=(packed_data >> 20) & 0b11111,
            special_defence=(packed_data >> 25) & 0b11111,
        )

    @property
    def contest_conditions(self) -> ContestConditions:
        return ContestConditions(
            coolness=self._data[0x0E],
            beauty=self._data[0x0F],
            cuteness=self._data[0x10],
            smartness=self._data[0x11],
            toughness=self._data[0x12],
            feel=0,
        )

    @property
    def current_hp(self):
        return unpack_uint16(self._data[0x0A:0x0C])

    @property
    def level(self):
        return self._data[0x0C]

    @property
    def status_condition(self):
        return StatusCondition.from_bitfield(self._data[0x0D])

    @property
    def personality_value(self) -> int:
        return unpack_uint32(self._data[4:8])

    @property
    def nature(self) -> Nature:
        return get_nature_by_index(self.personality_value % 25)

    @property
    def gender(self) -> Literal["male", "female", None]:
        ratio = self.species.gender_ratio
        if ratio == 255:
            return None
        elif ratio == 254:
            return "female"
        elif ratio == 0:
            return "male"

        value = self.personality_value & 0xFF
        if value >= ratio:
            return "male"
        else:
            return "female"

    @property
    def shiny_value(self) -> int:
        return (
            self._trainer_id ^ self._trainer_secret_id ^ unpack_uint16(self._data[4:6]) ^ unpack_uint16(self._data[6:8])
        )

    @property
    def is_shiny(self) -> bool:
        return self.shiny_value < 8

    @property
    def is_anti_shiny(self) -> bool:
        return 65528 <= self.shiny_value <= 65535

    @property
    def hidden_power_type(self) -> Type:
        ivs = self.ivs
        value = (
            ((ivs.hp & 1) << 0)
            + ((ivs.attack & 1) << 1)
            + ((ivs.defence & 1) << 2)
            + ((ivs.speed & 1) << 3)
            + ((ivs.special_attack & 1) << 4)
            + ((ivs.special_defence & 1) << 5)
        )
        value = (value * 15) // 63
        return get_type_by_name(HIDDEN_POWER_MAP[value])

    @property
    def hidden_power_damage(self) -> int:
        ivs = self.ivs
        value = (
            ((ivs.hp & 2) >> 1)
            + ((ivs.attack & 2) << 0)
            + ((ivs.defence & 2) << 1)
            + ((ivs.speed & 2) << 2)
            + ((ivs.special_attack & 2) << 3)
            + ((ivs.special_defence & 2) << 4)
        )
        value = (value * 40) // 63 + 30
        return value

    def __str__(self):
        output = f"{self.species.name}, lvl. {self.level}, {self.current_hp} HP"
        if self.status_condition != StatusCondition.Healthy:
            output += ", " + str(self.status_condition)
        return output + " @ " + self.map_name


def get_roamer() -> Roamer | None:
    if context.rom.is_frlg:
        offset = 0x30D0
    elif context.rom.is_emerald:
        offset = 0x31DC
    else:
        offset = 0x3144

    data = get_save_block(1, offset, size=0x14)
    location = read_symbol("sRoamerLocation")
    if data[0x13] and (data[0x08] or data[0x09]):
        trainer_id = get_save_block(2, offset=0xA, size=4)
        return Roamer(data, location, unpack_uint16(trainer_id[0:2]), unpack_uint16(trainer_id[2:4]))
    else:
        return None


def dangerous_set_roamer_location(location: tuple[int, int]) -> None:
    write_symbol("sRoamerLocation", bytes([location[0], location[1]]))


def dangerous_make_roamer_shiny() -> None:
    import random
    from modules.memory import write_to_save_block, pack_uint32

    data = get_save_block(2, offset=0xA, size=4)
    trainer_id, secret_trainer_id = unpack_uint16(data[0:2]), unpack_uint16(data[2:4])

    while True:
        pv = random.randint(0, 0xFFFF_FFFF)
        upper = pv >> 16
        lower = pv & 0xFFFF
        if upper ^ lower ^ trainer_id ^ secret_trainer_id < 8:
            if context.rom.is_frlg:
                offset = 0x30D0
            elif context.rom.is_emerald:
                offset = 0x31DC
            else:
                offset = 0x3144
            write_to_save_block(pack_uint32(pv), 1, offset + 4)
            break
