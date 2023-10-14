from dataclasses import dataclass
from enum import IntEnum
from typing import Union
from modules.Memory import GetSaveBlock
from modules.Pokemon import ParsePokemon, pokemon_list


class EggGroup(IntEnum):
    _None = 0
    Monster = 1
    Water1 = 2
    Bug = 3
    Flying = 4
    Field = 5
    Fairy = 6
    Grass = 7
    HumanLike = 8
    Water3 = 9
    Mineral = 10
    Amorphous = 11
    Water2 = 12
    Ditto = 13
    Dragon = 14
    Undiscovered = 15

    @classmethod
    def GetForPokemon(cls, pokemon: dict) -> list['EggGroup']:
        result = []
        for egg_group in pokemon_list[pokemon['name']]['egg_groups']:
            result.append(EggGroup(egg_group))
        return result


class PokemonGender(IntEnum):
    Male = 0
    Female = 1
    Genderless = 2

    @classmethod
    def GetFromPokemonData(cls, pokemon: dict):
        species = pokemon_list[pokemon['name']]
        gender_threshold = species['gender_rate']
        gender_value = pokemon['pid'] % 256

        if gender_threshold == 0xFF:
            return PokemonGender.Genderless
        elif gender_threshold == 0xFE:
            return PokemonGender.Female
        elif gender_threshold == 0x00:
            return PokemonGender.Male
        elif gender_value >= gender_threshold:
            return PokemonGender.Male
        else:
            return PokemonGender.Female


class DaycareCompatibility(IntEnum):
    Incompatible = 0
    Low = 20
    Medium = 50
    High = 70

    @classmethod
    def CalculateFor(cls, pokemon1: Union[dict, None], pokemon2: Union[dict, None]) -> tuple[
        'DaycareCompatibility', str]:
        if pokemon1 is None or pokemon2 is None:
            return DaycareCompatibility.Incompatible, 'Less than two Pokémon in daycare'

        egg_groups1 = pokemon_list[pokemon1['name']]['egg_groups']
        egg_groups2 = pokemon_list[pokemon2['name']]['egg_groups']

        # The 'undiscovered' egg group cannot be bred.
        if egg_groups1[0] == 'no-eggs' or egg_groups2[0] == 'no-eggs':
            return DaycareCompatibility.Incompatible, 'At least one of the Pokémon is in the "Undiscovered" egg group'

        # Breeding with Ditto is special.
        if egg_groups1[0] == 'ditto' or egg_groups2[0] == 'ditto':
            if egg_groups1[0] == egg_groups2[0]:
                return DaycareCompatibility.Incompatible, 'Two Ditto cannot be bred'
            elif pokemon1['ot']['tid'] == pokemon2['ot']['tid']:
                return DaycareCompatibility.Low, 'Breeding with Ditto, same OT'
            else:
                return DaycareCompatibility.Medium, 'Breeding with Ditto, different OT'

        gender1 = PokemonGender.GetFromPokemonData(pokemon1)
        gender2 = PokemonGender.GetFromPokemonData(pokemon2)

        # Basic biology.
        if gender1 == gender2:
            return DaycareCompatibility.Incompatible, 'Pokémon have the same gender'

        if gender1 == PokemonGender.Genderless or gender2 == PokemonGender.Genderless:
            return DaycareCompatibility.Incompatible, 'At least one of the Pokémon is genderless'

        # Check for overlapping egg groups.
        if len(set(egg_groups1) & set(egg_groups2)) == 0:
            return DaycareCompatibility.Incompatible, 'No overlapping egg groups'

        if pokemon1['natID'] == pokemon2['natID']:
            if pokemon1['ot']['tid'] == pokemon2['ot']['tid']:
                return DaycareCompatibility.Medium, 'Same species, same OT'
            else:
                return DaycareCompatibility.High, 'Same species, different OT'
        else:
            if pokemon1['ot']['tid'] == pokemon2['ot']['tid']:
                return DaycareCompatibility.Low, 'Different species, same OT'
            else:
                return DaycareCompatibility.Medium, 'Different species, different OT'


@dataclass
class DaycareData:
    pokemon1: dict
    pokemon1_egg_groups: list[str]
    pokemon1_steps: int
    pokemon2: dict
    pokemon2_egg_groups: list[str]
    pokemon2_steps: int

    offspring_personality: int
    step_counter: int
    compatibility: tuple[DaycareCompatibility, str]


def GetDaycareData() -> Union[DaycareData, None]:
    data = GetSaveBlock(1, 0x3030, 0x120)
    if data is None:
        return None

    pokemon1 = ParsePokemon(data[0x00:0x50])
    pokemon2 = ParsePokemon(data[0x8C:0xDC])

    if pokemon1 is None:
        egg_groups1 = []
    else:
        egg_groups1 = pokemon_list[pokemon1['name']]['egg_groups']

    if pokemon2 is None:
        egg_groups2 = []
    else:
        egg_groups2 = pokemon_list[pokemon2['name']]['egg_groups']

    return DaycareData(
        pokemon1=pokemon1,
        pokemon1_egg_groups=egg_groups1,
        pokemon1_steps=int.from_bytes(data[0x88:0x8C], byteorder='little'),
        pokemon2=pokemon2,
        pokemon2_egg_groups=egg_groups2,
        pokemon2_steps=int.from_bytes(data[0x114:0x118], byteorder='little'),
        offspring_personality=int.from_bytes(data[0x118:0x11C], byteorder='little'),
        step_counter=int(data[0x11C]),
        compatibility=DaycareCompatibility.CalculateFor(pokemon1, pokemon2)
    )
