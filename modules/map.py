import string
from functools import cached_property

from modules.context import context
from modules.game import decode_string
from modules.memory import unpack_uint16, unpack_uint32, read_symbol


def _get_tile_type_name(tile_type: int):
    if context.rom.game_title in ["POKEMON RUBY", "POKEMON SAPP"]:
        rse = True
        frlg = False
        emerald = False
    elif context.rom.game_title == "POKEMON EMER":
        rse = True
        frlg = False
        emerald = True
    else:
        rse = False
        frlg = True
        emerald = False

    match tile_type:
        case 0x00:
            return "Normal"
        case 0x01:
            return "Secret Base Wall"
        case 0x02:
            return "Tall Grass"
        case 0x03:
            return "Long Grass"
        case 0x06:
            return "Deep Sand"
        case 0x07:
            return "Short Grass"
        case 0x08:
            return "Cave"
        case 0x09:
            return "Long Grass South Edge"
        case 0x0A:
            return "No Running"
        case 0x0B:
            return "Indoor Encounter"
        case 0x0C:
            return "Mountain Top"
        case 0x0D:
            return "Battle Pyramid Warp" if emerald else "Secret Base Glitter Map"
        case 0x0E:
            return "Mossdeep Gym Warp"
        case 0x0F:
            return "Mount Pyre Hole"
        case 0x10:
            return "Pond Water"
        case 0x11:
            if emerald:
                return "Interior Deep Water"  # Used by interior maps; functionally the same as MB_DEEP_WATER
            elif frlg:
                return "Fast Water"
            else:
                return "Semi-Deep Water"
        case 0x12:
            return "Deep Water"
        case 0x13:
            return "Waterfall"
        case 0x14:
            return "Sootopolis Deep Water"
        case 0x15:
            return "Ocean Water"
        case 0x16:
            return "Puddle"
        case 0x17:
            return "Shallow Water"
        case 0x18:
            return "Sootopolis Deep Water (2)"
        case 0x19:
            return "Underwater Blocked Above"
        case 0x1A:
            return "Sootopolis Deep Water (3)"
        case 0x1B:
            return "Stairs Outside Abandoned Ship" if rse else "Cycling Road Water"
        case 0x1C:
            return "Shoal Cave Entrance"
        case 0x20:
            return "Ice" if rse else "Strength Button"
        case 0x21:
            return "Sand"
        case 0x22:
            return "Seaweed"
        case 0x23:
            return "Ice"
        case 0x24:
            return "Ash Grass"
        case 0x25:
            return "Footprints"
        case 0x26:
            return "Thin Ice"
        case 0x27:
            return "Cracked Ice"
        case 0x28:
            return "Hot Springs"
        case 0x29:
            return "Lavaridge Gym B1F Warp"
        case 0x2A:
            return "Seaweed No Surfacing" if rse else "Rock Stairs"
        case 0x2B:
            return "Reflection Under Bridge" if rse else "Sand Cave"
        case 0x30:
            return "Impassable East"
        case 0x31:
            return "Impassable West"
        case 0x32:
            return "Impassable North"
        case 0x33:
            return "Impassable South"
        case 0x34:
            return "Impassable North/East"
        case 0x35:
            return "Impassable North/West"
        case 0x36:
            return "Impassable South/East"
        case 0x37:
            return "Impassable South/West"
        case 0x38:
            return "Jump East"
        case 0x39:
            return "Jump West"
        case 0x3A:
            return "Jump North"
        case 0x3B:
            return "Jump South"
        case 0x3C:
            return "Jump North/East"
        case 0x3D:
            return "Jump North/West"
        case 0x3E:
            return "Jump South/East"
        case 0x3F:
            return "Jump South/West"
        case 0x40:
            return "Walk East"
        case 0x41:
            return "Walk West"
        case 0x42:
            return "Walk North"
        case 0x43:
            return "Walk South"
        case 0x44:
            return "Slide East"
        case 0x45:
            return "Slide West"
        case 0x46:
            return "Slide North"
        case 0x47:
            return "Slide South"
        case 0x48:
            return "Trick House Puzzle 8 Floor"
        case 0x50:
            return "Eastward Current"
        case 0x51:
            return "Westward Current"
        case 0x52:
            return "Northward Current"
        case 0x53:
            return "Southward Current"
        case 0x54:
            return "Spin Right"
        case 0x55:
            return "Spin Left"
        case 0x56:
            return "Spin Up"
        case 0x57:
            return "Spin Down"
        case 0x58:
            return "Stop Spinning"
        case 0x60:
            return "Non-Animated Door" if rse else "Cave Door"
        case 0x61:
            return "Ladder"
        case 0x62:
            return "East Arrow Warp"
        case 0x63:
            return "West Arrow Warp"
        case 0x64:
            return "North Arrow Warp"
        case 0x65:
            return "South Arrow Warp"
        case 0x66:
            return "Fall Warp"
        case 0x67:
            return "Aqua Hideout Warp" if rse else "Regular Warp"
        case 0x68:
            return "Lavaridge Gym 1F Warp"
        case 0x69:
            return "Door Warp"
        case 0x6A:
            return "Escalator Up"
        case 0x6B:
            return "Escalator Down"
        case 0x6C:
            return "Water Door" if rse else "Stair Warp Up/Right"
        case 0x6D:
            return "Water South Arrow Warp" if rse else "Stair Warp Up/Left"
        case 0x6E:
            return "Deep South Warp" if rse else "Stair Warp Down/Right"
        case 0x6F:
            return "Stair Warp Down/Left"
        case 0x70:
            return "Bridge over Ocean"
        case 0x71:
            return "Bridge over Pond (Low)" if rse else "Union Room Warp"
        case 0x72:
            return "Bridge over Pond (Medium)"
        case 0x73:
            return "Bridge over Pond (High)"
        case 0x74:
            return "Pacifidlog Vertical Log (Top)"
        case 0x75:
            return "Pacifidlog Vertical Log (Bottom)"
        case 0x76:
            return "Pacifidlog Horizontal Log (Left)"
        case 0x77:
            return "Pacificlog Horizontal Log (Right)"
        case 0x78:
            return "Fortree Bridge"
        case 0x7A:
            return "Bridge over Pong (Medium) Edge 1"
        case 0x7B:
            return "Bridge over Pong (Medium) Edge 2"
        case 0x7C:
            return "Bridge over Pong (High) Edge 1"
        case 0x7D:
            return "Bridge over Pong (High) Edge 2"
        case 0x7E:
            return "Bridge"
        case 0x7F:
            return "Bike Bridge over Barrier"
        case 0x80:
            return "Counter"
        case 0x81:
            return "Bookshelf"
        case 0x82:
            return "Pokemart Shelf"
        case 0x83:
            return "PC"
        case 0x84:
            if emerald:
                return "Cable Box Results"
            elif frlg:
                return "Signpost"
            else:
                return "Link Battle Records"
        case 0x85:
            return "Region Map"
        case 0x86:
            return "Television"
        case 0x87:
            return "Pokeblock Feeder" if rse else "Pokemon Center Sign"
        case 0x88:
            return "Pokemart Sign"
        case 0x89:
            return "Slot Machine" if rse else "Cabinet"
        case 0x8A:
            return "Roulette" if rse else "Kitchen"
        case 0x8B:
            return "Closed Sootopolis Door" if rse else "Dresser"
        case 0x8C:
            return "Trick House Puzzle Door" if rse else "Snacks"
        case 0x8D:
            return "Petalburg Gym Door" if rse else "Cable Club Wireless Monitor"
        case 0x8E:
            return "Running Shoes Instructions" if rse else "Battle Records"
        case 0x8F:
            return "Questionnaire"
        case 0x90:
            return "Secret Base Spot Red Cave" if rse else "Food"
        case 0x91:
            return "Secret Base Spot Red Cave (Open)" if rse else "Indigo Plateau Sign 1"
        case 0x92:
            return "Secret Base Spot Brown Cave" if rse else "Indigo Plateau Sign 2"
        case 0x93:
            return "Secret Base Spot Brown Cave (Open)" if rse else "Blueprints"
        case 0x94:
            return "Secret Base Spot Yellow Cave" if rse else "Painting"
        case 0x95:
            return "Secret Base Spot Yellow Cave (Open)" if rse else "Power Plant Machine"
        case 0x96:
            return "Secret Base Spot Tree Left" if rse else "Telephone"
        case 0x97:
            return "Secret Base Spot Tree Left (Open)" if rse else "Computer"
        case 0x98:
            return "Secret Base Spot Shrub" if rse else "Advertising Poster"
        case 0x99:
            return "Secret Base Spot Shrub (Open)" if rse else "Tasty-Smelling Food"
        case 0x9A:
            return "Secret Base Spot Blue Cave" if rse else "Trash Bin"
        case 0x9B:
            return "Secret Base Spot Blue Cave (Open)" if rse else "Cup"
        case 0x9C:
            return "Secret Base Spot Tree Right" if rse else "Porthole"
        case 0x9D:
            return "Secret Base Spot Tree Right (Open)" if rse else "Window"
        case 0x9E:
            return "Blinking Lights"
        case 0x9F:
            return "Neatly Lined-up Tools"
        case 0xA0:
            return "Berry Tree Soil" if rse else "Impressive Machine"
        case 0xA1:
            return "Video Game"
        case 0xA2:
            return "Burglary"
        case 0xA3:
            return "Trainer Tower Monitor"
        case 0xB0:
            return "Secret Base PC"
        case 0xB1:
            return "Secret Base Register PC"
        case 0xB2:
            return "Secret Base Scenery"
        case 0xB3:
            return "Secret Base Trainer Spot"
        case 0xB4:
            return "Secret Base Decoration"
        case 0xB5:
            return "Secret Base Large Mat Edge"
        case 0xB7:
            return "Secret Base North Wall"
        case 0xB8:
            return "Secret Base Balloon"
        case 0xB9:
            return "Secret Base Impassable"
        case 0xBA:
            return "Secret Base Glitter Mat"
        case 0xBB:
            return "Secret Base Jump Mat"
        case 0xBC:
            return "Secret Base Spin Mat"
        case 0xBD:
            return "Secret Base Sound Mat"
        case 0xBE:
            return "Secret Base Breakable Door"
        case 0xBF:
            return "Secret Base Sand Ornament"
        case 0xC0:
            return "Impassable North and South"
        case 0xC1:
            return "Impassable West and East"
        case 0xC2:
            return "Secret Base Hole"
        case 0xC3:
            return "Secret Base Large Mat Center"
        case 0xC4:
            return "Secret Base Toy TV or Shield"
        case 0xC5:
            return "Player Room PC On"
        case 0xC6:
            return "Secret Base Decoration Base"
        case 0xC7:
            return "Secret Base Poster"
        case 0xD0:
            return "Muddy Slope" if rse else "Cycling Road Pull Down"
        case 0xD1:
            return "Bumpy Slope" if rse else "Cycling Road Pull Down Grass"
        case 0xD2:
            return "Cracked Floor"
        case 0xD3:
            return "Isolated Vertical Rail"
        case 0xD4:
            return "Isolated Horizontal Rail"
        case 0xD5:
            return "Vertical Rail"
        case 0xD6:
            return "Horizontal Rail"
        case 0xE0:
            return "Picture Book Shelf"
        case 0xE1:
            return "Bookshelf"
        case 0xE2:
            return "Pokemon Center Bookshelf"
        case 0xE3:
            return "Vase"
        case 0xE4:
            return "Trash Can"
        case 0xE5:
            return "Shop Shelf"
        case 0xE6:
            return "Blueprint"
        case 0xE7:
            return "Cable Box Results (2)"
        case 0xE8:
            return "Wireless Box Results"
        case 0xE9:
            return "Trainer Hill Timer"
        case 0xEA:
            return "Sky Pillar Closed Door"
        case _:
            return "???"


