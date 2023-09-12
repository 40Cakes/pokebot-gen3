# Displays Data of the Daycare
# Move this script to the root directory to ensure all imports work correctly

import struct
from rich.table import Table
from rich.live import Live
from modules.Memory import GetSaveBlock, ParsePokemon, pokemon_list

"""
struct SaveBlock1
{
    /*0x3030*/ struct DayCare daycare;
};

#define MAIL_WORDS_COUNT 9
#define PLAYER_NAME_LENGTH 7
#define POKEMON_NAME_LENGTH 10
#define DAYCARE_MON_COUNT 2
#define TRAINER_ID_LENGTH 4
struct Mail
{
    /*0x00*/ u16 words[MAIL_WORDS_COUNT];
    /*0x12*/ u8 playerName[PLAYER_NAME_LENGTH + 1];
    /*0x1D*/ u8 trainerId[TRAINER_ID_LENGTH];
    /*0x21*/ u16 species;
    /*0x23*/ u16 itemId;
};

struct DaycareMail
{
    /*0x00*/ struct Mail message;
    /*0x24*/ u8 otName[PLAYER_NAME_LENGTH + 1];
    /*0x2C*/ u8 monName[POKEMON_NAME_LENGTH + 1];
    /*0x37*/ u8 gameLanguage:4;
    /*0x38*/ u8 monLanguage:4;
};

struct DaycareMon
{
    /*0x00*/ struct BoxPokemon mon;
    /*0x50*/ struct DaycareMail mail;
    /*0x88*/ u32 steps;
};

struct DayCare
{
    /*0x00*/ struct DaycareMon mons[DAYCARE_MON_COUNT];
    /*0x118*/ u32 offspringPersonality;
    /*0x11C*/ u8 stepCounter;
    /*0x11D*/ //u8 padding[3];
};

#define EGG_GROUPS_PER_MON      2
static u8 GetDaycareCompatibilityScore(struct DayCare *daycare)
{
    u32 i;
    u16 eggGroups[DAYCARE_MON_COUNT][EGG_GROUPS_PER_MON];
    u16 species[DAYCARE_MON_COUNT];
    u32 trainerIds[DAYCARE_MON_COUNT];
    u32 genders[DAYCARE_MON_COUNT];

    for (i = 0; i < DAYCARE_MON_COUNT; i++)
    {
        u32 personality;

        species[i] = GetBoxMonData(&daycare->mons[i].mon, MON_DATA_SPECIES);
        trainerIds[i] = GetBoxMonData(&daycare->mons[i].mon, MON_DATA_OT_ID);
        personality = GetBoxMonData(&daycare->mons[i].mon, MON_DATA_PERSONALITY);
        genders[i] = GetGenderFromSpeciesAndPersonality(species[i], personality);
        eggGroups[i][0] = gSpeciesInfo[species[i]].eggGroups[0];
        eggGroups[i][1] = gSpeciesInfo[species[i]].eggGroups[1];
    }

    // check unbreedable egg group
    if (eggGroups[0][0] == EGG_GROUP_UNDISCOVERED || eggGroups[1][0] == EGG_GROUP_UNDISCOVERED)
        return PARENTS_INCOMPATIBLE;
    // two Ditto can't breed
    if (eggGroups[0][0] == EGG_GROUP_DITTO && eggGroups[1][0] == EGG_GROUP_DITTO)
        return PARENTS_INCOMPATIBLE;

    // one parent is Ditto
    if (eggGroups[0][0] == EGG_GROUP_DITTO || eggGroups[1][0] == EGG_GROUP_DITTO)
    {
        if (trainerIds[0] == trainerIds[1])
            return PARENTS_LOW_COMPATIBILITY;

        return PARENTS_MED_COMPATIBILITY;
    }
    // neither parent is Ditto
    else
    {
        if (genders[0] == genders[1])
            return PARENTS_INCOMPATIBLE;
        if (genders[0] == MON_GENDERLESS || genders[1] == MON_GENDERLESS)
            return PARENTS_INCOMPATIBLE;
        if (!EggGroupsOverlap(eggGroups[0], eggGroups[1]))
            return PARENTS_INCOMPATIBLE;

        if (species[0] == species[1])
        {
            if (trainerIds[0] == trainerIds[1])
                return PARENTS_MED_COMPATIBILITY; // same species, same trainer

            return PARENTS_MAX_COMPATIBILITY; // same species, different trainers
        }
        else
        {
            if (trainerIds[0] != trainerIds[1])
                return PARENTS_MED_COMPATIBILITY; // different species, different trainers

            return PARENTS_LOW_COMPATIBILITY; // different species, same trainer
        }
    }
}

// Determine if the two given egg group lists contain any of the
// same egg groups.
static bool8 EggGroupsOverlap(u16 *eggGroups1, u16 *eggGroups2)
{
    s32 i, j;

    for (i = 0; i < EGG_GROUPS_PER_MON; i++)
    {
        for (j = 0; j < EGG_GROUPS_PER_MON; j++)
        {
            if (eggGroups1[i] == eggGroups2[j])
                return TRUE;
        }
    }

    return FALSE;
}

u8 GetGenderFromSpeciesAndPersonality(u16 species, u32 personality)
{
    switch (gSpeciesInfo[species].genderRatio)
    {
    case MON_MALE:
    case MON_FEMALE:
    case MON_GENDERLESS:
        return gSpeciesInfo[species].genderRatio;
    }

    if (gSpeciesInfo[species].genderRatio > (personality & 0xFF))
        return MON_FEMALE;
    else
        return MON_MALE;
}

"""


