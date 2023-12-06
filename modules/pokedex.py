from functools import cached_property

from modules.context import context
from modules.memory import get_save_block
from modules.pokemon import Species, get_species_by_national_dex
from modules.state_cache import state_cache


class Pokedex:
    def __init__(self, data, seen1, seen2):
        self._data = data
        self._seen1 = seen1
        self._seen2 = seen2

    def __eq__(self, other):
        if isinstance(other, Pokedex):
            return other._data == self._data and \
                other._seen1 == self._seen1 and \
                other._seen2 == self._seen2
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Pokedex):
            return other._data != self._data or \
                other._seen1 != self._seen1 or \
                other._seen2 != self._seen2
        else:
            return NotImplemented

    @property
    def is_national_dex_enabled(self) -> bool:
        return self._data[2] == 0xDA

    @cached_property
    def seen_species(self) -> list[Species]:
        result = []
        for index in range(412):
            offset = index // 8
            mask = 1 << (index % 8)

            is_seen = self._data[0x44 + offset] & mask
            if is_seen and \
                    (self._seen1[offset] & mask) == is_seen and \
                    (self._seen2[offset] & mask) == is_seen:
                result.append(get_species_by_national_dex(index + 1))
        return result

    @cached_property
    def owned_species(self) -> list[Species]:
        result = []
        for index in range(412):
            offset = index // 8
            mask = 1 << (index % 8)

            is_seen = self._data[0x10 + offset] & mask
            if is_seen and \
                    (self._seen1[offset] & mask) == is_seen and \
                    (self._seen2[offset] & mask) == is_seen:
                result.append(get_species_by_national_dex(index + 1))
        return result

    def to_dict(self) -> dict[str, list[dict]]:
        seen = []
        for species in self.seen_species:
            seen.append({"national_dex_number": species.national_dex_number, "name": species.name})

        owned = []
        for species in self.owned_species:
            owned.append({"national_dex_number": species.national_dex_number, "name": species.name})

        return {"seen": seen, "owned": owned}


def get_pokedex() -> Pokedex:
    if state_cache.pokedex.age_in_frames == 0:
        return state_cache.pokedex.value

    if context.rom.game_title == "POKEMON EMER":
        seen1_offset = 0x988
        seen2_offset = 0x3B24
    elif context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP"]:
        seen1_offset = 0x938
        seen2_offset = 0x3A8C
    else:
        seen1_offset = 0x5F8
        seen2_offset = 0x3A18

    pokedex = Pokedex(
        get_save_block(2, offset=0x18, size=0x78),
        get_save_block(1, offset=seen1_offset, size=0x34),
        get_save_block(1, offset=seen2_offset, size=0x34),
    )

    state_cache.pokedex = pokedex
    return pokedex
