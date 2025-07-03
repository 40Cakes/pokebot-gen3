from enum import Enum, auto
from modules.context import context
from modules.items import Item, get_item_by_index
from modules.memory import unpack_uint16, get_save_block


class BerryTreeStage(Enum):
    Empty = 0
    Planted = 1
    Sprouted = 2
    Taller = 3
    Flowering = 4
    Berries = 5


class BerryTree:
    def __init__(self, data: bytes):
        self._data = data

    @property
    def berry(self) -> Item | None:
        if self._data[0] == 0 or self._data[0] > 43 or self.stage is BerryTreeStage.Empty:
            return None
        return get_item_by_index(132 + self._data[0])

    @property
    def stage(self) -> BerryTreeStage:
        return BerryTreeStage(self._data[1] & 0b0111_1111)

    @property
    def is_sparkling(self) -> bool:
        return bool(self._data[1] & 0b1000_0000)

    @property
    def stop_growth(self) -> bool:
        return bool(self._data[1] & 0b1000_0000)

    @property
    def minutes_until_next_stage(self) -> int:
        return unpack_uint16(self._data[2:4])

    @property
    def berry_yield(self) -> int:
        return self._data[4]

    @property
    def regrowth_count(self) -> int:
        return self._data[5] & 0b0000_1111

    @property
    def watered_stages(self) -> tuple[bool, bool, bool, bool]:
        return (
            bool(self._data[5] & (1 << 4)),
            bool(self._data[5] & (1 << 5)),
            bool(self._data[5] & (1 << 6)),
            bool(self._data[5] & (1 << 7)),
        )

    @property
    def current_stage_is_unwatered(self) -> bool:
        match self.stage:
            case BerryTreeStage.Planted:
                return not self.watered_stages[0]
            case BerryTreeStage.Sprouted:
                return not self.watered_stages[1]
            case BerryTreeStage.Taller:
                return not self.watered_stages[2]
            case BerryTreeStage.Flowering:
                return not self.watered_stages[3]
            case _:
                return False

    def to_dict(self) -> dict:
        return {
            "berry": self.berry.name if self.berry is not None else None,
            "stage": self.stage.name,
            "stage_id": self.stage.value,
            "is_sparkling": self.is_sparkling,
            "minutes_until_next_stage": self.minutes_until_next_stage,
            "berry_yield": self.berry_yield,
            "regrowth_count": self.regrowth_count,
            "watered_stages": self.watered_stages,
            "current_stage_is_unwatered": self.current_stage_is_unwatered,
            "stop_growth": self.stop_growth,
        }


def get_all_berry_trees() -> list[BerryTree]:
    if context.rom.is_frlg:
        return []
    offset = 0x169C if context.rom.is_emerald else 0x1608
    data = get_save_block(1, offset=offset, size=8 * 89)
    return [BerryTree(data[i * 8 : i * 8 + 6]) for i in range(89)]


def get_berry_tree_by_id(berry_tree_id) -> BerryTree | None:
    if context.rom.is_frlg or berry_tree_id < 0 or berry_tree_id >= 128:
        return None
    offset = 0x169C if context.rom.is_emerald else 0x1608
    return BerryTree(get_save_block(1, offset=offset + berry_tree_id * 8, size=6))
