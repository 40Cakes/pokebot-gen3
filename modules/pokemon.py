import contextlib
import json
import struct
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Literal

import numpy

from modules.game import decode_string
from modules.items import Item, get_item_by_index, get_item_by_move_id, get_item_by_name
from modules.memory import pack_uint32, read_symbol, unpack_uint16, unpack_uint32
from modules.roms import ROMLanguage
from modules.runtime import get_data_path

DATA_DIRECTORY = Path(__file__).parent / "data"

# Some substructures in the data are in a different order each time, depending
# on the Personality Value of the Pokémon. This is a lookup table for that.
# see: https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)#Substructure_order
POKEMON_DATA_SUBSTRUCTS_ORDER = [
    (0, 1, 2, 3),
    (0, 1, 3, 2),
    (0, 2, 1, 3),
    (0, 3, 1, 2),
    (0, 2, 3, 1),
    (0, 3, 2, 1),
    (1, 0, 2, 3),
    (1, 0, 3, 2),
    (2, 0, 1, 3),
    (3, 0, 1, 2),
    (2, 0, 3, 1),
    (3, 0, 2, 1),
    (1, 2, 0, 3),
    (1, 3, 0, 2),
    (2, 1, 0, 3),
    (3, 1, 0, 2),
    (2, 3, 0, 1),
    (3, 2, 0, 1),
    (1, 2, 3, 0),
    (1, 3, 2, 0),
    (2, 1, 3, 0),
    (3, 1, 2, 0),
    (2, 3, 1, 0),
    (3, 2, 1, 0),
]

HIDDEN_POWER_MAP = [
    "Fighting",
    "Flying",
    "Poison",
    "Ground",
    "Rock",
    "Bug",
    "Ghost",
    "Steel",
    "Fire",
    "Water",
    "Grass",
    "Electric",
    "Psychic",
    "Ice",
    "Dragon",
    "Dark",
]

LOCATION_MAP = [
    "Littleroot Town",
    "Oldale Town",
    "Dewford Town",
    "Lavaridge Town",
    "Fallarbor Town",
    "Verdanturf Town",
    "Pacifidlog Town",
    "Petalburg City",
    "Slateport City",
    "Mauville City",
    "Rustboro City",
    "Fortree City",
    "Lilycove City",
    "Mossdeep City",
    "Sootopolis City",
    "Ever Grande City",
    "Route 101",
    "Route 102",
    "Route 103",
    "Route 104",
    "Route 105",
    "Route 106",
    "Route 107",
    "Route 108",
    "Route 109",
    "Route 110",
    "Route 111",
    "Route 112",
    "Route 113",
    "Route 114",
    "Route 115",
    "Route 116",
    "Route 117",
    "Route 118",
    "Route 119",
    "Route 120",
    "Route 121",
    "Route 122",
    "Route 123",
    "Route 124",
    "Route 125",
    "Route 126",
    "Route 127",
    "Route 128",
    "Route 129",
    "Route 130",
    "Route 131",
    "Route 132",
    "Route 133",
    "Route 134",
    "Underwater (Route 124)",
    "Underwater (Route 126)",
    "Underwater (Route 127)",
    "Underwater (Route 128)",
    "Underwater (Sootopolis City)",
    "Granite Cave",
    "Mt. Chimney",
    "Safari Zone",
    "Battle TowerRS/Battle FrontierE",
    "Petalburg Woods",
    "Rusturf Tunnel",
    "Abandoned Ship",
    "New Mauville",
    "Meteor Falls",
    "Meteor Falls (unused)",
    "Mt. Pyre",
    "Hideout* (Magma HideoutR/Aqua HideoutS)",
    "Shoal Cave",
    "Seafloor Cavern",
    "Underwater (Seafloor Cavern)",
    "Victory Road",
    "Mirage Island",
    "Cave of Origin",
    "Southern Island",
    "Fiery Path",
    "Fiery Path (unused)",
    "Jagged Pass",
    "Jagged Pass (unused)",
    "Sealed Chamber",
    "Underwater (Route 134)",
    "Scorched Slab",
    "Island Cave",
    "Desert Ruins",
    "Ancient Tomb",
    "Inside of Truck",
    "Sky Pillar",
    "Secret Base",
    "Ferry",
    "Pallet Town",
    "Viridian City",
    "Pewter City",
    "Cerulean City",
    "Lavender Town",
    "Vermilion City",
    "Celadon City",
    "Fuchsia City",
    "Cinnabar Island",
    "Indigo Plateau",
    "Saffron City",
    "Route 4 (Pokémon Center)",
    "Route 10 (Pokémon Center)",
    "Route 1",
    "Route 2",
    "Route 3",
    "Route 4",
    "Route 5",
    "Route 6",
    "Route 7",
    "Route 8",
    "Route 9",
    "Route 10",
    "Route 11",
    "Route 12",
    "Route 13",
    "Route 14",
    "Route 15",
    "Route 16",
    "Route 17",
    "Route 18",
    "Route 19",
    "Route 20",
    "Route 21",
    "Route 22",
    "Route 23",
    "Route 24",
    "Route 25",
    "Viridian Forest",
    "Mt. Moon",
    "S.S. Anne",
    "Underground Path (Routes 5-6)",
    "Underground Path (Routes 7-8)",
    "Diglett's Cave",
    "Victory Road",
    "Rocket Hideout",
    "Silph Co.",
    "Pokémon Mansion",
    "Safari Zone",
    "Pokémon League",
    "Rock Tunnel",
    "Seafoam Islands",
    "Pokémon Tower",
    "Cerulean Cave",
    "Power Plant",
    "One Island",
    "Two Island",
    "Three Island",
    "Four Island",
    "Five Island",
    "Seven Island",
    "Six Island",
    "Kindle Road",
    "Treasure Beach",
    "Cape Brink",
    "Bond Bridge",
    "Three Isle Port",
    "Sevii Isle 6",
    "Sevii Isle 7",
    "Sevii Isle 8",
    "Sevii Isle 9",
    "Resort Gorgeous",
    "Water Labyrinth",
    "Five Isle Meadow",
    "Memorial Pillar",
    "Outcast Island",
    "Green Path",
    "Water Path",
    "Ruin Valley",
    "Trainer Tower (exterior)",
    "Canyon Entrance",
    "Sevault Canyon",
    "Tanoby Ruins",
    "Sevii Isle 22",
    "Sevii Isle 23",
    "Sevii Isle 24",
    "Navel Rock",
    "Mt. Ember",
    "Berry Forest",
    "Icefall Cave",
    "Rocket Warehouse",
    "Trainer Tower",
    "Dotted Hole",
    "Lost Cave",
    "Pattern Bush",
    "Altering Cave",
    "Tanoby Chambers",
    "Three Isle Path",
    "Tanoby Key",
    "Birth Island",
    "Monean Chamber",
    "Liptoo Chamber",
    "Weepth Chamber",
    "Dilford Chamber",
    "Scufib Chamber",
    "Rixy Chamber",
    "Viapois Chamber",
    "Ember Spa",
    "Special Area",
    "Aqua Hideout",
    "Magma Hideout",
    "Mirage Tower",
    "Birth Island",
    "Faraway Island",
    "Artisan Cave",
    "Marine Cave",
    "Underwater (Marine Cave)",
    "Terra Cave",
    "Underwater (Route 105)",
    "Underwater (Route 125)",
    "Underwater (Route 129)",
    "Desert Underpass",
    "Altering Cave",
    "Navel Rock",
    "Trainer Hill",
    *["?" for n in range(40)],
    "Gift Egg",
    "In-game Trade",
    "Fateful Encounter",
]


