from dataclasses import dataclass
from enum import IntEnum
from typing import Union

from modules.Memory import GetSaveBlock, unpack_uint32
from modules.Pokemon import Pokemon, parse_pokemon


class DaycareCompatibility(IntEnum):
    Incompatible = 0
    Low = 20
    Medium = 50
    High = 70

    @classmethod
    def CalculateFor(
        cls, pokemon1: Union[Pokemon, None], pokemon2: Union[Pokemon, None]
    ) -> tuple["DaycareCompatibility", str]:
        if pokemon1 is None or pokemon1.is_empty or pokemon2 is None or pokemon2.is_empty:
            return DaycareCompatibility.Incompatible, "Less than two Pokémon in daycare"

        egg_groups1 = pokemon1.species.egg_groups
        egg_groups2 = pokemon2.species.egg_groups

        # The 'undiscovered' egg group cannot be bred.
        if egg_groups1[0] == "no-eggs" or egg_groups2[0] == "no-eggs":
            return DaycareCompatibility.Incompatible, 'At least one of the Pokémon is in the "Undiscovered" egg group'

        # Breeding with Ditto is special.
        if egg_groups1[0] == "Ditto" or egg_groups2[0] == "Ditto":
            if egg_groups1[0] == egg_groups2[0]:
                return DaycareCompatibility.Incompatible, "Two Ditto cannot be bred"
            elif pokemon1.original_trainer.id == pokemon2.original_trainer.id:
                return DaycareCompatibility.Low, "Breeding with Ditto, same OT"
            else:
                return DaycareCompatibility.Medium, "Breeding with Ditto, different OT"

        gender1 = pokemon1.gender
        gender2 = pokemon2.gender

        # Basic biology.
        if gender1 is None or gender2 is None:
            return DaycareCompatibility.Incompatible, "At least one of the Pokémon is genderless"

        if gender1 == gender2:
            return DaycareCompatibility.Incompatible, "Pokémon have the same gender"

        # Check for overlapping egg groups.
        if len(set(egg_groups1) & set(egg_groups2)) == 0:
            return DaycareCompatibility.Incompatible, "No overlapping egg groups"

        if pokemon1.species == pokemon2.species:
            if pokemon1.original_trainer.id == pokemon2.original_trainer.id:
                return DaycareCompatibility.Medium, "Same species, same OT"
            else:
                return DaycareCompatibility.High, "Same species, different OT"
        else:
            if pokemon1.original_trainer.id == pokemon2.original_trainer.id:
                return DaycareCompatibility.Low, "Different species, same OT"
            else:
                return DaycareCompatibility.Medium, "Different species, different OT"


@dataclass
class DaycareData:
    pokemon1: Pokemon
    pokemon1_egg_groups: list[str]
    pokemon1_steps: int
    pokemon2: Pokemon
    pokemon2_egg_groups: list[str]
    pokemon2_steps: int

    offspring_personality: int
    step_counter: int
    compatibility: tuple[DaycareCompatibility, str]


def GetDaycareData() -> Union[DaycareData, None]:
    data = GetSaveBlock(1, 0x3030, 0x120)
    if data is None:
        return None

    pokemon1 = parse_pokemon(data[0x00:0x50])
    pokemon2 = parse_pokemon(data[0x8C:0xDC])

    if pokemon1 is None:
        egg_groups1 = []
    else:
        egg_groups1 = pokemon1.species.egg_groups

    if pokemon2 is None:
        egg_groups2 = []
    else:
        egg_groups2 = pokemon2.species.egg_groups

    return DaycareData(
        pokemon1=pokemon1,
        pokemon1_egg_groups=egg_groups1,
        pokemon1_steps=unpack_uint32(data[0x88:0x8C]),
        pokemon2=pokemon2,
        pokemon2_egg_groups=egg_groups2,
        pokemon2_steps=unpack_uint32(data[0x114:0x118]),
        offspring_personality=unpack_uint32(data[0x118:0x11C]),
        step_counter=int(data[0x11C]),
        compatibility=DaycareCompatibility.CalculateFor(pokemon1, pokemon2),
    )
