import json
import os
import string
import sys
from pathlib import Path
from typing import IO, BinaryIO

sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.game import set_rom, decode_string, get_symbol, get_symbol_name_before
from modules.roms import list_available_roms, ROMLanguage, ROM


def find_roms() -> tuple[ROM, dict[str, ROM], dict[str, ROM]]:
    """
    Ensures that we have a valid Emerald ROM for every possible language.
    To make things easier, we only support rev. 0 so we don't have to manage
    too many different offsets.

    :return: A tuple where the first entry is the English ROM, and the second entry
             is a dictionary with language code as the key and the matching ROM file
             as value.
    """
    english_rom = None
    matched_languages = set([])
    language_roms: dict[str, ROM] = {}
    other_editions_roms: dict[str, ROM] = {}

    for rom in list_available_roms():
        if rom.game_title != "POKEMON EMER" and rom.revision == 1 and rom.language == ROMLanguage.English:
            other_editions_roms[rom.game_title[8:]] = rom

        if rom.game_title != "POKEMON EMER" or rom.revision != 0:
            continue

        if rom.language == ROMLanguage.English and english_rom is None:
            english_rom = rom

        if str(rom.language) not in matched_languages:
            matched_languages.add(str(rom.language))
            language_roms[str(rom.language)] = rom

    if english_rom is None:
        raise Exception("Could not find an English Emerald (rev 0) ROM.")

    if len(language_roms) != 6:
        raise Exception(
            "Could not find all languages of Emerald (rev 0). Languages found: " + ", ".join(language_roms.keys())
        )

    if len(other_editions_roms) != 4:
        missing_editions = ", ".join(("RUBY", "SAPP", "FIRE", "LEAF") - other_editions_roms.keys())
        raise Exception(f"Could not find rev 1 ROMs for all other editions. Missing: {missing_editions}")

    return english_rom, language_roms, other_editions_roms


def initialise_localised_string() -> dict[str, str]:
    """
    Sets up the default dict structure for translatable strings.
    :return: Dict that maps each language code to an empty string
    """
    return {"D": "", "E": "", "F": "", "I": "", "J": "", "S": ""}


def get_address(symbol_name: str) -> int:
    """
    The GBA maps the ROM to memory location 0x0800_0000, so the symbol table
    references addresses in that range. Since we are working with the actual
    ROM file here, that 0x0800_0000 must be subtracted from any address.
    :param symbol_name: Name of the symbol to look up
    :return: The offset from the start of the ROM
    """
    return get_symbol(symbol_name)[0] - 0x0800_0000


def read_string(file: IO, offset: int = -1) -> str:
    """
    Reads a string of unknown length from a file, all the way up to the next
    0xFF byte (which indicates the end of a string, similar to 0x00 in C-style
    strings.)
    :param file: The file handle, opened in binary read mode.
    :param offset: Offset from the start of the file to read the string from.
                   If negative, this will use the current file cursor position
                   and not restore it after advancing it by reading.
    :return: The decoded string.
    """
    previous_position = file.tell()
    if offset >= 0:
        file.seek(offset, os.SEEK_SET)
    file_size = os.fstat(file.fileno()).st_size
    buffer = b""
    while file.tell() < file_size - 1:
        byte = file.read(1)
        if byte == b"\xff":
            break
        else:
            buffer += byte
    if offset >= 0:
        file.seek(previous_position, os.SEEK_SET)
    return decode_string(buffer)


def get_tm_hm_move_map(data_source: BinaryIO) -> dict[str, int]:
    offset = get_address("sTMHMMoves")
    data_source.seek(offset)
    tm_hm_data = data_source.read(0x74)
    tm_hm_move_map: dict[str, int] = {}
    for index in range(58):
        if index >= 50:
            item_name = f"HM{index - 49:02d}"
        else:
            item_name = f"TM{index + 1:02d}"
        tm_hm_move_map[item_name] = int.from_bytes(tm_hm_data[index * 2 : (index + 1) * 2], byteorder="little")
    return tm_hm_move_map


