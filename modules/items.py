import json
from dataclasses import dataclass
from enum import Enum
from functools import cached_property

from modules.context import context
from modules.memory import get_save_block, unpack_uint16, write_to_save_block, pack_uint16
from modules.runtime import get_data_path
from modules.state_cache import state_cache


class ItemType(Enum):
    Mail = ("mail",)
    UsableOutsideBattle = "usable_outside_battle"
    UsableInCertainLocations = "usable_in_certain_locations"
    PokeblockCase = "pokeblock_case"
    NotUsableOutsideBattle = "not_usable_outside_battle"

    def __str__(self):
        return self.value

    @classmethod
    def from_value(cls, value: str) -> "ItemType":
        for name, member in ItemType.__members__.items():
            if member.value == value:
                return member


class ItemPocket(Enum):
    Items = "items"
    PokeBalls = "poke_balls"
    TmsAndHms = "tms_and_hms"
    Berries = "berries"
    KeyItems = "key_items"

    def __str__(self):
        return self.value


@dataclass
class Item:
    """
    This represents an item type in the game.
    """

    index: int
    name: str
    sprite_name: str
    price: int
    type: ItemType
    pocket: ItemPocket
    parameter: int
    extra_parameter: int

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Item":
        if data["pocket"] == "poke_balls":
            item_type = data["type"]
        else:
            item_type = ItemType.from_value(data["type"])

        return Item(
            index=index,
            name=data["name"],
            sprite_name=data["name"].replace("'", "-").replace(".", "-"),
            price=data["price"],
            type=item_type,
            pocket=ItemPocket(data["pocket"]),
            parameter=data["parameter"],
            extra_parameter=data["extra_parameter"],
        )


@dataclass
class ItemSlot:
    item: Item
    quantity: int

    def to_dict(self) -> dict:
        return {
            "item": self.item.name,
            "quantity": self.quantity,
        }


class ItemBag:
    def __init__(
        self,
        data: bytes,
        items_count: int,
        key_items_count: int,
        poke_balls_count: int,
        tms_hms_count: int,
        berries_count: int,
        encryption_key: bytes,
    ):
        self._data = data
        self._encryption_key = encryption_key
        self.items_size = items_count
        self.key_items_size = key_items_count
        self.poke_balls_size = poke_balls_count
        self.tms_hms_size = tms_hms_count
        self.berries_size = berries_count

    def __eq__(self, other):
        if isinstance(other, ItemBag):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ItemBag):
            return other._data != self._data
        else:
            return NotImplemented

    def _get_pocket(self, slot_offset: int, number_of_slots: int) -> list[ItemSlot]:
        result = []
        for index in range(number_of_slots):
            offset = (slot_offset + index) * 4
            item_index = unpack_uint16(self._data[offset : offset + 2])
            quantity = unpack_uint16(self._data[offset + 2 : offset + 4]) ^ unpack_uint16(self._encryption_key[0:2])
            if item_index != 0 and quantity > 0:
                item = get_item_by_index(item_index)
                result.append(ItemSlot(item, quantity))
        return result

    @cached_property
    def items(self) -> list[ItemSlot]:
        return self._get_pocket(slot_offset=0, number_of_slots=self.items_size)

    @cached_property
    def key_items(self) -> list[ItemSlot]:
        offset = self.items_size
        return self._get_pocket(slot_offset=offset, number_of_slots=self.key_items_size)

    @cached_property
    def poke_balls(self) -> list[ItemSlot]:
        offset = self.items_size + self.key_items_size
        return self._get_pocket(slot_offset=offset, number_of_slots=self.poke_balls_size)

    @cached_property
    def tms_hms(self) -> list[ItemSlot]:
        offset = self.items_size + self.key_items_size + self.poke_balls_size
        return self._get_pocket(slot_offset=offset, number_of_slots=self.tms_hms_size)

    @cached_property
    def berries(self) -> list[ItemSlot]:
        offset = self.items_size + self.key_items_size + self.poke_balls_size + self.tms_hms_size
        return self._get_pocket(slot_offset=offset, number_of_slots=self.berries_size)

    def has_space_for(self, item: Item) -> bool:
        match item.pocket:
            case ItemPocket.Items:
                pocket = self.items
                pocket_size = self.items_size
            case ItemPocket.KeyItems:
                pocket = self.key_items
                pocket_size = self.key_items_size
            case ItemPocket.PokeBalls:
                pocket = self.poke_balls
                pocket_size = self.poke_balls_size
            case ItemPocket.TmsAndHms:
                pocket = self.tms_hms
                pocket_size = self.tms_hms_size
            case ItemPocket.Berries:
                pocket = self.berries
                pocket_size = self.berries_size
            case _:
                pocket = []
                pocket_size = 0

        if len(pocket) < pocket_size:
            return True

        # In FireRed/LeafGreen, you can always put 999 items in a stack. In RSE, this only works for berries.
        if context.rom.is_frlg or item.pocket == ItemPocket.Berries:
            stack_size = 999
        else:
            stack_size = 99

        for slot in pocket:
            if slot.item == item and slot.quantity < stack_size:
                return True

        return False

    def quantity_of(self, item: Item) -> int:
        match item.pocket:
            case ItemPocket.Items:
                pocket = self.items
            case ItemPocket.KeyItems:
                pocket = self.key_items
            case ItemPocket.PokeBalls:
                pocket = self.poke_balls
            case ItemPocket.TmsAndHms:
                pocket = self.tms_hms
            case ItemPocket.Berries:
                pocket = self.berries
            case _:
                pocket = []

        quantity = 0
        for slot in pocket:
            if slot.item == item:
                quantity += slot.quantity

        return quantity

    def to_dict(self) -> dict:
        return {
            "items": [s.to_dict() for s in self.items],
            "key_items": [s.to_dict() for s in self.key_items],
            "poke_balls": [s.to_dict() for s in self.poke_balls],
            "tms_hms": [s.to_dict() for s in self.tms_hms],
            "berries": [s.to_dict() for s in self.berries],
        }


