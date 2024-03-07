import itertools
import string
import struct
from dataclasses import dataclass
from functools import cached_property
from typing import Literal

from modules.context import context
from modules.game import decode_string, get_event_flag_name, get_event_var_name
from modules.memory import get_save_block, get_symbol_name, read_symbol, unpack_uint16, unpack_uint32
from modules.pokemon import Item, Species, get_item_by_index, get_species_by_index


def _get_tile_type_name(tile_type: int):
    if context.rom.is_rs:
        rse = True
        frlg = False
        emerald = False
    elif context.rom.is_emerald:
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


MAP_TYPES = [
    "None",
    "Town",
    "City",
    "Route",
    "Underground",
    "Underwater",
    "Ocean Route",
    "Unknown",
    "Indoor",
    "Secret Base",
]
WEATHER_TYPES = [
    "None",
    "Sunny Clouds",
    "Sunny",
    "Rain",
    "Snow",
    "Thunderstorm",
    "Fog (Horizontal)",
    "Volcanic Ash",
    "Sandstorm",
    "Fog (Diagonal)",
    "Underwater",
    "Shade",
    "Drought",
    "Downpour",
    "Underwater Bubbles",
    "Abnormal",
    "Route 119 Cycle",
    "Route 123 Cycle",
]


class MapConnection:
    def __init__(self, data: bytes):
        self._data = data

    @property
    def direction(self) -> str:
        match self._data[0]:
            case 1:
                return "South"
            case 2:
                return "North"
            case 3:
                return "West"
            case 4:
                return "East"
            case 5:
                return "Dive"
            case 6:
                return "Emerge"
            case _:
                return "???"

    @property
    def offset(self) -> int:
        return struct.unpack("<i", self._data[4:8])[0]

    @property
    def destination_map_group(self) -> int:
        return self._data[8]

    @property
    def destination_map_number(self) -> int:
        return self._data[9]

    @property
    def destination_map(self) -> "MapLocation":
        return get_map_data((self.destination_map_group, self.destination_map_number), (0, 0))

    def to_dict(self) -> dict:
        return {
            "direction": self.direction,
            "offset": self.offset,
            "destination": {
                "map_group": self.destination_map_group,
                "map_number": self.destination_map_number,
                "map_name": self.destination_map.map_name,
            },
        }


class MapWarp:
    def __init__(self, data: bytes):
        self._data = data

    @property
    def local_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self._data[:2]), unpack_uint16(self._data[2:4])

    @property
    def elevation(self) -> int:
        return self._data[4]

    @property
    def destination_warp_id(self) -> int:
        return self._data[5]

    @property
    def destination_map_group(self) -> int:
        return self._data[7]

    @property
    def destination_map_number(self) -> int:
        return self._data[6]

    @property
    def destination_location(self) -> "MapLocation":
        map_group = self.destination_map_group
        map_number = self.destination_map_number
        warp_id = self.destination_warp_id

        # There is a special case for 'dynamic warps' that have their destination set
        # in the player's save data.
        if map_group == 127 and map_number == 127:
            map_group, map_number, warp_id = get_save_block(1, offset=0x14, size=3)

        destination_map = get_map_data((map_group, map_number), (0, 0))

        # Another special case is when there is no corresponding target warp on the
        # destination map we use _this_ warp's coordinates as the destination.
        if warp_id == 0xFF:
            destination_map.local_position = self.local_coordinates
        else:
            destination_warp = destination_map.warps[warp_id]
            destination_map.local_position = destination_warp.local_coordinates
        return destination_map

    def to_dict(self) -> dict:
        return {
            "local_coordinates": self.local_coordinates,
            "elevation": self.elevation,
            "destination": {
                "warp_id": self.destination_warp_id,
                "map_group": self.destination_map_group,
                "map_number": self.destination_map_number,
                "map_name": self.destination_location.map_name,
            },
        }


class MapCoordEvent:
    """
    A 'coord event' is an event that gets triggered by entering a tile.
    """

    def __init__(self, data: bytes):
        self._data = data

    @property
    def local_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self._data[:2]), unpack_uint16(self._data[2:4])

    @property
    def elevation(self) -> int:
        return self._data[4]

    @property
    def trigger_var_number(self) -> int:
        return unpack_uint16(self._data[6:8]) - 0x4000

    @property
    def trigger_value(self) -> int:
        return unpack_uint16(self._data[8:10])

    @property
    def script_pointer(self) -> int:
        return unpack_uint32(self._data[12:16])

    @property
    def script_symbol(self) -> str:
        symbol = get_symbol_name(self.script_pointer, pretty_name=True)
        return hex(self.script_pointer) if symbol == "" else symbol

    def to_dict(self) -> dict:
        return {
            "local_coordinates": self.local_coordinates,
            "trigger_var": get_event_var_name(self.trigger_var_number),
            "trigger_value": self.trigger_value,
            "elevation": self.elevation,
            "script": self.script_symbol,
        }


