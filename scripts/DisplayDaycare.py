# Displays Data of the Daycare
# Move this script to the root directory to ensure all imports work correctly

import struct
from rich.table import Table
from rich.live import Live
from modules.Memory import GetSaveBlock, ParsePokemon, pokemon_list

# https://github.com/pret/pokeemerald/blob/master/src/daycare.c


def ParseDayCare():
    b_DayCare = GetSaveBlock(1, 0x3030, 0x120)
    mons = [ParsePokemon(b_DayCare[0x0:0x50]), ParsePokemon(b_DayCare[0x8C:0xDC])]
    DayCare = {
        'mons': [
            {
                'mon': mons[0],
                'steps': struct.unpack('<I', b_DayCare[0x88:0x8C])[0],
            },
            {
                'mon': mons[1],
                'steps': struct.unpack('<I', b_DayCare[0x114:0x118])[0],
            },
        ],
        'offspringPersonality': struct.unpack('<I', b_DayCare[0x118:0x11C])[0],
        'stepCounter': int(b_DayCare[0x11C]),
        'DaycareCompatibilityScore': GetDaycareCompatibilityScore(mons)
        if (mons[0] and mons[1])
        else PARENTS_INCOMPATIBLE,
    }
    return DayCare


MON_MALE = 0x00
MON_FEMALE = 0xFE
MON_GENDERLESS = 0xFF


def GetGenderFromSpeciesAndPersonality(name: int, personality: int):
    gender_ratio = pokemon_list[name]['gender_rate']
    if (
        gender_ratio == MON_MALE
        or gender_ratio == MON_FEMALE
        or gender_ratio == MON_GENDERLESS
    ):
        return gender_ratio
    if gender_ratio > (personality & 0xFF):
        return MON_FEMALE
    else:
        return MON_MALE


# Determine if the two given egg group lists contain any of the
# same egg groups.
def EggGroupsOverlap(eggGroups1, eggGroups2):
    for i in range(2):
        for j in range(2):
            if eggGroups1[i] == eggGroups2[j]:
                return True
    return False


EGG_GROUP_NONE = 0
EGG_GROUP_MONSTER = 1
EGG_GROUP_WATER_1 = 2
EGG_GROUP_BUG = 3
EGG_GROUP_FLYING = 4
EGG_GROUP_FIELD = 5
EGG_GROUP_FAIRY = 6
EGG_GROUP_GRASS = 7
EGG_GROUP_HUMAN_LIKE = 8
EGG_GROUP_WATER_3 = 9
EGG_GROUP_MINERAL = 10
EGG_GROUP_AMORPHOUS = 11
EGG_GROUP_WATER_2 = 12
EGG_GROUP_DITTO = 13
EGG_GROUP_DRAGON = 14
EGG_GROUP_UNDISCOVERED = 15

PARENTS_INCOMPATIBLE = 0
PARENTS_LOW_COMPATIBILITY = 20
PARENTS_MED_COMPATIBILITY = 50
PARENTS_MAX_COMPATIBILITY = 70


def GetDaycareCompatibilityScore(mons):
    egg_groups = [[0, 0], [0, 0]]
    species = [0, 0]
    trainer_ids = [0, 0]
    genders = [0, 0]
    for i in range(2):
        species[i] = mons[i]['natID']
        trainer_ids[i] = mons[i]['ot']['tid']
        personality = mons[i]['pid']
        genders[i] = GetGenderFromSpeciesAndPersonality(mons[i]['name'], personality)
        egg_groups[i] = pokemon_list[mons[i]['name']]['egg_groups']

    # check unbreedable egg group
    if (
        egg_groups[0][0] == EGG_GROUP_UNDISCOVERED
        or egg_groups[1][0] == EGG_GROUP_UNDISCOVERED
    ):
        return PARENTS_INCOMPATIBLE
    # two Ditto can't breed
    if egg_groups[0][0] == EGG_GROUP_DITTO and egg_groups[1][0] == EGG_GROUP_DITTO:
        return PARENTS_INCOMPATIBLE

    # one parent is Ditto
    if egg_groups[0][0] == EGG_GROUP_DITTO or egg_groups[1][0] == EGG_GROUP_DITTO:
        if trainer_ids[0] == trainer_ids[1]:
            return PARENTS_LOW_COMPATIBILITY
        else:
            return PARENTS_MED_COMPATIBILITY
    else:  # neither parent is Ditto
        if genders[0] == genders[1]:
            return PARENTS_INCOMPATIBLE
        if genders[0] == MON_GENDERLESS or genders[1] == MON_GENDERLESS:
            return PARENTS_INCOMPATIBLE
        if not EggGroupsOverlap(egg_groups[0], egg_groups[1]):
            return PARENTS_INCOMPATIBLE

        if species[0] == species[1]:
            if trainer_ids[0] == trainer_ids[1]:
                return PARENTS_MED_COMPATIBILITY  # same species, same trainer
            return PARENTS_MAX_COMPATIBILITY  # same species, different trainers
        else:
            if trainer_ids[0] != trainer_ids[1]:
                return (
                    PARENTS_MED_COMPATIBILITY  # different species, different trainers
                )
            return PARENTS_LOW_COMPATIBILITY  # different species, same trainer


def generate_table() -> Table:
    table = Table()
    table.add_column('Name', justify='left', no_wrap=True)
    table.add_column('Value', justify='left', width=10)
    if last_data['mons'][0]['mon']:
        table.add_row('Mon 1 Name', str(last_data['mons'][0]['mon']['name']))
        table.add_row(
            'Mon 1 Gender',
            str(
                GetGenderFromSpeciesAndPersonality(
                    last_data['mons'][0]['mon']['name'],
                    last_data['mons'][0]['mon']['pid'],
                )
            ),
        )
        table.add_row('Mon 1 Steps', str(last_data['mons'][0]['steps']))
    if last_data['mons'][1]['mon']:
        table.add_row('Mon 2 Name', str(last_data['mons'][1]['mon']['name']))
        table.add_row(
            'Mon 2 Gender',
            str(
                GetGenderFromSpeciesAndPersonality(
                    last_data['mons'][1]['mon']['name'],
                    last_data['mons'][1]['mon']['pid']
                )
            ),
        )
        table.add_row('Mon 2 Steps', str(last_data['mons'][1]['steps']))
    table.add_row(
        'Daycare Compatibility Score', str(last_data['DaycareCompatibilityScore'])
    )
    table.add_row('Offspring Personality', str(last_data['offspringPersonality']))
    table.add_row('Daycare Step Counter', str(last_data['stepCounter']))
    return table


last_data = ParseDayCare()
with Live(generate_table(), refresh_per_second=4) as live:
    while True:
        data = ParseDayCare()
        if data != last_data:
            last_data = data
            live.update(generate_table())