class ItemStorage:
    def __init__(self, data: bytes, number_of_slots: int):
        self._data = data
        self.number_of_slots = number_of_slots

    def __eq__(self, other):
        if isinstance(other, ItemStorage):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ItemStorage):
            return other._data != self._data
        else:
            return NotImplemented

    @cached_property
    def items(self) -> list[ItemSlot]:
        result = []
        for index in range(self.number_of_slots):
            offset = index * 4
            item_index = unpack_uint16(self._data[offset : offset + 2])
            quantity = unpack_uint16(self._data[offset + 2 : offset + 4])
            if item_index != 0 and quantity > 0:
                item = get_item_by_index(item_index)
                result.append(ItemSlot(item, quantity))
        return result

    def has_space_for(self, item: Item) -> bool:
        if len(self.items) < self.number_of_slots:
            return True

        for slot in self.items:
            if slot.item == item and slot.quantity < 999:
                return True

        return False

    def quantity_of(self, item: Item) -> int:
        quantity = 0
        for slot in self.items:
            if slot.item == item:
                quantity += slot.quantity

        return quantity

    def to_list(self) -> list[dict]:
        return list([s.to_dict() for s in self.items])


def _load_items() -> tuple[dict[str, Item], list[Item]]:
    by_name: dict[str, Item] = {}
    by_index: list[Item] = []
    with open(get_data_path() / "items.json", "r") as file:
        items_data = json.load(file)
        for index in range(len(items_data)):
            item = Item.from_dict(index, items_data[index])
            by_name[item.name] = item
            by_index.append(item)
    return by_name, by_index


_items_by_name, _items_by_index = _load_items()


def get_item_by_name(name: str) -> Item:
    return _items_by_name[name]


def get_item_by_index(index: int) -> Item:
    return _items_by_index[index]


def get_item_bag() -> ItemBag:
    if state_cache.item_bag.age_in_frames == 0:
        return state_cache.item_bag.value

    if context.rom.is_frlg:
        items_count = 42
        key_items_count = 30
        poke_balls_count = 13
        tms_hms_count = 58
        berries_count = 43
        offset = 0x310
        encryption_key = get_save_block(2, offset=0xF20, size=4)
    elif context.rom.is_emerald:
        items_count = 30
        key_items_count = 30
        poke_balls_count = 16
        tms_hms_count = 64
        berries_count = 46
        offset = 0x560
        encryption_key = get_save_block(2, offset=0xAC, size=4)
    else:
        items_count = 20
        key_items_count = 20
        poke_balls_count = 16
        tms_hms_count = 64
        berries_count = 46
        offset = 0x560
        encryption_key = b"\x00\x00\x00\x00"

    data_size = 4 * (items_count + key_items_count + poke_balls_count + tms_hms_count + berries_count)
    data = get_save_block(1, offset=offset, size=data_size)

    item_bag = ItemBag(
        data, items_count, key_items_count, poke_balls_count, tms_hms_count, berries_count, encryption_key
    )
    state_cache.item_bag = item_bag
    return item_bag


def get_item_storage() -> ItemStorage:
    if state_cache.item_storage.age_in_frames == 0:
        return state_cache.item_storage.value

    if context.rom.is_frlg:
        items_count = 30
        offset = 0x298
    else:
        items_count = 50
        offset = 0x498

    data = get_save_block(1, offset=offset, size=items_count * 4)
    item_storage = ItemStorage(data, items_count)
    state_cache.item_storage = item_storage
    return item_storage