class MapBgEvent:
    """
    A 'BG event' is an event that triggers when interacting with a tile.
    """

    def __init__(self, data: bytes):
        self._data = data

    @property
    def local_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self._data[:2]), unpack_uint16(self._data[2:4])

    @property
    def elevation(self) -> int:
        return self._data[4]

    @property
    def kind(self) -> Literal["Script", "Hidden Item", "Secret Base", "???"]:
        match self._data[5]:
            case 0 | 1 | 2 | 3 | 4:
                return "Script"
            case 7:
                return "Hidden Item"
            case 8:
                return "Secret Base"
            case _:
                return "???"

    @property
    def player_facing_direction(self) -> str:
        """This only has meaning if `kind` is 'Script'."""
        match self._data[5]:
            case 0:
                return "Any"
            case 1:
                return "Up"
            case 2:
                return "Down"
            case 3:
                return "Right"
            case 4:
                return "Left"
            case _:
                return "???"

    @property
    def script_pointer(self) -> int:
        """This only has meaning if `kind` is 'Script'."""
        return unpack_uint32(self._data[8:12])

    @property
    def script_symbol(self) -> str:
        """This only has meaning if `kind` is 'Script'."""
        symbol = get_symbol_name(self.script_pointer, pretty_name=True)
        return hex(self.script_pointer) if symbol == "" else symbol

    @property
    def hidden_item(self) -> Item:
        """This only has meaning if `kind` is 'Hidden Item'."""
        return get_item_by_index(unpack_uint16(self._data[8:10]))

    @property
    def hidden_item_flag_id(self) -> int:
        """This only has meaning if `kind` is 'Hidden Item'."""
        return unpack_uint16(self._data[10:12])

    @property
    def secret_base_id(self) -> int:
        """This only has meaning if `kind` is 'Secret Base'."""
        return unpack_uint32(self._data[8:12])

    def to_dict(self) -> dict:
        kind = self.kind
        data = {
            "local_coordinates": self.local_coordinates,
            "elevation": self.elevation,
            "kind": kind,
        }

        match kind:
            case "Script":
                data["player_facing_direction"] = self.player_facing_direction
                data["script"] = self.script_symbol
            case "Hidden Item":
                data["item"] = self.hidden_item.name
                data["flag"] = get_event_flag_name(self.hidden_item_flag_id)
            case "Secret Base":
                data["secret_base_id"] = self.secret_base_id

        return data


_map_layout_cache: dict[tuple[int, int], bytes] = {}


class MapLocation:
    def __init__(self, map_header: bytes, map_group: int, map_number: int, local_position: tuple[int, int]):
        self._map_header = map_header
        self.map_group = map_group
        self.map_number = map_number
        self.local_position = local_position

    @cached_property
    def _map_layout(self) -> bytes:
        global _map_layout_cache
        if self.map_group_and_number not in _map_layout_cache:
            map_layout_pointer = unpack_uint32(self._map_header[:4])
            _map_layout_cache[self.map_group_and_number] = context.emulator.read_bytes(map_layout_pointer, 24)
        return _map_layout_cache[self.map_group_and_number]

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

        metatile = map_grid_block & 0x03FF
        collision = (map_grid_block & 0x0C00) >> 10
        elevation = (map_grid_block & 0xF000) >> 12

        if context.rom.is_frlg:
            metatiles_in_primary = 640
            metatiles_attributes_size = 4
            metatiles_attributes_offset = 0x14
        else:
            metatiles_in_primary = 512
            metatiles_attributes_size = 2
            metatiles_attributes_offset = 0x10

        metatiles_in_secondary = 1024
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

    @cached_property
    def _event_list(self) -> bytes | None:
        events_list_pointer = unpack_uint32(self._map_header[0x04:0x08])
        if events_list_pointer == 0:
            return None
        else:
            return context.emulator.read_bytes(events_list_pointer, 20)

    @property
    def map_group_and_number(self) -> tuple[int, int]:
        return self.map_group, self.map_number

    @property
    def map_name(self) -> str:
        region_map_section_id = self._map_header[0x14]
        if context.rom.is_frlg:
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
        return unpack_uint32(self._map_layout[:4]), unpack_uint32(self._map_layout[4:8])

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
        if context.rom.is_frlg:
            return bool(self._metatile_attributes[0] & 0x0700_0000)
        else:
            return bool(self._tile_behaviour & 1)

    @property
    def is_surfable(self) -> bool:
        if context.rom.is_frlg:
            return self.tile_type in [
                "Pond Water",
                "Fast Water",
                "Deep Water",
                "Waterfall",
                "Ocean Water",
                "Cycling Road Water",
                "Eastward Current",
                "Westward Current",
                "Northward Current",
                "Southward Current",
            ]
        else:
            return bool(self._tile_behaviour & 2)

    @property
    def is_cycling_possible(self) -> bool:
        if self.map_type == "Indoor":
            return False

        if self.tile_type in [
            "No Running",
            "Long Grass",
            "Hot Springs",
            "Pacifidlog Vertical Log (Top)",
            "Pacifidlog Vertical Log (Bottom)",
            "Pacifidlog Horizontal Log (Left)",
            "Pacifidlog Horizontal Log (Right)",
            "Fortree Bridge",
        ]:
            return False

        if context.rom.is_frlg:
            return bool(self._map_header[0x18])
        else:
            return bool(self._map_header[0x1A] & 0b0001)

    @property
    def is_escaping_possible(self) -> bool:
        if context.rom.is_frlg:
            return bool(self._map_header[0x19] & 0b0001)
        else:
            return bool(self._map_header[0x1A] & 0b0010)

    @property
    def is_running_possible(self) -> bool:
        if self.map_type == "Indoor":
            return False

        if self.tile_type in [
            "No Running",
            "Long Grass",
            "Hot Springs",
            "Pacifidlog Vertical Log (Top)",
            "Pacifidlog Vertical Log (Bottom)",
            "Pacifidlog Horizontal Log (Left)",
            "Pacifidlog Horizontal Log (Right)",
            "Fortree Bridge",
        ]:
            return False

        if context.rom.is_frlg:
            return bool(self._map_header[0x19] & 0b0010)
        else:
            return bool(self._map_header[0x1A] & 0b0100)

    @property
    def is_map_name_popup_shown(self) -> bool:
        if context.rom.is_frlg:
            return bool(self._map_header[0x19] & 0b0100)
        else:
            return bool(self._map_header[0x1A] & 0b1000)

    @property
    def is_dark_cave(self) -> bool:
        return bool(self._map_header[0x15] & 0b0001)

    @property
    def connections(self) -> list[MapConnection]:
        list_of_connections_pointer = unpack_uint32(self._map_header[0x0C:0x10])
        if list_of_connections_pointer == 0:
            return []

        list_of_connections = context.emulator.read_bytes(list_of_connections_pointer, 0x08)
        count = unpack_uint32(list_of_connections[:4])
        connection_pointer = unpack_uint32(list_of_connections[4:8])
        if connection_pointer == 0:
            return []

        size_of_struct = 12
        data = context.emulator.read_bytes(connection_pointer, size_of_struct * count)

        return [MapConnection(data[size_of_struct * index : size_of_struct * (index + 1)]) for index in range(count)]

    @property
    def warps(self) -> list[MapWarp]:
        warp_count = self._event_list[1]
        warp_pointer = unpack_uint32(self._event_list[8:12])
        if warp_count == 0 or warp_pointer == 0:
            return []

        size_of_struct = 8
        data = context.emulator.read_bytes(warp_pointer, warp_count * size_of_struct)

        return [MapWarp(data[size_of_struct * index : size_of_struct * (index + 1)]) for index in range(warp_count)]

    @property
    def objects(self) -> list["ObjectEventTemplate"]:
        object_event_count = self._event_list[0]
        object_event_pointer = unpack_uint32(self._event_list[4:8])
        if object_event_count == 0 or object_event_pointer == 0:
            return []

        size_of_struct = 24
        data = context.emulator.read_bytes(object_event_pointer, size_of_struct * object_event_count)

        return [
            ObjectEventTemplate(data[size_of_struct * index : size_of_struct * (index + 1)])
            for index in range(object_event_count)
        ]

    @property
    def coord_events(self) -> list[MapCoordEvent]:
        coord_event_count = self._event_list[2]
        coord_event_pointer = unpack_uint32(self._event_list[12:16])
        if coord_event_count == 0 or coord_event_pointer == 0:
            return []

        size_of_struct = 16
        data = context.emulator.read_bytes(coord_event_pointer, size_of_struct * coord_event_count)

        return [
            MapCoordEvent(data[size_of_struct * index : size_of_struct * (index + 1)])
            for index in range(coord_event_count)
        ]

    @property
    def bg_events(self) -> list[MapBgEvent]:
        bg_event_count = self._event_list[3]
        bg_event_pointer = unpack_uint32(self._event_list[16:20])
        if bg_event_count == 0 or bg_event_pointer == 0:
            return []

        size_of_struct = 12
        data = context.emulator.read_bytes(bg_event_pointer, size_of_struct * bg_event_count)

        return [
            MapBgEvent(data[size_of_struct * index : size_of_struct * (index + 1)]) for index in range(bg_event_count)
        ]

    def all_tiles(self) -> list[list["MapLocation"]]:
        result = []

        for x in range(self.map_size[0]):
            row = [
                MapLocation(self._map_header, self.map_group, self.map_number, (x, y)) for y in range(self.map_size[1])
            ]
            result.append(row)

        return result

    def dict_for_map(self) -> dict:
        return {
            "map_group": self.map_group,
            "map_number": self.map_number,
            "name": self.map_name,
            "size": self.map_size,
            "type": self.map_type,
            "weather": self.weather,
            "is_cycling_possible": self.is_cycling_possible,
            "is_escaping_possible": self.is_escaping_possible,
            "is_running_possible": self.is_running_possible,
            "is_map_name_popup_shown": self.is_map_name_popup_shown,
            "is_dark_cave": self.is_dark_cave,
            "connections": [c.to_dict() for c in self.connections],
            "warps": [w.to_dict() for w in self.warps],
            "tile_enter_events": [e.to_dict() for e in self.coord_events],
            "tile_interact_events": [e.to_dict() for e in self.bg_events],
            "object_templates": [t.to_dict() for t in self.objects],
        }

    def dict_for_tile(self) -> dict:
        return {
            "local_coordinates": self.local_position,
            "elevation": self.elevation,
            "type": self.tile_type,
            "has_encounters": self.has_encounters,
            "collision": self.collision,
            "is_surfing_possible": self.is_surfable,
        }

    def dicts_for_all_tiles(self) -> list[list[dict]]:
        result = []
        for row in self.all_tiles():
            result_row = [tile.dict_for_tile() for tile in row]
            result.append(result_row)
        return result


