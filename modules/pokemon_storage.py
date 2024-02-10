from dataclasses import dataclass
from functools import cached_property

from modules.context import context
from modules.game import get_symbol, decode_string
from modules.memory import read_symbol, unpack_uint32
from modules.pokemon import Pokemon, Species
from modules.state_cache import state_cache


@dataclass
class PokemonStorageSlot:
    slot_index: int
    pokemon: Pokemon

    @property
    def row(self) -> int:
        return self.slot_index // 6

    @property
    def column(self) -> int:
        return self.slot_index % 6

    def to_dict(self) -> dict:
        return {
            "slot_index": self.slot_index,
            "row": self.row,
            "column": self.column,
            "pokemon": self.pokemon.to_dict(),
        }


@dataclass
class PokemonStorageBox:
    number: int
    name: str
    wallpaper_id: int
    slots: list[PokemonStorageSlot]

    def __len__(self):
        return len(self.slots)

    @property
    def first_empty_slot_index(self) -> int | None:
        potential_empty_slot_index = 0
        for slot in self.slots:
            if potential_empty_slot_index != slot.slot_index:
                return potential_empty_slot_index
            else:
                potential_empty_slot_index += 1
        if potential_empty_slot_index >= 30:
            return None
        else:
            return potential_empty_slot_index

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "wallpaper_id": self.wallpaper_id,
            "slots": [s.to_dict() for s in self.slots],
        }


class PokemonStorage:
    def __init__(self, offset: int, data: bytes):
        self._offset = offset
        self._data = data

    def __eq__(self, other):
        if isinstance(other, PokemonStorage):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, PokemonStorage):
            return other._data != self._data
        else:
            return NotImplemented

    @property
    def active_box_index(self) -> int:
        return self._data[0]

    @property
    def active_box(self) -> PokemonStorageBox:
        return self.boxes[self.active_box_index]

    @cached_property
    def boxes(self) -> list[PokemonStorageBox]:
        boxes = []
        for box_index in range(14):
            name_offset = 0x8344 + (box_index * 9)
            name = decode_string(self._data[name_offset : name_offset + 9])

            wallpaper_id_index = 0x83C2 + box_index
            wallpaper_id = self._data[wallpaper_id_index]

            pokemon_offset = 0x4 + (box_index * 30 * 80)
            slots = []
            for slot_index in range(30):
                offset = pokemon_offset + (slot_index * 80)
                pokemon = Pokemon(self._data[offset : offset + 80])
                if not pokemon.is_empty:
                    slots.append(PokemonStorageSlot(slot_index, pokemon))

            boxes.append(PokemonStorageBox(box_index, name, wallpaper_id, slots))
        return boxes

    @property
    def pokemon_count(self) -> int:
        count = 0
        for box in self.boxes:
            count += len(box.slots)
        return count

    def contains_species(self, species: Species) -> bool:
        for box in self.boxes:
            for slot in box.slots:
                if slot.pokemon.species == species:
                    return True
        return False

    def contains_pokemon(self, pokemon: Pokemon) -> bool:
        for box in self.boxes:
            for slot in box.slots:
                if slot.pokemon.data[0:4] == pokemon.data[0:4]:
                    return True
        return False

    def to_dict(self) -> dict:
        return {
            "active_box_index": self.active_box_index,
            "pokemon_count": self.pokemon_count,
            "boxes": [b.to_dict() for b in self.boxes],
        }


def get_pokemon_storage() -> PokemonStorage:
    if state_cache.pokemon_storage.age_in_frames == 0:
        return state_cache.pokemon_storage.value

    if not context.rom.is_rs:
        offset = unpack_uint32(read_symbol("gPokemonStoragePtr"))
        length = get_symbol("gPokemonStorage")[1]
    else:
        offset, length = get_symbol("gPokemonStorage")

    pokemon_storage = PokemonStorage(offset, context.emulator.read_bytes(offset, length))
    state_cache.pokemon_storage = pokemon_storage
    return pokemon_storage
