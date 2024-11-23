from modules.memory import unpack_uint16, unpack_sint8, read_symbol


class GameSprite:
    """
    This represents in _in-game_ Sprite object, as opposed to a
    Sprite image file in this repository.
    """

    def __init__(self, data: bytes):
        self._data = data

    @property
    def coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self._data[0x20:0x22]), unpack_uint16(self._data[0x22:0x24])

    @property
    def secondary_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self._data[0x24:0x26]), unpack_uint16(self._data[0x26:0x28])

    @property
    def center_to_corner_vector(self) -> tuple[int, int]:
        return unpack_sint8(self._data[0x28]), unpack_sint8(self._data[0x29])

    @property
    def flags(self) -> list[str]:
        flags = []

        if self._data[0x3E] & 0b001:
            flags.append("in_use")
        if self._data[0x3E] & 0b010:
            flags.append("coordinate_offset_enabled")
        if self._data[0x3E] & 0b100:
            flags.append("invisible")

        if self._data[0x3F] & 0b0000_0001:
            flags.append("flip_horizontally")
        if self._data[0x3F] & 0b0000_0010:
            flags.append("flip_vertically")
        if self._data[0x3F] & 0b0000_0100:
            flags.append("animation_beginning")
        if self._data[0x3F] & 0b0000_1000:
            flags.append("affine_animation_beginning")
        if self._data[0x3F] & 0b0001_0000:
            flags.append("animation_ended")
        if self._data[0x3F] & 0b0010_0000:
            flags.append("affine_animation_ended")
        if self._data[0x3F] & 0b0100_0000:
            flags.append("using_sheet")
        if self._data[0x3F] & 0b1000_0000:
            flags.append("anchored")

        return flags

    def data_value(self, index: int) -> int:
        if index < 0 or index >= 8:
            raise IndexError(f"Invalid data index '{index}', must be between 0 and 7.")

        offset = 0x2E + index * 2
        return unpack_uint16(self._data[offset : offset + 2])


def get_game_sprite_by_id(id: int) -> GameSprite:
    if id < 0 or id >= 64:
        raise IndexError(f"Invalid sprite ID '{id}', must be between 0 and 64.")

    return GameSprite(read_symbol("gSprites", offset=0x44 * id, size=0x44))