class ObjectEvent:
    MOVEMENT_TYPES = [
        "NONE",
        "LOOK_AROUND",
        "WANDER_AROUND",
        "WANDER_UP_AND_DOWN",
        "WANDER_DOWN_AND_UP",
        "WANDER_LEFT_AND_RIGHT",
        "WANDER_RIGHT_AND_LEFT",
        "FACE_UP",
        "FACE_DOWN",
        "FACE_LEFT",
        "FACE_RIGHT",
        "PLAYER",
        "BERRY_TREE_GROWTH",
        "FACE_DOWN_AND_UP",
        "FACE_LEFT_AND_RIGHT",
        "FACE_UP_AND_LEFT",
        "FACE_UP_AND_RIGHT",
        "FACE_DOWN_AND_LEFT",
        "FACE_DOWN_AND_RIGHT",
        "FACE_DOWN_UP_AND_LEFT",
        "FACE_DOWN_UP_AND_RIGHT",
        "FACE_UP_LEFT_AND_RIGHT",
        "FACE_DOWN_LEFT_AND_RIGHT",
        "ROTATE_COUNTERCLOCKWISE",
        "ROTATE_CLOCKWISE",
        "WALK_UP_AND_DOWN",
        "WALK_DOWN_AND_UP",
        "WALK_LEFT_AND_RIGHT",
        "WALK_RIGHT_AND_LEFT",
        "WALK_SEQUENCE_UP_RIGHT_LEFT_DOWN",
        "WALK_SEQUENCE_RIGHT_LEFT_DOWN_UP",
        "WALK_SEQUENCE_DOWN_UP_RIGHT_LEFT",
        "WALK_SEQUENCE_LEFT_DOWN_UP_RIGHT",
        "WALK_SEQUENCE_UP_LEFT_RIGHT_DOWN",
        "WALK_SEQUENCE_LEFT_RIGHT_DOWN_UP",
        "WALK_SEQUENCE_DOWN_UP_LEFT_RIGHT",
        "WALK_SEQUENCE_RIGHT_DOWN_UP_LEFT",
        "WALK_SEQUENCE_LEFT_UP_DOWN_RIGHT",
        "WALK_SEQUENCE_UP_DOWN_RIGHT_LEFT",
        "WALK_SEQUENCE_RIGHT_LEFT_UP_DOWN",
        "WALK_SEQUENCE_DOWN_RIGHT_LEFT_UP",
        "WALK_SEQUENCE_RIGHT_UP_DOWN_LEFT",
        "WALK_SEQUENCE_UP_DOWN_LEFT_RIGHT",
        "WALK_SEQUENCE_LEFT_RIGHT_UP_DOWN",
        "WALK_SEQUENCE_DOWN_LEFT_RIGHT_UP",
        "WALK_SEQUENCE_UP_LEFT_DOWN_RIGHT",
        "WALK_SEQUENCE_DOWN_RIGHT_UP_LEFT",
        "WALK_SEQUENCE_LEFT_DOWN_RIGHT_UP",
        "WALK_SEQUENCE_RIGHT_UP_LEFT_DOWN",
        "WALK_SEQUENCE_UP_RIGHT_DOWN_LEFT",
        "WALK_SEQUENCE_DOWN_LEFT_UP_RIGHT",
        "WALK_SEQUENCE_LEFT_UP_RIGHT_DOWN",
        "WALK_SEQUENCE_RIGHT_DOWN_LEFT_UP",
        "COPY_PLAYER",
        "COPY_PLAYER_OPPOSITE",
        "COPY_PLAYER_COUNTERCLOCKWISE",
        "COPY_PLAYER_CLOCKWISE",
        "TREE_DISGUISE",
        "MOUNTAIN_DISGUISE",
        "COPY_PLAYER_IN_GRASS",
        "COPY_PLAYER_OPPOSITE_IN_GRASS",
        "COPY_PLAYER_COUNTERCLOCKWISE_IN_GRASS",
        "COPY_PLAYER_CLOCKWISE_IN_GRASS",
        "BURIED",
        "WALK_IN_PLACE_DOWN",
        "WALK_IN_PLACE_UP",
        "WALK_IN_PLACE_LEFT",
        "WALK_IN_PLACE_RIGHT",
        "WALK_IN_PLACE_FAST_DOWN",
        "WALK_IN_PLACE_FAST_UP",
        "WALK_IN_PLACE_FAST_LEFT",
        "WALK_IN_PLACE_FAST_RIGHT",
        "JOG_IN_PLACE_DOWN",
        "JOG_IN_PLACE_UP",
        "JOG_IN_PLACE_LEFT",
        "JOG_IN_PLACE_RIGHT",
        "INVISIBLE",
        "RAISE_HAND_AND_STOP",
        "RAISE_HAND_AND_JUMP",
        "RAISE_HAND_AND_SWIM",
        "WANDER_AROUND_SLOWER",
    ]

    MOVEMENT_ACTIONS = {
        0x0: "FACE_DOWN",
        0x1: "FACE_UP",
        0x2: "FACE_LEFT",
        0x3: "FACE_RIGHT",
        0x4: "FACE_DOWN_FAST",
        0x5: "FACE_UP_FAST",
        0x6: "FACE_LEFT_FAST",
        0x7: "FACE_RIGHT_FAST",
        0x8: "WALK_SLOWER_DOWN",
        0x9: "WALK_SLOWER_UP",
        0xA: "WALK_SLOWER_LEFT",
        0xB: "WALK_SLOWER_RIGHT",
        0xC: "WALK_SLOW_DOWN",
        0xD: "WALK_SLOW_UP",
        0xE: "WALK_SLOW_LEFT",
        0xF: "WALK_SLOW_RIGHT",
        0x10: "WALK_NORMAL_DOWN",
        0x11: "WALK_NORMAL_UP",
        0x12: "WALK_NORMAL_LEFT",
        0x13: "WALK_NORMAL_RIGHT",
        0x14: "JUMP_2_DOWN",
        0x15: "JUMP_2_UP",
        0x16: "JUMP_2_LEFT",
        0x17: "JUMP_2_RIGHT",
        0x18: "DELAY_1",
        0x19: "DELAY_2",
        0x1A: "DELAY_4",
        0x1B: "DELAY_8",
        0x1C: "DELAY_16",
        0x1D: "WALK_FAST_DOWN",
        0x1E: "WALK_FAST_UP",
        0x1F: "WALK_FAST_LEFT",
        0x20: "WALK_FAST_RIGHT",
        0x21: "WALK_IN_PLACE_SLOW_DOWN",
        0x22: "WALK_IN_PLACE_SLOW_UP",
        0x23: "WALK_IN_PLACE_SLOW_LEFT",
        0x24: "WALK_IN_PLACE_SLOW_RIGHT",
        0x25: "WALK_IN_PLACE_NORMAL_DOWN",
        0x26: "WALK_IN_PLACE_NORMAL_UP",
        0x27: "WALK_IN_PLACE_NORMAL_LEFT",
        0x28: "WALK_IN_PLACE_NORMAL_RIGHT",
        0x29: "WALK_IN_PLACE_FAST_DOWN",
        0x2A: "WALK_IN_PLACE_FAST_UP",
        0x2B: "WALK_IN_PLACE_FAST_LEFT",
        0x2C: "WALK_IN_PLACE_FAST_RIGHT",
        0x2D: "WALK_IN_PLACE_FASTER_DOWN",
        0x2E: "WALK_IN_PLACE_FASTER_UP",
        0x2F: "WALK_IN_PLACE_FASTER_LEFT",
        0x30: "WALK_IN_PLACE_FASTER_RIGHT",
        0x31: "RIDE_WATER_CURRENT_DOWN",
        0x32: "RIDE_WATER_CURRENT_UP",
        0x33: "RIDE_WATER_CURRENT_LEFT",
        0x34: "RIDE_WATER_CURRENT_RIGHT",
        0x35: "WALK_FASTER_DOWN",
        0x36: "WALK_FASTER_UP",
        0x37: "WALK_FASTER_LEFT",
        0x38: "WALK_FASTER_RIGHT",
        0x39: "SLIDE_DOWN",
        0x3A: "SLIDE_UP",
        0x3B: "SLIDE_LEFT",
        0x3C: "SLIDE_RIGHT",
        0x3D: "PLAYER_RUN_DOWN",
        0x3E: "PLAYER_RUN_UP",
        0x3F: "PLAYER_RUN_LEFT",
        0x40: "PLAYER_RUN_RIGHT",
        0x41: "PLAYER_RUN_DOWN_SLOW",
        0x42: "PLAYER_RUN_UP_SLOW",
        0x43: "PLAYER_RUN_LEFT_SLOW",
        0x44: "PLAYER_RUN_RIGHT_SLOW",
        0x45: "START_ANIM_IN_DIRECTION",
        0x46: "JUMP_SPECIAL_DOWN",
        0x47: "JUMP_SPECIAL_UP",
        0x48: "JUMP_SPECIAL_LEFT",
        0x49: "JUMP_SPECIAL_RIGHT",
        0x4A: "FACE_PLAYER",
        0x4B: "FACE_AWAY_PLAYER",
        0x4C: "LOCK_FACING_DIRECTION",
        0x4D: "UNLOCK_FACING_DIRECTION",
        0x4E: "JUMP_DOWN",
        0x4F: "JUMP_UP",
        0x50: "JUMP_LEFT",
        0x51: "JUMP_RIGHT",
        0x52: "JUMP_IN_PLACE_DOWN",
        0x53: "JUMP_IN_PLACE_UP",
        0x54: "JUMP_IN_PLACE_LEFT",
        0x55: "JUMP_IN_PLACE_RIGHT",
        0x56: "JUMP_IN_PLACE_DOWN_UP",
        0x57: "JUMP_IN_PLACE_UP_DOWN",
        0x58: "JUMP_IN_PLACE_LEFT_RIGHT",
        0x59: "JUMP_IN_PLACE_RIGHT_LEFT",
        0x5A: "FACE_ORIGINAL_DIRECTION",
        0x5B: "NURSE_JOY_BOW_DOWN",
        0x5C: "ENABLE_JUMP_LANDING_GROUND_EFFECT",
        0x5D: "DISABLE_JUMP_LANDING_GROUND_EFFECT",
        0x5E: "DISABLE_ANIMATION",
        0x5F: "RESTORE_ANIMATION",
        0x60: "SET_INVISIBLE",
        0x61: "SET_VISIBLE",
        0x62: "EMOTE_EXCLAMATION_MARK",
        0x63: "EMOTE_QUESTION_MARK",
        0x64: "EMOTE_X",
        0x65: "EMOTE_DOUBLE_EXCL_MARK",
        0x66: "EMOTE_SMILE",
        0x67: "REVEAL_TRAINER",
        0x68: "ROCK_SMASH_BREAK",
        0x69: "CUT_TREE",
        0x6A: "SET_FIXED_PRIORITY",
        0x6B: "CLEAR_FIXED_PRIORITY",
        0x6C: "INIT_AFFINE_ANIM",
        0x6D: "CLEAR_AFFINE_ANIM",
        0x6E: "WALK_DOWN_START_AFFINE",
        0x6F: "WALK_DOWN_AFFINE",
        0x70: "ACRO_WHEELIE_FACE_DOWN",
        0x71: "ACRO_WHEELIE_FACE_UP",
        0x72: "ACRO_WHEELIE_FACE_LEFT",
        0x73: "ACRO_WHEELIE_FACE_RIGHT",
        0x74: "ACRO_POP_WHEELIE_DOWN",
        0x75: "ACRO_POP_WHEELIE_UP",
        0x76: "ACRO_POP_WHEELIE_LEFT",
        0x77: "ACRO_POP_WHEELIE_RIGHT",
        0x78: "ACRO_END_WHEELIE_FACE_DOWN",
        0x79: "ACRO_END_WHEELIE_FACE_UP",
        0x7A: "ACRO_END_WHEELIE_FACE_LEFT",
        0x7B: "ACRO_END_WHEELIE_FACE_RIGHT",
        0x7C: "ACRO_WHEELIE_HOP_FACE_DOWN",
        0x7D: "ACRO_WHEELIE_HOP_FACE_UP",
        0x7E: "ACRO_WHEELIE_HOP_FACE_LEFT",
        0x7F: "ACRO_WHEELIE_HOP_FACE_RIGHT",
        0x80: "ACRO_WHEELIE_HOP_DOWN",
        0x81: "ACRO_WHEELIE_HOP_UP",
        0x82: "ACRO_WHEELIE_HOP_LEFT",
        0x83: "ACRO_WHEELIE_HOP_RIGHT",
        0x84: "ACRO_WHEELIE_JUMP_DOWN",
        0x85: "ACRO_WHEELIE_JUMP_UP",
        0x86: "ACRO_WHEELIE_JUMP_LEFT",
        0x87: "ACRO_WHEELIE_JUMP_RIGHT",
        0x88: "ACRO_WHEELIE_IN_PLACE_DOWN",
        0x89: "ACRO_WHEELIE_IN_PLACE_UP",
        0x8A: "ACRO_WHEELIE_IN_PLACE_LEFT",
        0x8B: "ACRO_WHEELIE_IN_PLACE_RIGHT",
        0x8C: "ACRO_POP_WHEELIE_MOVE_DOWN",
        0x8D: "ACRO_POP_WHEELIE_MOVE_UP",
        0x8E: "ACRO_POP_WHEELIE_MOVE_LEFT",
        0x8F: "ACRO_POP_WHEELIE_MOVE_RIGHT",
        0x90: "ACRO_WHEELIE_MOVE_DOWN",
        0x91: "ACRO_WHEELIE_MOVE_UP",
        0x92: "ACRO_WHEELIE_MOVE_LEFT",
        0x93: "ACRO_WHEELIE_MOVE_RIGHT",
        0x94: "SPIN_DOWN",
        0x95: "SPIN_UP",
        0x96: "SPIN_LEFT",
        0x97: "SPIN_RIGHT",
        0x98: "RAISE_HAND_AND_STOP",
        0x99: "RAISE_HAND_AND_JUMP",
        0x9A: "RAISE_HAND_AND_SWIM",
        0x9B: "WALK_SLOWEST_DOWN",
        0x9C: "WALK_SLOWEST_UP",
        0x9D: "WALK_SLOWEST_LEFT",
        0x9E: "WALK_SLOWEST_RIGHT",
        0x9F: "SHAKE_HEAD_OR_WALK_IN_PLACE",
        0xA0: "GLIDE_DOWN",
        0xA1: "GLIDE_UP",
        0xA2: "GLIDE_LEFT",
        0xA3: "GLIDE_RIGHT",
        0xA4: "FLY_UP",
        0xA5: "FLY_DOWN",
        0xA6: "JUMP_SPECIAL_WITH_EFFECT_DOWN",
        0xA7: "JUMP_SPECIAL_WITH_EFFECT_UP",
        0xA8: "JUMP_SPECIAL_WITH_EFFECT_LEFT",
        0xA9: "JUMP_SPECIAL_WITH_EFFECT_RIGHT",
        0xFE: "STEP_END",
        0xFF: "NONE",
    }

    def __init__(self, data: bytes):
        self._data = data

    def __eq__(self, other):
        if isinstance(other, ObjectEvent):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ObjectEvent):
            return other._data != self._data
        else:
            return NotImplemented

    @property
    def flags(self) -> list[str]:
        flag_names = [
            "active",
            "singleMovementActive",
            "triggerGroundEffectsOnMove",
            "triggerGroundEffectsOnStop",
            "disableCoveringGroundEffects",
            "landingJump",
            "heldMovementActive",
            "heldMovementFinished",
            "frozen",
            "facingDirectionLocked",
            "disableAnim",
            "enableAnim",
            "inanimate",
            "invisible",
            "offScreen",
            "trackedByCamera",
            "isPlayer",
            "hasReflection",
            "inShortGrass",
            "inShallowFlowingWater",
            "inSandPile",
            "inHotSprings",
            "hasShadow",
            "spriteAnimPausedBackup",
            "spriteAffineAnimPausedBackup",
            "disableJumpLandingGroundEffect",
            "fixedPriority",
            "hideReflection",
        ]

        bitmap = unpack_uint32(self._data[:4])
        return [flag_names[i] for i in range(len(flag_names)) if (bitmap >> i) & 0x01]

    @property
    def sprite_id(self) -> int:
        return self._data[4]

    @property
    def graphics_id(self) -> int:
        return self._data[5]

    @property
    def movement_type(self) -> str:
        return string.capwords(self.MOVEMENT_TYPES[self._data[6]].replace("_", " "))

    @property
    def trainer_type(self) -> str:
        match self._data[7]:
            case 0:
                return "None"
            case 1:
                return "Normal"
            case 2:
                return "See All Directions"
            case 3:
                return "Buried"

    @property
    def local_id(self) -> int:
        return self._data[8]

    @property
    def map_num(self) -> int:
        return self._data[9]

    @property
    def map_group(self) -> int:
        return self._data[10]

    @property
    def map_group_and_number(self) -> tuple[int, int]:
        return self.map_group, self.map_num

    @property
    def current_elevation(self) -> int:
        return self._data[11] & 0x0F

    @property
    def previous_elevation(self) -> int:
        return (self._data[11] & 0xF0) >> 4

    @property
    def initial_coords(self) -> tuple[int, int]:
        return unpack_uint16(self._data[0x0C:0x0E]) - 7, unpack_uint16(self._data[0x0E:0x10]) - 7

    @property
    def current_coords(self) -> tuple[int, int]:
        return unpack_uint16(self._data[0x10:0x12]) - 7, unpack_uint16(self._data[0x12:0x14]) - 7

    @property
    def previous_coords(self) -> tuple[int, int]:
        return unpack_uint16(self._data[0x14:0x16]) - 7, unpack_uint16(self._data[0x16:0x18]) - 7

    @property
    def facing_direction(self) -> str:
        direction = unpack_uint16(self._data[0x18:0x1A]) & 0x000F
        match direction:
            case 1:
                return "Down"
            case 2:
                return "Up"
            case 3:
                return "Left"
            case 4:
                return "Right"

    @property
    def movement_direction(self) -> str:
        direction = (unpack_uint16(self._data[0x18:0x1A]) & 0x00F0) >> 4
        match direction:
            case 1:
                return "Down"
            case 2:
                return "Up"
            case 3:
                return "Left"
            case 4:
                return "Right"

    @property
    def range_x(self) -> int:
        return (unpack_uint16(self._data[0x18:0x1A]) & 0x0F00) >> 8

    @property
    def range_y(self) -> int:
        return (unpack_uint16(self._data[0x18:0x1A]) & 0xF000) >> 12

    @property
    def field_effect_sprite_id(self) -> int:
        return self._data[0x1A]

    @property
    def warp_arrow_sprite_id(self) -> int:
        return self._data[0x1B]

    @property
    def movement_action(self) -> str:
        return string.capwords(self.MOVEMENT_ACTIONS[self._data[0x1C]].replace("_", " "))

    @property
    def trainer_range_berry_tree_id(self) -> int:
        return self._data[0x1D]

    @property
    def current_metatile_behaviour(self) -> int:
        return self._data[0x1E]

    @property
    def previous_metatile_behaviour(self) -> int:
        return self._data[0x1F]

    @property
    def previous_movement_direction(self) -> int:
        return self._data[0x20]

    @property
    def direction_sequence_index(self) -> int:
        return self._data[0x21]

    @property
    def player_copyable_movement(self) -> int:
        return self._data[0x22]

    def __str__(self) -> str:
        if "isPlayer" in self.flags:
            return "Player"
        elif self.trainer_type == "Buried":
            return f"Buried Trainer at {self.current_coords}"
        elif self.trainer_type != "None":
            return f"Trainer at {self.current_coords}"
        else:
            return f"Entity at {self.current_coords}"