def extract_items(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    item_list = []
    type_map = [
        "mail",
        "usable_outside_battle",
        "usable_in_certain_locations",
        "pokeblock_case",
        "not_usable_outside_battle",
    ]
    battle_use_map = {
        "ItemUseInBattle_PokeBall": "catch",
        "ItemUseInBattle_StatIncrease": "stat_increase",
        "ItemUseInBattle_Medicine": "healing",
        "ItemUseInBattle_PPRecovery": "pp_recovery",
        "ItemUseInBattle_Escape": "escape",
        "ItemUseInBattle_EnigmaBerry": "enigma_berry",
    }
    pocket_map = ["???", "items", "poke_balls", "tms_and_hms", "berries", "key_items"]

    set_rom(english_rom)
    with open(english_rom.file, "rb") as english_file:
        # Extract move mapping for HM/TM items
        tm_hm_move_map = get_tm_hm_move_map(english_file)

        # Extract items themselves
        offset = get_address("gItems")
        for i in range(377):
            english_file.seek(offset + (i * 44))
            item_data = english_file.read(44)

            name = decode_string(item_data[:14])
            pretty_name = string.capwords(name)
            if pretty_name.startswith(("Tm", "Hm", "Pp", "Hp", "Vs")):
                pretty_name = pretty_name[:2].upper() + pretty_name[2:]
            if pretty_name.startswith("S.s."):
                pretty_name = f"S.S.{pretty_name[4:]}"

            pocket = int.from_bytes(item_data[26:27], byteorder="little")

            # Poké Balls use the 'item type' field to indicate the Poké Ball type instead.
            if pocket == 2:
                item_type = int.from_bytes(item_data[27:28], byteorder="little")
            else:
                item_type = type_map[int.from_bytes(item_data[27:28], byteorder="little")]

            if int.from_bytes(item_data[32:33], byteorder="little") > 0:
                battle_use_function = int.from_bytes(item_data[36:40], byteorder="little")
                battle_use = get_symbol_name_before(battle_use_function, True)
                if battle_use in battle_use_map:
                    battle_use = battle_use_map[battle_use]
                else:
                    battle_use = None
            else:
                battle_use = None

            if (pretty_name.startswith("TM") or pretty_name.startswith("HM")) and pretty_name != "TM Case":
                move_id = tm_hm_move_map[pretty_name]
            else:
                move_id = None

            item_entry = {
                "index": int.from_bytes(item_data[14:16], byteorder="little"),
                "name": pretty_name,
                "price": int.from_bytes(item_data[16:18], byteorder="little"),
                "type": item_type,
                "battle_use": battle_use,
                "pocket": pocket_map[pocket],
                "parameter": int.from_bytes(item_data[19:20], byteorder="little"),
                "extra_parameter": int.from_bytes(item_data[40:44], byteorder="little"),
                "tm_hm_move_id": move_id,
                "localised_names": initialise_localised_string(),
                "localised_descriptions": initialise_localised_string(),
            }

            item_list.append(item_entry)

    for language_code in "DEFIJS":
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, "rb") as localised_file:
            set_rom(localised_rom)

            if language_code == "J":
                length_of_item = 40
                length_of_name = 10
                description_pointer_offset = 16
            else:
                length_of_item = 44
                length_of_name = 14
                description_pointer_offset = 20

            offset = get_address("gItems")
            localised_file.seek(offset, os.SEEK_SET)

            for i in range(377):
                item_data = localised_file.read(length_of_item)
                name = decode_string(item_data[:length_of_name])

                description_pointer = int.from_bytes(
                    item_data[description_pointer_offset : description_pointer_offset + 4], byteorder="little"
                )
                description = read_string(localised_file, description_pointer - 0x0800_0000)

                item_list[i]["localised_names"][language_code] = name
                item_list[i]["localised_descriptions"][language_code] = description

    return item_list