class Type:
    """
    This represents an elemental type such as Fight, Electric, etc.
    """

    def __init__(self, index: int, name: str):
        self.index: int = index
        self.name: str = name
        self._effectiveness: dict["Type", float] = {}

    def set_effectiveness(self, other_type: "Type", effectiveness: float):
        self._effectiveness[other_type] = effectiveness

    def get_effectiveness_against(self, other_type: "Type") -> float:
        return self._effectiveness.get(other_type, 1)

    @property
    def is_physical(self) -> bool:
        return self.index < 9

    @property
    def is_special(self) -> bool:
        return self.index >= 9

    @property
    def kind(self) -> str:
        return "Physical" if self.is_physical else "Special"

    @property
    def safe_name(self) -> str:
        return "Unknown" if self.name == "???" else self.name

    def __str__(self):
        return self.name


@dataclass
class Move:
    """
    This represents a battle move, but not the connection to any particular Pokémon.
    Think of it as the 'move species'.
    """

    index: int
    name: str
    description: str
    type: Type
    accuracy: float
    # This is the accuracy for a secondary effect, such as optional
    # status changes etc.
    secondary_accuracy: float
    pp: int
    priority: int
    base_power: int
    effect: str
    target: str
    makes_contact: bool
    is_sound_move: bool
    affected_by_protect: bool
    affected_by_magic_coat: bool
    affected_by_snatch: bool
    usable_with_mirror_move: bool
    affected_by_kings_rock: bool
    tm_hm: Item | None

    def __str__(self):
        return self.name

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Move":
        return Move(
            index=index,
            name=data["name"],
            description=data["localised_descriptions"]["E"],
            type=get_type_by_name(data["type"]),
            accuracy=float(data["accuracy"]),
            secondary_accuracy=float(data["secondary_accuracy"]),
            pp=data["pp"],
            priority=data["priority"],
            base_power=data["base_power"],
            effect=data["effect"],
            target=data["target"],
            makes_contact=data["makes_contact"],
            is_sound_move=data["is_sound_move"],
            affected_by_protect=data["affected_by_protect"],
            affected_by_magic_coat=data["affected_by_magic_coat"],
            affected_by_snatch=data["affected_by_snatch"],
            usable_with_mirror_move=data["usable_with_mirror_move"],
            affected_by_kings_rock=data["affected_by_kings_rock"],
            tm_hm=get_item_by_name(data["tm_hm"]) if data["tm_hm"] is not None else None,
        )


@dataclass
class LearnedMove:
    """
    This represents a move slot for an individual Pokémon.
    """

    move: Move
    total_pp: int
    pp: int
    pp_ups: int

    def added_pps(self) -> int:
        return self.total_pp - self.move.pp

    def __str__(self):
        return f"{self.move.name} ({self.pp} / {self.total_pp})"