MAP_TYPES = ["None", "Town", "City", "Route", "Underground", "Underwater", "Ocean Route", "Unknown", "Indoor",
             "Secret Base"]
WEATHER_TYPES = ["None", "Sunny Clouds", "Sunny", "Rain", "Snow", "Thunderstorm", "Fog (Horizontal)", "Volcanic Ash",
                 "Sandstorm", "Fog (Diagonal)", "Underwater", "Shade", "Drought", "Downpour", "Underwater Bubbles",
                 "Abnormal", "Route 119 Cycle", "Route 123 Cycle"]


class MapLocation:
    def __init__(self, map_header: bytes, map_group: int, map_number: int, local_position: tuple[int, int]):
        self._map_header = map_header
        self.map_group = map_group
        self.map_number = map_number
        self.local_position = local_position

    @cached_property
    def _map_layout(self) -> bytes:
        map_layout_pointer = unpack_uint32(self._map_header[0:4])
        return context.emulator.read_bytes(map_layout_pointer, 24)

    @cached_property
    def _metatile_attributes(self) -> tuple[int, int, int]:
        """
        :return: Metatile Attributes, Collision, Elevation
        """
        mapgrid_metatile_id_mask = 0x3FF

        x, y = self.local_position
        width, height = self.map_size

        map_grid_block = mapgrid_metatile_id_mask
        if 0 <= x < width and 0 <= y < height:
            offset = (x * 2) + (width * y * 2)
            map_data_pointer = unpack_uint32(self._map_layout[12:16])
            map_grid_block = unpack_uint16(context.emulator.read_bytes(map_data_pointer + offset, 2))

        if (map_grid_block & mapgrid_metatile_id_mask) == mapgrid_metatile_id_mask:
            i = (x + 1) & 1
            i += ((y + 1) & 1) * 2
            border_pointer = unpack_uint32(self._map_layout[8:12])
            map_grid_block = unpack_uint16(context.emulator.read_bytes(border_pointer + i * 2, 2)) | 0xC00

        metatile = (map_grid_block & 0x03FF)
        collision = (map_grid_block & 0x0C00) >> 10
        elevation = (map_grid_block & 0xF000) >> 12

        if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
            metatiles_in_primary = 640
            metatiles_in_secondary = 1024
            metatiles_attributes_size = 4
            metatiles_attributes_offset = 0x14
        else:
            metatiles_in_primary = 512
            metatiles_in_secondary = 1024
            metatiles_attributes_size = 2
            metatiles_attributes_offset = 0x10

        attributes_pointer = None
        attribute_offset = None
        if metatile < metatiles_in_primary:
            primary_tileset_pointer = unpack_uint32(self._map_layout[16:20])
            apd = context.emulator.read_bytes(primary_tileset_pointer + metatiles_attributes_offset, 4)
            attributes_pointer = unpack_uint32(apd)
            attribute_offset = metatile * metatiles_attributes_size
        elif metatile < metatiles_in_secondary:
            secondary_tileset_pointer = unpack_uint32(self._map_layout[20:24])
            apd = context.emulator.read_bytes(secondary_tileset_pointer + metatiles_attributes_offset, 4)
            attributes_pointer = unpack_uint32(apd)
            attribute_offset = (metatile - metatiles_in_primary) * metatiles_attributes_size

        if metatiles_attributes_size == 4:
            attribute = unpack_uint32(context.emulator.read_bytes(attributes_pointer + attribute_offset, 4))
        else:
            attribute = unpack_uint16(context.emulator.read_bytes(attributes_pointer + attribute_offset, 2))

        return attribute, collision, elevation

    @cached_property
    def _tile_behaviour(self) -> int:
        return read_symbol("sTileBitAttributes", self._metatile_attributes[0] & 0x3FF, 1)[0]

    @property
    def map_name(self) -> str:
        region_map_section_id = self._map_header[0x14]
        if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
            map_index = region_map_section_id - 0x58
            if 0 <= map_index < 0xC4 - 0x58:
                # The game special-cases the Celadon Department Store by map number
                if self.map_group == 9 and self.map_number <= 6:
                    return "CELADON DEPT."

                map_name_pointer = unpack_uint32(read_symbol("sMapNames", (region_map_section_id - 0x58) * 4, 4))
            else:
                map_name_pointer = 0
        else:
            map_name_pointer = unpack_uint32(read_symbol("gRegionMapEntries", region_map_section_id * 8 + 4, 4))
        if map_name_pointer > 0:
            return decode_string(context.emulator.read_bytes(map_name_pointer, 32))
        else:
            return "???"

    @property
    def map_size(self) -> tuple[int, int]:
        return unpack_uint32(self._map_layout[0:4]), unpack_uint32(self._map_layout[4:8])

    @property
    def map_type(self) -> str:
        return MAP_TYPES[self._map_header[0x17]]

    @property
    def weather(self) -> str:
        return WEATHER_TYPES[self._map_header[0x16]]

    @property
    def tile_type(self) -> str:
        return _get_tile_type_name(self._metatile_attributes[0] & 0xFF)

    @property
    def collision(self) -> int:
        return self._metatile_attributes[1]

    @property
    def elevation(self) -> int:
        return self._metatile_attributes[2]

    @property
    def has_encounters(self) -> bool:
        if context.rom.game_title in ["POKEMON FIRE", "POKEMON SAPP"]:
            return bool(self._metatile_attributes[0] & 0x0700_0000)
        else:
            return bool(self._tile_behaviour & 1)

    @property
    def is_surfable(self) -> bool:
        if context.rom.game_title in ["POKEMON FIRE", "POKEMON SAPP"]:
            return self.tile_type in ["Pond Water", "Fast Water", "Deep Water", "Waterfall", "Ocean Water",
                                      "Cycling Road Water", "Eastward Current", "Westward Current", "Northward Current",
                                      "Southward Current"]
        else:
            return bool(self._tile_behaviour & 2)

    @property
    def is_cycling_possible(self) -> bool:
        if self.map_type == "Indoor":
            return False

        if self.tile_type in ["No Running", "Long Grass", "Hot Springs", "Pacifidlog Vertical Log (Top)",
                              "Pacifidlog Vertical Log (Bottom)", "Pacifidlog Horizontal Log (Left)",
                              "Pacifidlog Horizontal Log (Right)", "Fortree Bridge"]:
            return False

        if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
            return bool(self._map_header[0x18])
        else:
            return bool(self._map_header[0x1A] & 0b0001)

    @property
    def is_escaping_possible(self) -> bool:
        if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
            return bool(self._map_header[0x19] & 0b0001)
        else:
            return bool(self._map_header[0x1A] & 0b0010)

    @property
    def is_running_possible(self) -> bool:
        if self.map_type == "Indoor":
            return False

        if self.tile_type in ["No Running", "Long Grass", "Hot Springs", "Pacifidlog Vertical Log (Top)",
                              "Pacifidlog Vertical Log (Bottom)", "Pacifidlog Horizontal Log (Left)",
                              "Pacifidlog Horizontal Log (Right)", "Fortree Bridge"]:
            return False

        if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
            return bool(self._map_header[0x19] & 0b0010)
        else:
            return bool(self._map_header[0x1A] & 0b0100)

    @property
    def is_map_name_popup_shown(self) -> bool:
        if context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]:
            return bool(self._map_header[0x19] & 0b0100)
        else:
            return bool(self._map_header[0x1A] & 0b1000)

    @property
    def is_dark_cave(self) -> bool:
        return bool(self._map_header[0x15] & 0b0001)


def get_map_data_for_current_position() -> MapLocation:
    from modules.trainer import trainer
    map_group, map_number = trainer.get_map()
    return MapLocation(read_symbol("gMapHeader"), map_group, map_number, trainer.get_coords())


def get_map_data(map_group: int, map_number: int, local_position: tuple[int, int]) -> MapLocation:
    map_group_pointer = unpack_uint32(read_symbol("gMapGroups", map_group * 4, 4))
    map_number_pointer = unpack_uint32(context.emulator.read_bytes(map_group_pointer + 4 * map_number, 4))
    map_header = context.emulator.read_bytes(map_number_pointer, 0x1C)
    return MapLocation(map_header, map_group, map_number, local_position)