def extract_abilities(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    abilities_list = []

    set_rom(english_rom)
    offset = get_address("gAbilityNames")

    with open(english_rom.file, "rb") as english_file:
        abilities_list.extend(
            {
                "name": string.capwords(read_string(english_file, offset + (i * 13))),
                "localised_names": initialise_localised_string(),
                "localised_descriptions": initialise_localised_string(),
            }
            for i in range(78)
        )
    for language_code in "DEFIJS":
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, "rb") as localised_file:
            set_rom(localised_rom)

            offset = get_address("gAbilityNames")
            for i in range(78):
                if language_code == "J":
                    name = read_string(localised_file, offset + (i * 8))
                else:
                    name = read_string(localised_file, offset + (i * 13))
                abilities_list[i]["localised_names"][language_code] = name

            end_of_strings_found = 0
            while end_of_strings_found <= 78:
                offset -= 1
                localised_file.seek(offset, os.SEEK_SET)
                if localised_file.read(1) == b"\xff":
                    end_of_strings_found += 1

            for i in range(78):
                abilities_list[i]["localised_descriptions"][language_code] = read_string(localised_file)

    return abilities_list


def extract_types(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    types_list = []

    set_rom(english_rom)
    with open(english_rom.file, "rb") as english_file:
        offset = get_address("gTypeNames")
        for i in range(18):
            name = string.capwords(read_string(english_file, offset + (i * 7)))
            if name == "Electr":
                name = "Electric"
            elif name == "Psychc":
                name = "Psychic"
            elif name == "Fight":
                name = "Fighting"
            types_list.append(
                {
                    "name": name,
                    "effectiveness": {},
                    "localised_names": initialise_localised_string(),
                }
            )

        english_file.seek(get_address("gTypeEffectiveness"))
        for i in range(112):
            data = english_file.read(3)
            if data[0] < 18:
                types_list[data[0]]["effectiveness"][types_list[data[1]]["name"]] = data[2] / 10

    for language_code in "DEFIJS":
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, "rb") as localised_file:
            set_rom(localised_rom)

            localised_file.seek(get_address("gTypeNames"))
            for i in range(18):
                name_length = 5 if language_code == "J" else 7
                types_list[i]["localised_names"][language_code] = decode_string(localised_file.read(name_length))

    return types_list


def extract_natures(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    natures_list = []

    set_rom(english_rom)
    with open(english_rom.file, "rb") as english_file:
        english_file.seek(get_address("sHardyNatureName"))
        natures_list.extend(
            {
                "name": string.capwords(read_string(english_file)),
                "localised_names": initialise_localised_string(),
            }
            for _ in range(25)
        )
        english_file.seek(get_address("gNatureStatTable"))
        for i in range(25):
            modifiers = english_file.read(5)
            stats_list = ["attack", "defence", "speed", "special_attack", "special_defence"]
            for j in range(len(stats_list)):
                key = f"{stats_list[j]}_modifier"
                if modifiers[j] == 0:
                    natures_list[i][key] = 1
                elif modifiers[j] == 1:
                    natures_list[i][key] = 1.1
                else:
                    natures_list[i][key] = 0.9

    for language_code in "DEFIJS":
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, "rb") as localised_file:
            set_rom(localised_rom)

            localised_file.seek(get_address("sHardyNatureName"))
            for i in range(25):
                natures_list[i]["localised_names"][language_code] = read_string(localised_file)

    return natures_list