class ObjectEventTemplate:
    def __init__(self, data: bytes):
        self._data = data

    @property
    def local_id(self) -> int:
        return self._data[0]

    @property
    def graphics_id(self) -> int:
        return self._data[1]

    @property
    def kind(self) -> Literal["normal", "clone"]:
        return "clone" if self._data[2] == 255 else "normal"

    @property
    def local_coordinates(self) -> tuple[int, int]:
        return unpack_uint16(self._data[4:6]), unpack_uint16(self._data[6:8])

    @property
    def elevation(self) -> int:
        return self._data[8]

    @property
    def movement_type(self) -> str:
        return ObjectEvent.MOVEMENT_TYPES[self._data[9]]

    @property
    def movement_range(self) -> tuple[int, int]:
        return (self._data[10] & 0xF0) >> 4, self._data[10] & 0x0F

    @property
    def trainer_type(self) -> Literal["None", "Normal", "See All Directions", "Buried", "???"]:
        match unpack_uint16(self._data[12:14]):
            case 0:
                return "None"
            case 1:
                return "Normal"
            case 2:
                return "See All Directions"
            case 3:
                return "Buried"
            case _:
                return "???"

    @property
    def trainer_range(self) -> int:
        return unpack_uint16(self._data[14:16])

    @property
    def berry_tree_id(self) -> int:
        return unpack_uint16(self._data[14:16])

    @property
    def script_pointer(self) -> int:
        return unpack_uint32(self._data[16:20])

    @property
    def script_symbol(self) -> str:
        if self.script_pointer == 0:
            return ""
        symbol = get_symbol_name(self.script_pointer, pretty_name=True)
        return hex(self.script_pointer) if symbol == "" else symbol

    @property
    def flag_id(self) -> int:
        return unpack_uint16(self._data[20:22])

    @property
    def clone_target_local_id(self) -> int:
        """This only has meaning if `kind` is 'clone' on FRLG."""
        return self.elevation

    @property
    def clone_target_map_group(self) -> int:
        """This only has meaning if `kind` is 'clone' on FRLG."""
        return unpack_uint16(self._data[14:16])

    @property
    def clone_target_map_number(self) -> int:
        """This only has meaning if `kind` is 'clone' on FRLG."""
        return unpack_uint16(self._data[12:14])

    @property
    def clone_target_map(self) -> MapLocation:
        """This only has meaning if `kind` is 'clone' on FRLG."""
        return get_map_data((self.clone_target_map_group, self.clone_target_map_number), (0, 0))

    def to_dict(self) -> dict:
        kind = self.kind
        data = {
            "local_id": self.local_id,
            "local_coordinates": self.local_coordinates,
            "kind": kind,
            "script": self.script_symbol,
            "flag": get_event_flag_name(self.flag_id),
        }

        if kind == "normal":
            trainer = None
            if self.trainer_type != "None":
                trainer = {
                    "type": self.trainer_type,
                    "range": self.trainer_range,
                }

            data["elevation"] = self.elevation
            data["trainer"] = trainer
            data["movement"] = {
                "type": self.movement_type,
                "range": self.movement_range,
            }
        else:
            data["target"] = {
                "map_group": self.clone_target_map_group,
                "map_number": self.clone_target_map_number,
                "map_name": self.clone_target_map.map_name,
                "local_id": self.local_id,
            }

        return data

    def __str__(self) -> str:
        if self.trainer_type == "Buried":
            return f"Buried Trainer at {self.local_coordinates}"
        elif self.trainer_type != "None":
            return f"Trainer at {self.local_coordinates}"
        else:
            return f"Entity at {self.local_coordinates}"