@dataclass
class StatsValues:
    """
    A collection class for all 6 stats; can be used as a convenience thing wherever a list of
    stats is required (IVs, EVs, Pokémon stats, EV yields, ...)
    """

    hp: int
    attack: int
    defence: int
    speed: int
    special_attack: int
    special_defence: int

    @classmethod
    def from_dict(cls, data: dict) -> "StatsValues":
        return StatsValues(
            data.get("hp", 0),
            data.get("attack", 0),
            data.get("defence", 0),
            data.get("speed", 0),
            data.get("special_attack", 0),
            data.get("special_defence", 0),
        )

    def __getitem__(self, item):
        return self.__getattribute__(item)

    @classmethod
    def calculate(
        cls, species: "Species", ivs: "StatsValues", evs: "StatsValues", nature: "Nature", level: int
    ) -> "StatsValues":
        """
        Re-calculates the current effective stats of a Pokémon. This is needed for boxed
        Pokémon, that do not store their current stats anywhere.
        :param species:
        :param ivs:
        :param evs:
        :param nature:
        :param level:
        :return: The calculated set of battle stats for the Pokémon
        """
        if species.national_dex_number == 292:
            # Shedinja always has 1 HP
            hp = 1
        else:
            hp = ((2 * species.base_stats.hp + ivs.hp + (evs.hp // 4)) * level) // 100 + 10 + level

        stats = {
            i: (((2 * species.base_stats[i] + ivs[i] + (evs[i] // 4)) * level) // 100 + 5) * nature.modifiers[i]
            for i in [
                "attack",
                "defence",
                "speed",
                "special_attack",
                "special_defence",
            ]
        }
        return cls(
            hp=int(hp),
            attack=int(stats["attack"]),
            defence=int(stats["defence"]),
            speed=int(stats["speed"]),
            special_attack=int(stats["special_attack"]),
            special_defence=int(stats["special_defence"]),
        )

    def sum(self) -> int:
        return self.hp + self.attack + self.defence + self.speed + self.special_attack + self.special_defence


@dataclass
class ContestConditions:
    """
    Represents the stats that are being used in the Pokémon Contest, equivalent to `StatsValues`.
    """

    coolness: int
    beauty: int
    cuteness: int
    smartness: int
    toughness: int
    feel: int


@dataclass
class HeldItem:
    """
    Represents a possible held item for a Pokémon encounter, along with the probability of it
    being held.
    """

    item: Item
    probability: float


@dataclass
class Nature:
    """
    Represents a Pokémon nature and its stats modifiers.
    """

    index: int
    name: str
    modifiers: dict[str, float]

    def __str__(self):
        return self.name

    @property
    def name_with_modifiers(self) -> str:
        increased_stat = None
        decreased_stat = None
        for stat in self.modifiers:
            if self.modifiers[stat] > 1:
                increased_stat = stat
            elif self.modifiers[stat] < 1:
                decreased_stat = stat

        if increased_stat is None or decreased_stat is None or increased_stat == decreased_stat:
            return f"{self.name} (neutral)"

        stat_name_map = {
            "attack": "Atk",
            "defence": "Def",
            "speed": "Speed",
            "special_attack": "SpAtk",
            "special_defence": "SpDef",
        }
        return f"{self.name} (+{stat_name_map[increased_stat]}, -{stat_name_map[decreased_stat]})"

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Nature":
        return Nature(
            index=index,
            name=data["name"],
            modifiers={
                "attack": data["attack_modifier"],
                "defence": data["defence_modifier"],
                "speed": data["speed_modifier"],
                "special_attack": data["special_attack_modifier"],
                "special_defence": data["special_defence_modifier"],
            },
        )


@dataclass
class Ability:
    index: int
    name: str

    def __str__(self):
        return self.name

    @classmethod
    def from_dict(cls, index: int, data: dict) -> "Ability":
        return Ability(index=index, name=data["name"])


class LevelUpType(Enum):
    MediumFast = "Medium Fast"
    Erratic = "Erratic"
    Fluctuating = "Fluctuating"
    MediumSlow = "Medium Slow"
    Fast = "Fast"
    Slow = "Slow"

    def get_experience_needed_for_level(self, level: int) -> int:
        """
        Calculates how much total experience is needed to reach a given level. The formulas here
        are taken straight from the decompliation project.
        :param level: The level to check for
        :return: The number of EXP required to reach that level
        """
        if level == 0:
            return 0
        elif level == 1:
            return 1
        elif self == LevelUpType.MediumSlow:
            return ((6 * (level**3)) // 5) - (15 * (level**2)) + (100 * level) - 140
        elif self == LevelUpType.Erratic:
            if level <= 50:
                return (100 - level) * (level**3) // 50
            elif level <= 68:
                return (150 - level) * (level**3) // 100
            elif level <= 98:
                return ((1911 - 10 * level) // 3) * (level**3) // 500
            else:
                return (160 - level) * (level**3) // 100
        elif self == LevelUpType.Fluctuating:
            if level <= 15:
                return ((level + 1) // 3 + 24) * (level**3) // 50
            elif level <= 36:
                return (level + 14) * (level**3) // 50
            else:
                return ((level // 2) + 32) * (level**3) // 50
        elif self == LevelUpType.MediumFast:
            return level**3
        elif self == LevelUpType.Slow:
            return (5 * (level**3)) // 4
        elif self == LevelUpType.Fast:
            return (4 * (level**3)) // 5

    def get_level_from_total_experience(self, total_experience: int) -> int:
        """
        Calculates which level a Pokémon should be, given a number of total EXP.
        This is required for box Pokémon, that do not actually store their level.
        :param total_experience: Total number of experience points
        :return: The level a Pokémon would have with that amount of EXP
        """
        level = 0
        while total_experience >= self.get_experience_needed_for_level(level + 1):
            level += 1
        return level


@dataclass
class SpeciesLevelUpMove:
    level: int
    move: Move

    def __str__(self):
        return f"{self.move.name} at Lv. {self.level}"


@dataclass
class SpeciesTmHmMove:
    item: Item
    move: Move

    def __str__(self):
        return f"{self.item.name} ({self.move.name})"

    def debug_dict_value(self):
        return {
            "item": self.item.name,
            "move": self.move.name,
        }


@dataclass
class SpeciesMoveLearnset:
    level_up: list[SpeciesLevelUpMove]
    tm_hm: list[SpeciesTmHmMove]
    tutor: list[Move]
    egg: list[Move]

    def debug_dict_value(self):
        return {
            "level_up": [f"{entry.move.name} at Lv. {entry.level}" for entry in self.level_up],
            "tm_hm": [f"{entry.item.name} ({entry.move.name})" for entry in self.tm_hm],
            "tutor": [entry.name for entry in self.tutor],
            "egg": [entry.name for entry in self.egg],
        }

    @classmethod
    def from_dict(cls, data: dict):
        return SpeciesMoveLearnset(
            level_up=[
                SpeciesLevelUpMove(level=data["level_up"][move_id], move=get_move_by_index(int(move_id)))
                for move_id in data["level_up"]
            ],
            tm_hm=[
                SpeciesTmHmMove(item=get_item_by_move_id(move_id), move=get_move_by_index(move_id))
                for move_id in data["tm_hm"]
            ],
            tutor=[get_move_by_index(move_id) for move_id in data["tutor"]],
            egg=[get_move_by_index(move_id) for move_id in data["egg"]],
        )


@dataclass
class Species:
    index: int
    national_dex_number: int
    hoenn_dex_number: int
    name: str
    types: list[Type]
    abilities: list[Ability]
    held_items: list[HeldItem]
    base_stats: StatsValues
    gender_ratio: int
    egg_cycles: int
    base_friendship: int
    catch_rate: int
    safari_zone_flee_probability: int
    level_up_type: LevelUpType
    egg_groups: list[str]
    base_experience_yield: int
    ev_yield: StatsValues
    learnset: SpeciesMoveLearnset
    localised_names: dict[str, str]

    def has_type(self, type_to_find: Type) -> bool:
        return any(t.index == type_to_find.index for t in self.types)

    def can_learn_tm_hm(self, tm_hm: Item | Move):
        if isinstance(tm_hm, Move):
            tm_hm = tm_hm.tm_hm

        for entry in self.learnset.tm_hm:
            if entry.item == tm_hm:
                return True

        return False

    def to_dict(self) -> dict:
        return _to_dict_helper(self)

    def __str__(self):
        return self.name

    @classmethod
    def from_dict(cls, index: int, data: dict):
        return Species(
            index=index,
            national_dex_number=data["national_dex_number"],
            hoenn_dex_number=data["hoenn_dex_number"],
            name=data["name"],
            types=list(map(get_type_by_name, data["types"])),
            abilities=list(map(get_ability_by_name, data["abilities"])),
            held_items=list(map(lambda e: HeldItem(e[0], e[1]), data["held_items"])),
            base_stats=StatsValues.from_dict(data["base_stats"]),
            gender_ratio=data["gender_ratio"],
            egg_cycles=data["egg_cycles"],
            base_friendship=data["base_friendship"],
            catch_rate=data["catch_rate"],
            safari_zone_flee_probability=data["safari_zone_flee_probability"],
            level_up_type=LevelUpType(data["level_up_type"]),
            egg_groups=data["egg_groups"],
            base_experience_yield=data["base_experience_yield"],
            ev_yield=StatsValues.from_dict(data["ev_yield"]),
            learnset=SpeciesMoveLearnset.from_dict(data["learnset"]),
            localised_names=data["localised_names"],
        )


@dataclass
class OriginalTrainer:
    id: int
    secret_id: int
    name: str
    gender: Literal["male", "female"]


class Marking(Enum):
    Circle = "●"
    Square = "■"
    Triangle = "▲"
    Heart = "♥"

    def __str__(self):
        return self.value

    @classmethod
    def from_bitfield(cls, bitfield) -> list["Marking"]:
        markings = []
        if bitfield & 0b0001:
            markings.append(Marking.Circle)
        if bitfield & 0b0010:
            markings.append(Marking.Square)
        if bitfield & 0b0100:
            markings.append(Marking.Triangle)
        if bitfield & 0b1000:
            markings.append(Marking.Heart)
        return markings


class StatusCondition(Enum):
    Healthy = "none"
    Sleep = "asleep"
    Poison = "poisoned"
    Burn = "burned"
    Freeze = "frozen"
    Paralysis = "paralysed"
    BadPoison = "badly poisoned"

    @classmethod
    def from_bitfield(cls, bitfield: int) -> "StatusCondition":
        condition = StatusCondition.Healthy
        if bitfield & 0b1000_0000:
            condition = StatusCondition.BadPoison
        elif bitfield & 0b0100_0000:
            condition = StatusCondition.Paralysis
        elif bitfield & 0b0010_0000:
            condition = StatusCondition.Freeze
        elif bitfield & 0b0001_0000:
            condition = StatusCondition.Burn
        elif bitfield & 0b0000_1000:
            condition = StatusCondition.Poison
        elif bitfield & 0b0000_0111:
            condition = StatusCondition.Sleep
        return condition

    def to_bitfield(self) -> int:
        match self:
            case StatusCondition.Healthy:
                return 0
            case StatusCondition.Sleep:
                return 0b0000_0111
            case StatusCondition.Poison:
                return 0b0000_1000
            case StatusCondition.Burn:
                return 0b0001_0000
            case StatusCondition.Freeze:
                return 0b0010_0000
            case StatusCondition.Paralysis:
                return 0b0100_0000
            case StatusCondition.BadPoison:
                return 0b1000_0000


@dataclass
class PokerusStatus:
    strain: int
    days_remaining: int


class Pokemon:
    """
    Represents an individual Pokémon.

    The only real data in here is the `self.data` property, which contains the 100-byte (party Pokémon)
    or 80-byte (box Pokémon) string of data that everything else can be computed from.

    So serialising or copying a Pokémon only requires to store/copy this property and nothing else.
    The class will calculate everything else on-the-fly.
    """

    def __init__(self, data: bytes):
        self.data = data

    def __eq__(self, other):
        if isinstance(other, Pokemon):
            return other.data == self.data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Pokemon):
            return other.data != self.data
        else:
            return NotImplemented

    @cached_property
    def _decrypted_data(self) -> bytes:
        """
        Returns the decrypted Pokémon data and also puts the substructures in a consistent order.

        For more information regarding encryption and substructure ordering, see:
        https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)#Format

        This is a `cached_property`, so it only runs once regardless of how many times it is called.

        It puts the substructures in the same order as they are listed on Bulbapedia, to make working
        with offsets a bit easier.

        :return: The decrypted and re-ordered data for this Pokémon.
        """
        order = POKEMON_DATA_SUBSTRUCTS_ORDER[self.personality_value % 24]
        u32le = numpy.dtype("<u4")

        personality_value = numpy.frombuffer(self.data, count=1, dtype=u32le)
        original_trainer_id = numpy.frombuffer(self.data, count=1, offset=4, dtype=u32le)
        key = numpy.repeat(personality_value ^ original_trainer_id, 3)

        decrypted = numpy.concatenate(
            [numpy.frombuffer(self.data, count=3, offset=32 + (order[i] * 12), dtype=u32le) ^ key for i in range(4)]
        )
        return self.data[:32] + decrypted.tobytes() + self.data[80:100]

    @property
    def _foo_data(self) -> str:
        return self._decrypted_data[32:80].hex(" ", 12)

    @property
    def _character_set(self) -> Literal["international", "japanese"]:
        """
        Figures out which character set needs to be used for decoding nickname and
        original trainer name of this Pokémon.
        :return: The character table name as supported by `DecodeString()`
        """
        return "japanese" if self.language == ROMLanguage.Japanese else "international"

    def calculate_checksum(self) -> int:
        words = struct.unpack("<24H", self._decrypted_data[32:80])
        return sum(words) & 0xFFFF

    def get_data_checksum(self) -> int:
        return unpack_uint16(self.data[28:30])

    @property
    def is_valid(self) -> bool:
        return self.get_data_checksum() == self.calculate_checksum()

    @property
    def is_empty(self) -> bool:
        """
        Since many places in memory _might_ contain a Pokémon but also might not (all zeros or something),
        this checks whether a given block of data is actually a Pokémon the same way the game does.
        :return: Whether the data represents a Pokémon or is just an empty slot.
        """
        return self.data[19] & 0x02 == 0

    # ==========================================
    # Unencrypted values (offsets 0 through 32)
    # ==========================================

    @property
    def personality_value(self) -> int:
        return unpack_uint32(self.data[:4])

    @property
    def original_trainer(self) -> OriginalTrainer:
        origin_data = unpack_uint16(self._decrypted_data[70:72])
        gender = "female" if origin_data & 0xF000 else "male"
        return OriginalTrainer(
            id=unpack_uint16(self.data[4:6]),
            secret_id=unpack_uint16(self.data[6:8]),
            name=decode_string(self.data[20:27], character_set=self._character_set),
            gender=gender,
        )

    @property
    def nickname(self) -> str:
        return decode_string(self.data[8:18], character_set=self._character_set)

    @property
    def name(self) -> str:
        if self.is_egg:
            return "EGG"
        return nickname if (nickname := self.nickname) else self.species.name.upper()

    @property
    def language(self) -> ROMLanguage | None:
        if self.data[18] == 1:
            return ROMLanguage.Japanese
        elif self.data[18] == 2:
            return ROMLanguage.English
        elif self.data[18] == 3:
            return ROMLanguage.French
        elif self.data[18] == 4:
            return ROMLanguage.Italian
        elif self.data[18] == 5:
            return ROMLanguage.German
        elif self.data[18] == 7:
            return ROMLanguage.Spanish
        else:
            return None

    @property
    def is_egg(self) -> bool:
        packed_data = unpack_uint32(self._decrypted_data[72:76])
        return self.data[19] & 0b0100 != 0 or (packed_data >> 30) & 1 != 0

    @property
    def markings(self) -> list[Marking]:
        return Marking.from_bitfield(self.data[27])

    # ==================================
    # Encrypted values from subsections
    # ==================================

    @property
    def species(self) -> Species:
        species_id = unpack_uint16(self._decrypted_data[32:34])
        return get_species_by_index(species_id)

    @property
    def held_item(self) -> Item | None:
        item_index = unpack_uint16(self._decrypted_data[34:36])
        return None if item_index == 0 else get_item_by_index(item_index)

    @property
    def total_exp(self) -> int:
        return unpack_uint32(self._decrypted_data[36:40])

    @property
    def friendship(self) -> int:
        return self._decrypted_data[41]

    def move(self, index: Literal[0, 1, 2, 3]) -> LearnedMove | None:
        offset = 44 + index * 2
        move_index = unpack_uint16(self._decrypted_data[offset : offset + 2])
        if move_index == 0:
            return None
        move = get_move_by_index(move_index)
        pp_bonuses = (self._decrypted_data[40] >> (2 * index)) & 0b11
        total_pp = move.pp + ((move.pp * 20 * pp_bonuses) // 100)
        pp = self._decrypted_data[52 + index]
        return LearnedMove(move=move, total_pp=total_pp, pp=pp, pp_ups=pp_bonuses)

    @property
    def moves(self) -> tuple[LearnedMove | None, LearnedMove | None, LearnedMove | None, LearnedMove | None]:
        return self.move(0), self.move(1), self.move(2), self.move(3)

    def knows_move(self, move: str | Move, with_pp_remaining: bool = False):
        if isinstance(move, Move):
            move = move.name
        for learned_move in self.moves:
            if (
                learned_move is not None
                and learned_move.move.name == move
                and (not with_pp_remaining or learned_move.pp > 0)
            ):
                return True
        return False

    @property
    def evs(self) -> StatsValues:
        return StatsValues(
            hp=self._decrypted_data[56],
            attack=self._decrypted_data[57],
            defence=self._decrypted_data[58],
            speed=self._decrypted_data[59],
            special_attack=self._decrypted_data[60],
            special_defence=self._decrypted_data[61],
        )

    @property
    def ivs(self) -> StatsValues:
        packed_data = unpack_uint32(self._decrypted_data[72:76])
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
            coolness=self._decrypted_data[62],
            beauty=self._decrypted_data[63],
            cuteness=self._decrypted_data[64],
            smartness=self._decrypted_data[65],
            toughness=self._decrypted_data[66],
            feel=self._decrypted_data[67],
        )

    @property
    def pokerus_status(self) -> PokerusStatus:
        return PokerusStatus(strain=self._decrypted_data[68] >> 4, days_remaining=self._decrypted_data[68] & 0b0111)

    @property
    def ability(self) -> Ability:
        packed_data = unpack_uint32(self._decrypted_data[72:76])
        if packed_data & (1 << 31) and len(self.species.abilities) > 1:
            return self.species.abilities[1]
        else:
            return self.species.abilities[0]

    @property
    def poke_ball(self) -> Item:
        origin_data = unpack_uint16(self._decrypted_data[70:72])
        item_index = (origin_data & 0b0111_1000_0000_0000) >> 11
        return get_item_by_index(item_index)

    @property
    def game_of_origin(self) -> str:
        origin_data = unpack_uint16(self._decrypted_data[70:72])
        game_id = (origin_data & 0b0000_0111_1000_0000) >> 7
        if game_id == 1:
            return "Sapphire"
        elif game_id == 2:
            return "Ruby"
        elif game_id == 3:
            return "Emerald"
        elif game_id == 4:
            return "FireRed"
        elif game_id == 5:
            return "LeafGreen"
        elif game_id == 15:
            return "Colosseum/XD"
        else:
            return "?"

    @property
    def level_met(self):
        return unpack_uint16(self._decrypted_data[70:72]) & 0b0111_1111

    @property
    def location_met(self):
        location_index = self._decrypted_data[69]
        if location_index < len(LOCATION_MAP):
            return LOCATION_MAP[location_index]
        else:
            return "Traded"

    # ================================================
    # Values that are only available for team Pokémon
    # and not for boxed Pokémon
    # ================================================

    @property
    def level(self) -> int:
        # This property is not available for boxed Pokémon, but can be re-calculated
        if len(self.data) <= 80:
            return self.species.level_up_type.get_level_from_total_experience(self.total_exp)
        return self.data[84]

    @property
    def exp_needed_until_next_level(self) -> int:
        if self.level >= 100:
            return 0
        total_exp_for_next_level = self.species.level_up_type.get_experience_needed_for_level(self.level + 1)
        return total_exp_for_next_level - self.total_exp

    @property
    def exp_fraction_to_next_level(self) -> float:
        if self.level >= 100:
            return 1
        total_exp_for_this_level = self.species.level_up_type.get_experience_needed_for_level(self.level)
        total_exp_for_next_level = self.species.level_up_type.get_experience_needed_for_level(self.level + 1)
        return (self.total_exp - total_exp_for_this_level) / (total_exp_for_next_level - total_exp_for_this_level)

    @property
    def sleep_duration(self) -> int:
        """Returns the remaining turns on the sleep condition."""
        return self.data[80] & 0b0111 if len(self.data) > 80 else 0

    @property
    def status_condition(self) -> StatusCondition:
        """Returns the StatusCondition of a pokémon."""
        return StatusCondition.from_bitfield(self.data[80]) if len(self.data) > 80 else StatusCondition.Healthy

    @property
    def stats(self) -> StatsValues:
        # This property is not available for boxed Pokémon, but can be re-calculated
        if len(self.data) <= 80:
            return StatsValues.calculate(self.species, self.ivs, self.evs, self.nature, self.level)
        else:
            return StatsValues(
                hp=unpack_uint16(self.data[88:90]),
                attack=unpack_uint16(self.data[90:92]),
                defence=unpack_uint16(self.data[92:94]),
                speed=unpack_uint16(self.data[94:96]),
                special_attack=unpack_uint16(self.data[96:98]),
                special_defence=unpack_uint16(self.data[98:100]),
            )

    @property
    def total_hp(self) -> int:
        return self.stats.hp

    @property
    def current_hp(self) -> int:
        if len(self.data) <= 80:
            return self.stats.hp
        else:
            return unpack_uint16(self.data[86:88])

    @property
    def current_hp_percentage(self) -> float:
        if self.total_hp == 0:
            return 0
        return 100 * self.current_hp / self.total_hp

    # ===================================================
    # Values that are derived from the Personality Value
    # ===================================================

    @property
    def nature(self) -> Nature:
        return get_nature_by_index(self.personality_value % 25)

    @property
    def gender(self) -> Literal["male", "female", None]:
        ratio = self.species.gender_ratio
        if ratio == 0:
            return "male"

        elif ratio == 254:
            return "female"
        elif ratio == 255:
            return None
        value = self.personality_value & 0xFF
        return "male" if value >= ratio else "female"

    @property
    def shiny_value(self) -> int:
        ot = self.original_trainer
        return ot.id ^ ot.secret_id ^ unpack_uint16(self.data[:2]) ^ unpack_uint16(self.data[2:4])

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
        return (value * 40) // 63 + 30

    @property
    def unown_letter(self) -> str:
        letter_index = (
            ((self.personality_value & (0b11 << 24)) >> 18)
            | ((self.personality_value & (0b11 << 16)) >> 12)
            | ((self.personality_value & (0b11 << 8)) >> 6)
            | self.personality_value & 0b11
        )
        return get_unown_letter_by_index(letter_index)

    @property
    def wurmple_evolution(self) -> Literal["silcoon", "cascoon"]:
        value = unpack_uint16(self.data[2:4]) % 10
        return "silcoon" if value <= 4 else "cascoon"

    @property
    def species_name_for_stats(self) -> str:
        if self.species.name == "Unown":
            return f"{self.species.name} ({self.unown_letter})"
        else:
            return self.species.name

    # ==============
    # Debug helpers
    # ==============

    def __str__(self):
        if self.is_empty:
            return "N/A"
        elif not self.is_valid:
            return "Invalid"
        elif self.is_egg:
            return f"Egg ({self.species.name})"
        else:
            gender = self.gender
            if self.species.name == "Unown":
                return f"{self.species.name} {self.unown_letter} (lvl. {self.level})"
            elif gender is not None:
                return f"{self.species.name} (lvl. {self.level}, {gender})"
            else:
                return f"{self.species.name} (lvl. {self.level})"

    def to_dict(self) -> dict:
        return _to_dict_helper(self)


def parse_pokemon(data: bytes) -> Pokemon | None:
    pokemon = Pokemon(data)
    return pokemon if not pokemon.is_empty and pokemon.is_valid else None


def get_unown_letter_by_index(letter_index: int) -> str:
    letter_index %= 28
    if letter_index == 26:
        return "!"
    elif letter_index == 27:
        return "?"
    else:
        return chr(65 + letter_index)


def get_unown_index_by_letter(letter: str) -> int:
    if letter == "!":
        return 26
    elif letter == "?":
        return 27
    else:
        return ord(letter) - 65


def _load_types() -> tuple[dict[str, Type], list[Type]]:
    by_name: dict[str, Type] = {}
    by_index: list[Type] = []
    with open(get_data_path() / "types.json", "r") as file:
        types_data = json.load(file)
        for index in range(len(types_data)):
            name = types_data[index]["name"]
            new_type = Type(index, name)
            by_name[name] = new_type
            by_index.append(new_type)

        for entry in types_data:
            for key in entry["effectiveness"]:
                by_name[entry["name"]].set_effectiveness(by_name[key], entry["effectiveness"][key])
    return by_name, by_index


_types_by_name, _types_by_index = _load_types()


def get_type_by_name(name: str) -> Type:
    return _types_by_name[name]


def get_type_by_index(index: int) -> Type:
    return _types_by_index[index]


def _load_moves() -> tuple[dict[str, Move], list[Move]]:
    by_name: dict[str, Move] = {}
    by_index: list[Move] = []
    with open(get_data_path() / "moves.json", "r") as file:
        moves_data = json.load(file)
        for index in range(len(moves_data)):
            move = Move.from_dict(index, moves_data[index])
            by_name[move.name] = move
            by_index.append(move)
    return by_name, by_index


_moves_by_name, _moves_by_index = _load_moves()


def get_move_by_name(name: str) -> Move:
    return _moves_by_name[name]


def get_move_by_index(index: int) -> Move:
    return _moves_by_index[index]


def _load_natures() -> tuple[dict[str, Nature], list[Nature]]:
    by_name: dict[str, Nature] = {}
    by_index: list[Nature] = []
    with open(get_data_path() / "natures.json", "r") as file:
        natures_data = json.load(file)
        for index in range(len(natures_data)):
            nature = Nature.from_dict(index, natures_data[index])
            by_name[nature.name] = nature
            by_index.append(nature)
    return by_name, by_index


_natures_by_name, _natures_by_index = _load_natures()


def get_nature_by_name(name: str) -> Nature:
    return _natures_by_name[name]


def get_nature_by_index(index: int) -> Nature:
    return _natures_by_index[index]


def _load_abilities() -> tuple[dict[str, Ability], list[Ability]]:
    by_name: dict[str, Ability] = {}
    by_index: list[Ability] = []
    with open(get_data_path() / "abilities.json", "r") as file:
        abilities_data = json.load(file)
        for index in range(len(abilities_data)):
            ability = Ability.from_dict(index, abilities_data[index])
            by_name[ability.name] = ability
            by_index.append(ability)
    return by_name, by_index


_abilities_by_name, _abilities_by_index = _load_abilities()


def get_ability_by_name(name: str) -> Ability:
    return _abilities_by_name[name]


def get_ability_by_index(index: int) -> Ability:
    return _abilities_by_index[index]


def _load_species() -> tuple[dict[str, Species], list[Species], dict[int, Species]]:
    by_name: dict[str, Species] = {}
    by_index: list[Species] = []
    by_national_dex: dict[int, Species] = {}
    with open(get_data_path() / "species.json", "r") as file:
        species_data = json.load(file)
        for index in range(len(species_data)):
            species = Species.from_dict(index, species_data[index])
            by_name[species.name] = species
            by_index.append(species)
            by_national_dex[species.national_dex_number] = species
    return by_name, by_index, by_national_dex


_species_by_name, _species_by_index, _species_by_national_dex = _load_species()


def get_species_by_name(name: str) -> Species:
    if name.startswith("Unown ("):
        name = "Unown"

    return _species_by_name[name]


def get_species_by_index(index: int) -> Species:
    # We use species IDs 20100+ for differentiating between Unown forms, so any
    # such ID should be mapped back to the Unown species.
    if index >= 20100 and index < 20200:
        index = 201

    return _species_by_index[index]


def get_species_by_national_dex(national_dex_number: int) -> Species:
    return _species_by_national_dex[national_dex_number]


def get_opponent() -> Pokemon | None:
    """
    :return: The first Pokémon of the opponent's party, or None if there is no active opponent.
    """
    from modules.pokemon_party import get_opponent_party

    opponent_party = get_opponent_party()
    if opponent_party is None:
        return None
    else:
        return opponent_party[0]


last_opid = pack_uint32(0)  # ReadSymbol('gEnemyParty', size=4)


def clear_opponent() -> None:
    global last_opid
    last_opid = pack_uint32(0)


def opponent_changed() -> bool:
    """
    Checks if the current opponent/encounter from `gEnemyParty` has changed since the function was last called.
    Very fast way to check as this only reads the first 4 bytes (PID) and does not decode the Pokémon data.

    :return: True if opponent changed, otherwise False (bool)
    """
    try:
        global last_opid
        opponent_pid = read_symbol("gEnemyParty", size=4)
        battle_type = unpack_uint32(read_symbol("gBattleTypeFlags", size=0x04))
        trainer_or_tutorial = (1 << 3) | (1 << 9)
        if opponent_pid != last_opid and opponent_pid != b"\x00\x00\x00\x00" and battle_type & trainer_or_tutorial:
            last_opid = opponent_pid
            return True
        else:
            return False
    except SystemExit:
        raise
    except Exception:
        return False


def _to_dict_helper(value) -> any:
    if value is None:
        return value

    debug_dict_callback = getattr(value, "debug_dict_value", None)
    if callable(debug_dict_callback):
        return _to_dict_helper(debug_dict_callback())

    if type(value) is dict:
        return {k: _to_dict_helper(value[k]) for k in value}
    if isinstance(value, (list, set, tuple, frozenset)):
        return [_to_dict_helper(v) for v in value]
    if isinstance(value, (bool, int, float, str)):
        return value

    if isinstance(value, Enum):
        return value.name

    result = {}
    with contextlib.suppress(AttributeError):
        for k in value.__dict__:
            if not k.startswith("_") and k != "data":
                result[k] = _to_dict_helper(value.__dict__[k])
    if hasattr(value, "__class__"):
        for k in dir(value.__class__):
            if not k.startswith("_") and isinstance(getattr(value.__class__, k), property):
                result[k] = _to_dict_helper(getattr(value, k))

    return result