def extract_moves(english_rom: ROM, localised_roms: dict[str, ROM], types_list: list[dict]) -> list[dict]:
    set_rom(english_rom)

    moves_list = []
    # Names taken verbatim from the decompilation project; nothing official
    effect_map = [
        "HIT",
        "SLEEP",
        "POISON_HIT",
        "ABSORB",
        "BURN_HIT",
        "FREEZE_HIT",
        "PARALYZE_HIT",
        "EXPLOSION",
        "DREAM_EATER",
        "MIRROR_MOVE",
        "ATTACK_UP",
        "DEFENSE_UP",
        "SPEED_UP",
        "SPECIAL_ATTACK_UP",
        "SPECIAL_DEFENSE_UP",
        "ACCURACY_UP",
        "EVASION_UP",
        "ALWAYS_HIT",
        "ATTACK_DOWN",
        "DEFENSE_DOWN",
        "SPEED_DOWN",
        "SPECIAL_ATTACK_DOWN",
        "SPECIAL_DEFENSE_DOWN",
        "ACCURACY_DOWN",
        "EVASION_DOWN",
        "HAZE",
        "BIDE",
        "RAMPAGE",
        "ROAR",
        "MULTI_HIT",
        "CONVERSION",
        "FLINCH_HIT",
        "RESTORE_HP",
        "TOXIC",
        "PAY_DAY",
        "LIGHT_SCREEN",
        "TRI_ATTACK",
        "REST",
        "OHKO",
        "RAZOR_WIND",
        "SUPER_FANG",
        "DRAGON_RAGE",
        "TRAP",
        "HIGH_CRITICAL",
        "DOUBLE_HIT",
        "RECOIL_IF_MISS",
        "MIST",
        "FOCUS_ENERGY",
        "RECOIL",
        "CONFUSE",
        "ATTACK_UP_2",
        "DEFENSE_UP_2",
        "SPEED_UP_2",
        "SPECIAL_ATTACK_UP_2",
        "SPECIAL_DEFENSE_UP_2",
        "ACCURACY_UP_2",
        "EVASION_UP_2",
        "TRANSFORM",
        "ATTACK_DOWN_2",
        "DEFENSE_DOWN_2",
        "SPEED_DOWN_2",
        "SPECIAL_ATTACK_DOWN_2",
        "SPECIAL_DEFENSE_DOWN_2",
        "ACCURACY_DOWN_2",
        "EVASION_DOWN_2",
        "REFLECT",
        "POISON",
        "PARALYZE",
        "ATTACK_DOWN_HIT",
        "DEFENSE_DOWN_HIT",
        "SPEED_DOWN_HIT",
        "SPECIAL_ATTACK_DOWN_HIT",
        "SPECIAL_DEFENSE_DOWN_HIT",
        "ACCURACY_DOWN_HIT",
        "EVASION_DOWN_HIT",
        "SKY_ATTACK",
        "CONFUSE_HIT",
        "TWINEEDLE",
        "VITAL_THROW",
        "SUBSTITUTE",
        "RECHARGE",
        "RAGE",
        "MIMIC",
        "METRONOME",
        "LEECH_SEED",
        "SPLASH",
        "DISABLE",
        "LEVEL_DAMAGE",
        "PSYWAVE",
        "COUNTER",
        "ENCORE",
        "PAIN_SPLIT",
        "SNORE",
        "CONVERSION_2",
        "LOCK_ON",
        "SKETCH",
        "???",
        "SLEEP_TALK",
        "DESTINY_BOND",
        "FLAIL",
        "SPITE",
        "FALSE_SWIPE",
        "HEAL_BELL",
        "QUICK_ATTACK",
        "TRIPLE_KICK",
        "THIEF",
        "MEAN_LOOK",
        "NIGHTMARE",
        "MINIMIZE",
        "CURSE",
        "UNUSED_6E",
        "PROTECT",
        "SPIKES",
        "FORESIGHT",
        "PERISH_SONG",
        "SANDSTORM",
        "ENDURE",
        "ROLLOUT",
        "SWAGGER",
        "FURY_CUTTER",
        "ATTRACT",
        "RETURN",
        "PRESENT",
        "FRUSTRATION",
        "SAFEGUARD",
        "THAW_HIT",
        "MAGNITUDE",
        "BATON_PASS",
        "PURSUIT",
        "RAPID_SPIN",
        "SONICBOOM",
        "UNUSED_83",
        "MORNING_SUN",
        "SYNTHESIS",
        "MOONLIGHT",
        "HIDDEN_POWER",
        "RAIN_DANCE",
        "SUNNY_DAY",
        "DEFENSE_UP_HIT",
        "ATTACK_UP_HIT",
        "ALL_STATS_UP_HIT",
        "???",
        "BELLY_DRUM",
        "PSYCH_UP",
        "MIRROR_COAT",
        "SKULL_BASH",
        "TWISTER",
        "EARTHQUAKE",
        "FUTURE_SIGHT",
        "GUST",
        "FLINCH_MINIMIZE_HIT",
        "SOLAR_BEAM",
        "THUNDER",
        "TELEPORT",
        "BEAT_UP",
        "SEMI_INVULNERABLE",
        "DEFENSE_CURL",
        "SOFTBOILED",
        "FAKE_OUT",
        "UPROAR",
        "STOCKPILE",
        "SPIT_UP",
        "SWALLOW",
        "UNUSED_A3",
        "HAIL",
        "TORMENT",
        "FLATTER",
        "WILL_O_WISP",
        "MEMENTO",
        "FACADE",
        "FOCUS_PUNCH",
        "SMELLINGSALT",
        "FOLLOW_ME",
        "NATURE_POWER",
        "CHARGE",
        "TAUNT",
        "HELPING_HAND",
        "TRICK",
        "ROLE_PLAY",
        "WISH",
        "ASSIST",
        "INGRAIN",
        "SUPERPOWER",
        "MAGIC_COAT",
        "RECYCLE",
        "REVENGE",
        "BRICK_BREAK",
        "YAWN",
        "KNOCK_OFF",
        "ENDEAVOR",
        "ERUPTION",
        "SKILL_SWAP",
        "IMPRISON",
        "REFRESH",
        "GRUDGE",
        "SNATCH",
        "LOW_KICK",
        "SECRET_POWER",
        "DOUBLE_EDGE",
        "TEETER_DANCE",
        "BLAZE_KICK",
        "MUD_SPORT",
        "POISON_FANG",
        "WEATHER_BALL",
        "OVERHEAT",
        "TICKLE",
        "COSMIC_POWER",
        "SKY_UPPERCUT",
        "BULK_UP",
        "POISON_TAIL",
        "WATER_SPORT",
        "CALM_MIND",
        "DRAGON_DANCE",
        "CAMOUFLAGE",
    ]
    target_map = {
        0x00: "SELECTED",
        0x01: "DEPENDS",
        0x02: "USER_OR_SELECTED",
        0x04: "RANDOM",
        0x08: "BOTH",
        0x10: "USER",
        0x20: "FOES_AND_ALLY",
        0x40: "OPPONENTS_FIELD",
    }

    with open(english_rom.file, "rb") as english_file:
        tm_hm_move_map = get_tm_hm_move_map(english_file)

        english_file.seek(get_address("gBattleMoves"))
        for i in range(355):
            move_data = english_file.read(12)

            accuracy = 1 if move_data[3] == 0 else move_data[3] / 100
            secondary_accuracy = 1 if move_data[5] == 0 else move_data[5] / 100

            tm_hm = None
            for item_name in tm_hm_move_map:
                if tm_hm_move_map[item_name] == i:
                    tm_hm = item_name

            moves_list.append(
                {
                    "name": "",
                    "effect": effect_map[move_data[0]],
                    "base_power": move_data[1],
                    "type": types_list[move_data[2]]["name"],
                    "accuracy": accuracy,
                    "pp": move_data[4],
                    "secondary_accuracy": secondary_accuracy,
                    "target": target_map[move_data[6]],
                    "priority": move_data[7] if move_data[7] < 0x80 else -1 * (256 - move_data[7]),
                    "makes_contact": move_data[8] & 0x01 != 0,
                    "affected_by_protect": move_data[8] & 0x02 != 0,
                    "affected_by_magic_coat": move_data[8] & 0x04 != 0,
                    "affected_by_snatch": move_data[8] & 0x08 != 0,
                    "usable_with_mirror_move": move_data[8] & 0x10 != 0,
                    "affected_by_kings_rock": move_data[8] & 0x20 != 0,
                    "tm_hm": tm_hm,
                    "localised_names": initialise_localised_string(),
                    "localised_descriptions": initialise_localised_string(),
                }
            )

        english_file.seek(get_address("gMoveNames"))
        for i in range(355):
            moves_list[i]["name"] = string.capwords(read_string(english_file))

    for language_code in "DEFIJS":
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, "rb") as localised_file:
            set_rom(localised_rom)

            length_of_name = 8 if language_code == "J" else 13
            localised_file.seek(get_address("gMoveNames"))
            for i in range(355):
                moves_list[i]["localised_names"][language_code] = decode_string(localised_file.read(length_of_name))

            localised_file.seek(get_address("gMoveDescriptionPointers"))
            for i in range(1, 355):
                description_pointer = int.from_bytes(localised_file.read(4), byteorder="little") - 0x0800_0000
                moves_list[i]["localised_descriptions"][language_code] = read_string(
                    localised_file, description_pointer
                )

    return moves_list