def get_map_data_for_current_position() -> MapLocation | None:
    from modules.player import get_player_avatar

    player = get_player_avatar()
    if player is None:
        return None

    map_group, map_number = player.map_group_and_number
    return MapLocation(read_symbol("gMapHeader"), map_group, map_number, player.local_coordinates)


_map_header_cache: dict[tuple[int, int], bytes] = {}


def get_map_data(
    map_group_and_number: "tuple[int, int] | MapFRLG | MapRSE", local_position: tuple[int, int]
) -> MapLocation:
    global _map_header_cache
    if not isinstance(map_group_and_number, tuple):
        map_group_and_number = map_group_and_number.value

    if len(_map_header_cache) == 0:
        from modules.map_data import MapGroupFRLG, MapGroupRSE

        if context.rom.is_rse:
            number_of_map_groups = len(MapGroupRSE)
            map_group_enum = MapGroupRSE
        else:
            number_of_map_groups = len(MapGroupFRLG)
            map_group_enum = MapGroupFRLG
        map_group_pointers = read_symbol("gMapGroups", size=4 * number_of_map_groups)

        for group_index in range(number_of_map_groups):
            number_of_maps = len(map_group_enum(group_index).maps)
            group_pointer = unpack_uint32(map_group_pointers[group_index * 4 : (group_index + 1) * 4])
            for map_index in range(number_of_maps):
                map_header_pointer = unpack_uint32(context.emulator.read_bytes(group_pointer + 4 * map_index, 4))
                map_header = context.emulator.read_bytes(map_header_pointer, 0x1C)
                _map_header_cache[(group_index, map_index)] = map_header

    if map_group_and_number not in _map_header_cache:
        raise ValueError(f"Tried to access invalid map: ({map_group_and_number})")

    return MapLocation(
        _map_header_cache[map_group_and_number], map_group_and_number[0], map_group_and_number[1], local_position
    )