def ParseDayCare():
    b_Daycare = GetSaveBlock(1, 0x3030, 0x120)
    mons = [ParsePokemon(b_Daycare[0x0:0x50]), ParsePokemon(b_Daycare[0x8C:0xDC])]
    DayCare = {
        "mons": [
            {
                "mon": mons[0],
                "steps": struct.unpack("<I", b_Daycare[0x88:0x8C])[0],
            },
            {
                "mon": mons[1],
                "steps": struct.unpack("<I", b_Daycare[0x114:0x118])[0],
            },
        ],
        "offspringPersonality": struct.unpack("<I", b_Daycare[0x118:0x11C])[0],
        "stepCounter": int(b_Daycare[0x11C]),
        "DaycareCompatibilityScore": GetDaycareCompatibilityScore(mons)
        if (mons[0] and mons[1])
        else PARENTS_INCOMPATIBLE,
    }
    return DayCare


MON_MALE = 0x00
MON_FEMALE = 0xFE
MON_GENDERLESS = 0xFF


def GetGenderFromSpeciesAndPersonality(name: int, personality: int):
    genderRatio = pokemon_list[name]["gender_rate"]
    if (
        genderRatio == MON_MALE
        or genderRatio == MON_FEMALE
        or genderRatio == MON_GENDERLESS
    ):
        return genderRatio
    if genderRatio > (personality & 0xFF):
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
    eggGroups = [[0, 0], [0, 0]]
    species = [0, 0]
    trainerIds = [0, 0]
    genders = [0, 0]
    for i in range(2):
        species[i] = mons[i]["natID"]
        trainerIds[i] = mons[i]["ot"]["tid"]
        personality = mons[i]["pid"]
        genders[i] = GetGenderFromSpeciesAndPersonality(mons[i]["name"], personality)
        eggGroups[i] = pokemon_list[mons[i]["name"]]["egg_groups"]

    # check unbreedable egg group
    if (
        eggGroups[0][0] == EGG_GROUP_UNDISCOVERED
        or eggGroups[1][0] == EGG_GROUP_UNDISCOVERED
    ):
        return PARENTS_INCOMPATIBLE
    # two Ditto can't breed
    if eggGroups[0][0] == EGG_GROUP_DITTO and eggGroups[1][0] == EGG_GROUP_DITTO:
        return PARENTS_INCOMPATIBLE

    # one parent is Ditto
    if eggGroups[0][0] == EGG_GROUP_DITTO or eggGroups[1][0] == EGG_GROUP_DITTO:
        if trainerIds[0] == trainerIds[1]:
            return PARENTS_LOW_COMPATIBILITY
        else:
            return PARENTS_MED_COMPATIBILITY
    else:  # neither parent is Ditto
        if genders[0] == genders[1]:
            return PARENTS_INCOMPATIBLE
        if genders[0] == MON_GENDERLESS or genders[1] == MON_GENDERLESS:
            return PARENTS_INCOMPATIBLE
        if not EggGroupsOverlap(eggGroups[0], eggGroups[1]):
            return PARENTS_INCOMPATIBLE

        if species[0] == species[1]:
            if trainerIds[0] == trainerIds[1]:
                return PARENTS_MED_COMPATIBILITY  # same species, same trainer
            return PARENTS_MAX_COMPATIBILITY  # same species, different trainers
        else:
            if trainerIds[0] != trainerIds[1]:
                return (
                    PARENTS_MED_COMPATIBILITY  # different species, different trainers
                )
            return PARENTS_LOW_COMPATIBILITY  # different species, same trainer


def generate_table() -> Table:
    table = Table()
    table.add_column("Name", justify="left", no_wrap=True)
    table.add_column("Value", justify="left", width=10)
    if last_data["mons"][0]["mon"]:
        table.add_row("Mon 1 Name", str(last_data["mons"][0]["mon"]["name"]))
        table.add_row(
            "Mon 1 Gender",
            str(
                GetGenderFromSpeciesAndPersonality(
                    last_data["mons"][0]["mon"]["name"],
                    last_data["mons"][0]["mon"]["pid"],
                )
            ),
        )
        table.add_row("Mon 1 Steps", str(last_data["mons"][0]["steps"]))
    if last_data["mons"][1]["mon"]:
        table.add_row("Mon 2 Name", str(last_data["mons"][1]["mon"]["name"]))
        table.add_row(
            "Mon 2 Gender",
            str(
                GetGenderFromSpeciesAndPersonality(
                    last_data["mons"][1]["mon"]["name"],
                    last_data["mons"][1]["mon"]["pid"],
                )
            ),
        )
        table.add_row("Mon 2 Steps", str(last_data["mons"][1]["steps"]))
    table.add_row(
        "Daycare Compatibility Score", str(last_data["DaycareCompatibilityScore"])
    )
    table.add_row("Offspring Personality", str(last_data["offspringPersonality"]))
    table.add_row("Daycare Step Counter", str(last_data["stepCounter"]))
    return table


last_data = ParseDayCare()
with Live(generate_table(), refresh_per_second=4) as live:
    while True:
        data = ParseDayCare()
        if data != last_data:
            last_data = data
            live.update(generate_table())