def extract_species(
    english_rom: ROM,
    localised_roms: dict[str, ROM],
    other_editions_roms: dict[str, ROM],
    type_list: list[dict],
    ability_list: list[dict],
    item_list: list[dict],
) -> list[dict]:
    set_rom(english_rom)
    species_list = []

    egg_group_map = [
        "???",
        "Monster",
        "Water 1",
        "Bug",
        "Flying",
        "Field",
        "Fairy",
        "Grass",
        "Human-Like",
        "Water 3",
        "Mineral",
        "Amorphous",
        "Water 2",
        "Ditto",
        "Dragon",
        "No Eggs",
    ]
    level_up_type_map = ["Medium Fast", "Erratic", "Fluctuating", "Medium Slow", "Fast", "Slow"]

    with open(english_rom.file, "rb") as english_file:
        english_file.seek(get_address("gTMHMLearnsets"))
        tm_hm_learnsets = english_file.read(0xCE0)
        tm_hm_move_map = get_tm_hm_move_map(english_file)

        english_file.seek(get_address("gLevelUpLearnsets"))
        level_up_learnsets = english_file.read(0x670)

        english_file.seek(get_address("gTutorMoves"))
        tutor_moves_list = english_file.read(0x3C)
        tutor_moves_map = []
        for index in range(30):
            tutor_moves_map.append(int.from_bytes(tutor_moves_list[index * 2 : (index + 1) * 2], byteorder="little"))

        english_file.seek(get_address("sTutorLearnsets"))
        tutor_learnsets = english_file.read(0x670)

        english_file.seek(get_address("gEggMoves"))
        egg_moves_data = english_file.read(0x8E6)

        for i in range(412):
            name = string.capwords(read_string(english_file, get_address("gSpeciesNames") + (i * 11)))
            if name == "Ho-oh":
                name = "Ho-Oh"

            english_file.seek(get_address("sSpeciesToNationalPokedexNum") + (i * 2 - 2))
            national_dex_number = int.from_bytes(english_file.read(2), byteorder="little")

            english_file.seek(get_address("sSpeciesToHoennPokedexNum") + (i * 2 - 2))
            hoenn_dex_number = int.from_bytes(english_file.read(2), byteorder="little")

            english_file.seek(get_address("gSpeciesInfo") + (i * 28))
            info = english_file.read(28)

            abilities = [ability_list[info[22]]["name"]]
            if info[23]:
                abilities.append(ability_list[info[23]]["name"])

            item1 = int.from_bytes(info[12:14], byteorder="little")
            item2 = int.from_bytes(info[14:16], byteorder="little")
            if item1 == 0:
                held_items = []
            elif item1 == item2:
                held_items = [(item_list[item1]["name"], 1)]
            elif item2 == 0:
                held_items = [(item_list[item1]["name"], 0.5)]
            else:
                held_items = [(item_list[item1]["name"], 0.5), (item_list[item2]["name"], 0.05)]

            level_up_moves = {}
            offset = 0
            level_up_learnset_pointer = int.from_bytes(level_up_learnsets[i * 4 : (i + 1) * 4], byteorder="little")
            english_file.seek(level_up_learnset_pointer - 0x0800_0000)
            level_up_learnset = english_file.read(0xFF)
            while offset < 100:
                move_info = int.from_bytes(level_up_learnset[offset : offset + 2], byteorder="little")
                if move_info == 0xFFFF:
                    break

                move_id = 0x1FF & move_info
                level = move_info >> 9
                level_up_moves[move_id] = level
                offset += 2

            tm_hm_moves = []
            tm_hm_bitfield = tm_hm_learnsets[i * 8 : (i + 1) * 8]
            for index in range(58):
                byte = index // 8
                bit = index % 8
                if tm_hm_bitfield[byte] & (1 << bit):
                    if index >= 50:
                        item_name = f"HM{index - 49:02d}"
                    else:
                        item_name = f"TM{index + 1:02d}"

                    tm_hm_moves.append(tm_hm_move_map[item_name])

            egg_moves = []
            offset = 0
            in_correct_block = False
            while offset < 0x8E6:
                entry = int.from_bytes(egg_moves_data[offset : offset + 2], byteorder="little")
                if entry >= 20000:
                    if in_correct_block:
                        break
                    elif entry == 20000 + i:
                        in_correct_block = True
                elif in_correct_block:
                    egg_moves.append(entry)
                offset += 2

            tutor_moves = []
            tutor_moves_bitfield = int.from_bytes(tutor_learnsets[i * 4 : (i + 1) * 4], byteorder="little")
            for index in range(30):
                if tutor_moves_bitfield & (1 << index):
                    tutor_moves.append(tutor_moves_map[index])

            species_list.append(
                {
                    "name": name,
                    "national_dex_number": national_dex_number,
                    "hoenn_dex_number": hoenn_dex_number,
                    "types": list(sorted({type_list[info[6]]["name"], type_list[info[7]]["name"]})),
                    "abilities": abilities,
                    "held_items": held_items,
                    "base_stats": {
                        "hp": info[0],
                        "attack": info[1],
                        "defence": info[2],
                        "speed": info[3],
                        "special_attack": info[4],
                        "special_defence": info[5],
                    },
                    "gender_ratio": info[16],
                    "egg_cycles": info[17],
                    "base_friendship": info[18],
                    "catch_rate": info[8],
                    "safari_zone_flee_probability": info[24],
                    "level_up_type": level_up_type_map[info[19]],
                    "egg_groups": list(sorted({egg_group_map[info[20]], egg_group_map[info[21]]})),
                    "base_experience_yield": info[9],
                    "ev_yield": {
                        "hp": (info[10] & 0b00000011) >> 0,
                        "attack": (info[10] & 0b00001100) >> 2,
                        "defence": (info[10] & 0b00110000) >> 4,
                        "speed": (info[10] & 0b11000000) >> 6,
                        "special_attack": (info[11] & 0b00000011) >> 0,
                        "special_defence": (info[11] & 0b00001100) >> 2,
                    },
                    "learnset": {
                        "level_up": level_up_moves,
                        "tm_hm": tm_hm_moves,
                        "tutor": tutor_moves,
                        "egg": egg_moves,
                    },
                    "localised_names": initialise_localised_string(),
                }
            )

    for language_code in "DEFIJS":
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, "rb") as localised_file:
            set_rom(localised_rom)

            length_of_name = 6 if language_code == "J" else 11
            localised_file.seek(get_address("gSpeciesNames"))
            for i in range(412):
                species_list[i]["localised_names"][language_code] = decode_string(localised_file.read(length_of_name))

    for edition_code in ("RUBY", "SAPP", "FIRE", "LEAF"):
        edition_rom = other_editions_roms[edition_code]
        with open(edition_rom.file, "rb") as edition_file:
            set_rom(edition_rom)
            for i in range(412):
                if edition_code in ("RUBY", "SAPP"):
                    edition_file.seek(get_address("gBaseStats") + (i * 28))
                else:
                    edition_file.seek(get_address("gSpeciesInfo") + (i * 28))
                info = edition_file.read(28)

                species_list[i]["catch_rate"] = max(species_list[i]["catch_rate"], info[8])
                species_list[i]["safari_zone_flee_probability"] = max(
                    species_list[i]["safari_zone_flee_probability"], info[24]
                )

    return species_list


if __name__ == "__main__":
    english_rom, localised_roms, other_editions_roms = find_roms()

    extracted_data = {
        "items": extract_items(english_rom, localised_roms),
        "abilities": extract_abilities(english_rom, localised_roms),
        "types": extract_types(english_rom, localised_roms),
        "natures": extract_natures(english_rom, localised_roms),
    }
    extracted_data["moves"] = extract_moves(english_rom, localised_roms, extracted_data["types"])
    extracted_data["species"] = extract_species(
        english_rom,
        localised_roms,
        other_editions_roms,
        extracted_data["types"],
        extracted_data["abilities"],
        extracted_data["items"],
    )
    for key in extracted_data:
        file_path = Path(__file__).parent / f"{key}.json"
        print(f"Writing {str(file_path)}...")
        with open(file_path, "w") as file:
            json.dump(extracted_data[key], file, indent=4)
            file.write("\n")

    print("✅ Done!")