def get_map_objects() -> list[ObjectEvent]:
    data = read_symbol("gObjectEvents", 0, 0x24 * 16)
    objects = []
    for i in range(16):
        offset = i * 0x24
        is_active = bool(data[offset] & 0x01)
        if is_active:
            map_object = ObjectEvent(data[offset : offset + 0x24])
            objects.append(map_object)
    return objects


def get_player_map_object() -> ObjectEvent | None:
    data = read_symbol("gObjectEvents", 0, 0x24)
    if data[0] & 0x01:
        return ObjectEvent(data)
    else:
        return None


def get_map_all_tiles(map_location: MapLocation | None = None) -> list[MapLocation]:
    if map_location is None:
        map_location = get_map_data_for_current_position()
    map_group, map_number = map_location.map_group, map_location.map_number
    map_width, map_height = map_location.map_size
    return [
        get_map_data((map_group, map_number), (x, y)) for y, x in itertools.product(range(map_height), range(map_width))
    ]


@dataclass
class WildEncounter:
    species: Species
    min_level: int
    max_level: int
    encounter_rate: int

    def __str__(self):
        if self.min_level == self.max_level:
            return f"{self.species.name} (lvl. {self.min_level}; {self.encounter_rate}%)"
        else:
            return f"{self.species.name} (lvl. {self.min_level}-{self.max_level}; {self.encounter_rate}%)"


