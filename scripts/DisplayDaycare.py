# Displays Data of the Daycare
# Move this script to the root directory to ensure all imports work correctly

import struct
from rich.table import Table
from rich.live import Live
from modules.Memory import GetSaveBlock, ParsePokemon

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
"""


def ParseDayCare():
    b_Daycare = GetSaveBlock(1, 0x3030, 0x120)
    DayCare = {
        "mons": [
            {
                "mon": ParsePokemon(b_Daycare[0x0:0x50]),
                "steps": struct.unpack("<I", b_Daycare[0x88:0x8C])[0],
            },
            {
                "mon": ParsePokemon(b_Daycare[0x8C:0xDC]),
                "steps": struct.unpack("<I", b_Daycare[0x114:0x118])[0],
            },
        ],
        "offspringPersonality": struct.unpack("<I", b_Daycare[0x118:0x11C])[0],
        "stepCounter": int(b_Daycare[0x11C])
    }
    return DayCare


def generate_table() -> Table:
    table = Table()
    table.add_column("Name", justify="left", no_wrap=True)
    table.add_column("Value", justify="left", width=10)
    if(last_data["mons"][0]["mon"]):
        table.add_row("Mon 1 Name", str(last_data["mons"][0]["mon"]["name"]))
        table.add_row("Mon 1 Steps", str(last_data["mons"][0]["steps"]))
    if(last_data["mons"][1]["mon"]):
        table.add_row("Mon 2 Name", str(last_data["mons"][1]["mon"]["name"]))
        table.add_row("Mon 2 Steps", str(last_data["mons"][1]["steps"]))
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