@dataclass
class WildEncounterList:
    land_encounter_rate: int
    surf_encounter_rate: int
    rock_smash_encounter_rate: int
    fishing_encounter_rate: int

    land_encounters: list[WildEncounter]
    surf_encounters: list[WildEncounter]
    rock_smash_encounters: list[WildEncounter]
    old_rod_encounters: list[WildEncounter]
    good_rod_encounters: list[WildEncounter]
    super_rod_encounters: list[WildEncounter]


_wild_encounters_cache: dict[tuple[int, int], WildEncounterList] = {}


def get_wild_encounters_for_map(map_group: int, map_number: int) -> WildEncounterList | None:
    global _wild_encounters_cache
    if len(_wild_encounters_cache) == 0:
        types = (
            (4, 8, "land", 12, (20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1)),
            (8, 12, "surf", 5, (60, 30, 5, 4, 1)),
            (12, 16, "rock_smash", 5, (60, 30, 5, 4, 1)),
            (16, 20, "fishing", 10, (70, 30, 60, 20, 20, 40, 40, 15, 4, 1)),
        )
        headers = read_symbol("gWildMonHeaders")
        for index in range(len(headers) // 20):
            offset = index * 20
            group = headers[offset]
            number = headers[offset + 1]
            if group == 0xFF:
                break

            def get_encounters_list(address: int, length: int, encounter_rates: list[int]) -> list[WildEncounter]:
                if address == 0:
                    return []

                raw_list = context.emulator.read_bytes(address, length=length * 4)
                result = []
                for n in range(length):
                    min_level = raw_list[4 * n]
                    max_level = raw_list[4 * n + 1]
                    if min_level > max_level:
                        max_level, min_level = min_level, max_level
                    species = get_species_by_index(unpack_uint16(raw_list[4 * n + 2 : 4 * n + 4]))
                    result.append(WildEncounter(species, min_level, max_level, encounter_rates[n]))
                return result

            data = {}
            for start, end, key, count, rates in types:
                pointer = unpack_uint32(headers[offset + start : offset + end])
                data[f"{key}_encounter_rate"] = 0
                if key != "fishing":
                    data[f"{key}_encounters"] = []
                else:
                    data["old_rod_encounters"] = []
                    data["good_rod_encounters"] = []
                    data["super_rod_encounters"] = []
                if pointer > 0:
                    encounter_info = context.emulator.read_bytes(pointer, length=8)
                    data[f"{key}_encounter_rate"] = encounter_info[0]
                    if data[f"{key}_encounter_rate"] > 0:
                        list_pointer = unpack_uint32(encounter_info[4:8])
                        if key != "fishing":
                            data[f"{key}_encounters"] = get_encounters_list(list_pointer, count, rates)
                        else:
                            data["old_rod_encounters"] = get_encounters_list(list_pointer, 2, rates[:2])
                            data["good_rod_encounters"] = get_encounters_list(list_pointer + 8, 3, rates[2:5])
                            data["super_rod_encounters"] = get_encounters_list(list_pointer + 20, 5, rates[5:10])
            _wild_encounters_cache[(group, number)] = WildEncounterList(**data)

    return _wild_encounters_cache.get((map_group, map_number))


def calculate_targeted_coords(current_coordinates: tuple[int, int], facing_direction: str) -> tuple[int, int]:
    match facing_direction:
        case "Up":
            return current_coordinates[0], current_coordinates[1] - 1
        case "Down":
            return current_coordinates[0], current_coordinates[1] + 1
        case "Left":
            return current_coordinates[0] - 1, current_coordinates[1]
        case "Right":
            return current_coordinates[0] + 1, current_coordinates[1]
        case _:
            raise ValueError(f"Invalid facing direction: {facing_direction}")
