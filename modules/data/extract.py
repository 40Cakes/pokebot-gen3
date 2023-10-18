import json
import os
import string
import sys
from pathlib import Path
from typing import IO

sys.path.append(str(Path(__file__).parent.parent.parent))

from modules.Game import SetROM, DecodeString, GetSymbol
from modules.Roms import ListAvailableRoms, ROMLanguage, ROM


def FindROMs() -> tuple[ROM, dict[str, ROM]]:
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

    for rom in ListAvailableRoms():
        if rom.game_title != 'POKEMON EMER' or rom.revision != 0:
            continue

        if rom.language == ROMLanguage.English and english_rom is None:
            english_rom = rom

        if not str(rom.language) in matched_languages:
            matched_languages.add(str(rom.language))
            language_roms[str(rom.language)] = rom

    if english_rom is None:
        raise Exception("Could not find an English Emerald (rev 0) ROM.")

    if len(language_roms) != 6:
        raise Exception(
            "Could not find all languages of Emerald (rev 0). Languages found: " + (', '.join(language_roms.keys())))

    return english_rom, language_roms


def InitialiseLocalisedString() -> dict[str, str]:
    """
    Sets up the default dict structure for translatable strings.
    :return: Dict that maps each language code to an empty string
    """
    return {'D': '', 'E': '', 'F': '', 'I': '', 'J': '', 'S': ''}


def GetAddress(symbol_name: str) -> int:
    """
    The GBA maps the ROM to memory location 0x0800_0000, so the symbol table
    references addresses in that range. Since we are working with the actual
    ROM file here, that 0x0800_0000 must be subtracted from any address.
    :param symbol_name: Name of the symbol to look up
    :return: The offset from the start of the ROM
    """
    return GetSymbol(symbol_name)[0] - 0x0800_0000


def ReadString(file: IO, offset: int = -1) -> str:
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
    buffer = b''
    while file.tell() < file_size - 1:
        byte = file.read(1)
        if byte == b'\xFF':
            break
        else:
            buffer += byte
    if offset >= 0:
        file.seek(previous_position, os.SEEK_SET)
    return DecodeString(buffer)


def ExtractItems(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    item_list = []
    type_map = ['mail', 'usable_outside_battle', 'usable_in_certain_locations', 'pokeblock_case',
                'not_usable_outside_battle']
    pocket_map = ['???', 'items', 'poke_balls', 'tms_and_hms', 'berries', 'key_items']

    SetROM(english_rom)
    offset = GetAddress('gItems')

    with open(english_rom.file, 'rb') as english_file:
        for i in range(377):
            english_file.seek(offset + (i * 44))
            item_data = english_file.read(44)

            name = DecodeString(item_data[0:14])
            pretty_name = string.capwords(name)
            if pretty_name.startswith(('Tm', 'Hm', 'Pp', 'Hp', 'Vs')):
                pretty_name = pretty_name[0:2].upper() + pretty_name[2:]
            if pretty_name.startswith('S.s.'):
                pretty_name = 'S.S.' + pretty_name[4:]

            pocket = int.from_bytes(item_data[26:27], byteorder='little')

            # Poke Balls use the 'item type' field to indicate the Poke Ball type instead.
            if pocket == 2:
                item_type = int.from_bytes(item_data[27:28], byteorder='little')
            else:
                item_type = type_map[int.from_bytes(item_data[27:28], byteorder='little')]

            item_entry = {
                'index': int.from_bytes(item_data[14:16], byteorder='little'),
                'name': pretty_name,
                'price': int.from_bytes(item_data[16:18], byteorder='little'),
                'type': item_type,
                'pocket': pocket_map[pocket],
                'parameter': int.from_bytes(item_data[19:20], byteorder='little'),
                'extra_parameter': int.from_bytes(item_data[40:44], byteorder='little'),
                'localised_names': InitialiseLocalisedString(),
                'localised_descriptions': InitialiseLocalisedString(),
            }

            item_list.append(item_entry)

    for language_code in 'DEFIJS':
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, 'rb') as localised_file:
            SetROM(localised_rom)

            if language_code == 'J':
                length_of_item = 40
                length_of_name = 10
                description_pointer_offset = 16
            else:
                length_of_item = 44
                length_of_name = 14
                description_pointer_offset = 20

            offset = GetAddress('gItems')
            localised_file.seek(offset, os.SEEK_SET)

            for i in range(377):
                item_data = localised_file.read(length_of_item)
                name = DecodeString(item_data[0:length_of_name])

                description_pointer = int.from_bytes(
                    item_data[description_pointer_offset:description_pointer_offset + 4],
                    byteorder='little')
                description = ReadString(localised_file, description_pointer - 0x0800_0000)

                item_list[i]['localised_names'][language_code] = name
                item_list[i]['localised_descriptions'][language_code] = description

        return item_list


def ExtractAbilities(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    abilities_list = []

    SetROM(english_rom)
    offset = GetAddress('gAbilityNames')

    with open(english_rom.file, 'rb') as english_file:
        for i in range(78):
            abilities_list.append({
                'name': string.capwords(ReadString(english_file, offset + (i * 13))),
                'localised_names': InitialiseLocalisedString(),
                'localised_descriptions': InitialiseLocalisedString(),
            })

    for language_code in 'DEFIJS':
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, 'rb') as localised_file:
            SetROM(localised_rom)

            offset = GetAddress('gAbilityNames')
            for i in range(78):
                if language_code == 'J':
                    name = ReadString(localised_file, offset + (i * 8))
                else:
                    name = ReadString(localised_file, offset + (i * 13))
                abilities_list[i]['localised_names'][language_code] = name

            end_of_strings_found = 0
            while end_of_strings_found <= 78:
                offset -= 1
                localised_file.seek(offset, os.SEEK_SET)
                if localised_file.read(1) == b'\xFF':
                    end_of_strings_found += 1

            for i in range(78):
                abilities_list[i]['localised_descriptions'][language_code] = ReadString(localised_file)

    return abilities_list


def ExtractTypes(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    types_list = []

    SetROM(english_rom)
    with open(english_rom.file, 'rb') as english_file:
        offset = GetAddress('gTypeNames')
        for i in range(18):
            name = string.capwords(ReadString(english_file, offset + (i * 7)))
            if name == 'Electr':
                name = 'Electric'
            elif name == 'Psychc':
                name = 'Psychic'
            types_list.append({
                'name': name,
                'effectiveness': {},
                'localised_names': InitialiseLocalisedString(),
            })

        english_file.seek(GetAddress('gTypeEffectiveness'))
        for i in range(112):
            data = english_file.read(3)
            if data[0] < 18:
                types_list[data[0]]['effectiveness'][types_list[data[1]]['name']] = data[2] / 10

    for language_code in 'DEFIJS':
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, 'rb') as localised_file:
            SetROM(localised_rom)

            localised_file.seek(GetAddress('gTypeNames'))
            for i in range(18):
                if language_code == 'J':
                    name_length = 5
                else:
                    name_length = 7
                types_list[i]['localised_names'][language_code] = DecodeString(localised_file.read(name_length))

    return types_list


def ExtractNatures(english_rom: ROM, localised_roms: dict[str, ROM]) -> list[dict]:
    natures_list = []

    SetROM(english_rom)
    with open(english_rom.file, 'rb') as english_file:
        english_file.seek(GetAddress('sHardyNatureName'))
        for i in range(25):
            natures_list.append({
                'name': string.capwords(ReadString(english_file)),
                'localised_names': InitialiseLocalisedString(),
            })

        english_file.seek(GetAddress('gNatureStatTable'))
        for i in range(25):
            modifiers = english_file.read(5)
            stats_list = ['attack', 'defence', 'speed', 'special_attack', 'special_defence']
            for j in range(len(stats_list)):
                key = f'{stats_list[j]}_modifier'
                if modifiers[j] == 0:
                    natures_list[i][key] = 1
                elif modifiers[j] == 1:
                    natures_list[i][key] = 1.1
                else:
                    natures_list[i][key] = 0.9

    for language_code in 'DEFIJS':
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, 'rb') as localised_file:
            SetROM(localised_rom)

            localised_file.seek(GetAddress('sHardyNatureName'))
            for i in range(25):
                natures_list[i]['localised_names'][language_code] = ReadString(localised_file)

    return natures_list


def ExtractMoves(english_rom: ROM, localised_roms: dict[str, ROM], types_list: list[dict]) -> list[dict]:
    SetROM(english_rom)

    moves_list = []
    # Names taken verbatim from the decompilation project; nothing official
    effect_map = ['HIT', 'SLEEP', 'POISON_HIT', 'ABSORB', 'BURN_HIT', 'FREEZE_HIT', 'PARALYZE_HIT', 'EXPLOSION',
                  'DREAM_EATER', 'MIRROR_MOVE', 'ATTACK_UP', 'DEFENSE_UP', 'SPEED_UP', 'SPECIAL_ATTACK_UP',
                  'SPECIAL_DEFENSE_UP', 'ACCURACY_UP', 'EVASION_UP', 'ALWAYS_HIT', 'ATTACK_DOWN', 'DEFENSE_DOWN',
                  'SPEED_DOWN', 'SPECIAL_ATTACK_DOWN', 'SPECIAL_DEFENSE_DOWN', 'ACCURACY_DOWN', 'EVASION_DOWN', 'HAZE',
                  'BIDE', 'RAMPAGE', 'ROAR', 'MULTI_HIT', 'CONVERSION', 'FLINCH_HIT', 'RESTORE_HP', 'TOXIC', 'PAY_DAY',
                  'LIGHT_SCREEN', 'TRI_ATTACK', 'REST', 'OHKO', 'RAZOR_WIND', 'SUPER_FANG', 'DRAGON_RAGE', 'TRAP',
                  'HIGH_CRITICAL', 'DOUBLE_HIT', 'RECOIL_IF_MISS', 'MIST', 'FOCUS_ENERGY', 'RECOIL', 'CONFUSE',
                  'ATTACK_UP_2', 'DEFENSE_UP_2', 'SPEED_UP_2', 'SPECIAL_ATTACK_UP_2', 'SPECIAL_DEFENSE_UP_2',
                  'ACCURACY_UP_2', 'EVASION_UP_2', 'TRANSFORM', 'ATTACK_DOWN_2', 'DEFENSE_DOWN_2', 'SPEED_DOWN_2',
                  'SPECIAL_ATTACK_DOWN_2', 'SPECIAL_DEFENSE_DOWN_2', 'ACCURACY_DOWN_2', 'EVASION_DOWN_2', 'REFLECT',
                  'POISON', 'PARALYZE', 'ATTACK_DOWN_HIT', 'DEFENSE_DOWN_HIT', 'SPEED_DOWN_HIT',
                  'SPECIAL_ATTACK_DOWN_HIT', 'SPECIAL_DEFENSE_DOWN_HIT', 'ACCURACY_DOWN_HIT', 'EVASION_DOWN_HIT',
                  'SKY_ATTACK', 'CONFUSE_HIT', 'TWINEEDLE', 'VITAL_THROW', 'SUBSTITUTE', 'RECHARGE', 'RAGE', 'MIMIC',
                  'METRONOME', 'LEECH_SEED', 'SPLASH', 'DISABLE', 'LEVEL_DAMAGE', 'PSYWAVE', 'COUNTER', 'ENCORE',
                  'PAIN_SPLIT', 'SNORE', 'CONVERSION_2', 'LOCK_ON', 'SKETCH', '???', 'SLEEP_TALK', 'DESTINY_BOND',
                  'FLAIL', 'SPITE', 'FALSE_SWIPE', 'HEAL_BELL', 'QUICK_ATTACK', 'TRIPLE_KICK', 'THIEF', 'MEAN_LOOK',
                  'NIGHTMARE', 'MINIMIZE', 'CURSE', 'UNUSED_6E', 'PROTECT', 'SPIKES', 'FORESIGHT', 'PERISH_SONG',
                  'SANDSTORM', 'ENDURE', 'ROLLOUT', 'SWAGGER', 'FURY_CUTTER', 'ATTRACT', 'RETURN', 'PRESENT',
                  'FRUSTRATION', 'SAFEGUARD', 'THAW_HIT', 'MAGNITUDE', 'BATON_PASS', 'PURSUIT', 'RAPID_SPIN',
                  'SONICBOOM', 'UNUSED_83', 'MORNING_SUN', 'SYNTHESIS', 'MOONLIGHT', 'HIDDEN_POWER', 'RAIN_DANCE',
                  'SUNNY_DAY', 'DEFENSE_UP_HIT', 'ATTACK_UP_HIT', 'ALL_STATS_UP_HIT', '???', 'BELLY_DRUM', 'PSYCH_UP',
                  'MIRROR_COAT', 'SKULL_BASH', 'TWISTER', 'EARTHQUAKE', 'FUTURE_SIGHT', 'GUST', 'FLINCH_MINIMIZE_HIT',
                  'SOLAR_BEAM', 'THUNDER', 'TELEPORT', 'BEAT_UP', 'SEMI_INVULNERABLE', 'DEFENSE_CURL', 'SOFTBOILED',
                  'FAKE_OUT', 'UPROAR', 'STOCKPILE', 'SPIT_UP', 'SWALLOW', 'UNUSED_A3', 'HAIL', 'TORMENT', 'FLATTER',
                  'WILL_O_WISP', 'MEMENTO', 'FACADE', 'FOCUS_PUNCH', 'SMELLINGSALT', 'FOLLOW_ME', 'NATURE_POWER',
                  'CHARGE', 'TAUNT', 'HELPING_HAND', 'TRICK', 'ROLE_PLAY', 'WISH', 'ASSIST', 'INGRAIN', 'SUPERPOWER',
                  'MAGIC_COAT', 'RECYCLE', 'REVENGE', 'BRICK_BREAK', 'YAWN', 'KNOCK_OFF', 'ENDEAVOR', 'ERUPTION',
                  'SKILL_SWAP', 'IMPRISON', 'REFRESH', 'GRUDGE', 'SNATCH', 'LOW_KICK', 'SECRET_POWER', 'DOUBLE_EDGE',
                  'TEETER_DANCE', 'BLAZE_KICK', 'MUD_SPORT', 'POISON_FANG', 'WEATHER_BALL', 'OVERHEAT', 'TICKLE',
                  'COSMIC_POWER', 'SKY_UPPERCUT', 'BULK_UP', 'POISON_TAIL', 'WATER_SPORT', 'CALM_MIND', 'DRAGON_DANCE',
                  'CAMOUFLAGE']
    target_map = {0x00: 'SELECTED', 0x01: 'DEPENDS', 0x02: 'USER_OR_SELECTED', 0x04: 'RANDOM', 0x08: 'BOTH',
                  0x10: 'USER', 0x20: 'FOES_AND_ALLY', 0x40: 'OPPONENTS_FIELD'}

    with open(english_rom.file, 'rb') as english_file:
        english_file.seek(GetAddress('gBattleMoves'))
        for i in range(355):
            move_data = english_file.read(12)

            if move_data[3] == 0:
                accuracy = 1
            else:
                accuracy = move_data[3] / 100

            if move_data[5] == 0:
                secondary_accuracy = 1
            else:
                secondary_accuracy = move_data[5] / 100

            moves_list.append({
                'name': '',
                'effect': effect_map[move_data[0]],
                'base_power': move_data[1],
                'type': types_list[move_data[2]]['name'],
                'accuracy': accuracy,
                'pp': move_data[4],
                'secondary_accuracy': secondary_accuracy,
                'target': target_map[move_data[6]],
                'priority': move_data[7] if move_data[7] < 0x80 else -1 * (256 - move_data[7]),
                'makes_contact': move_data[8] & 0x01 != 0,
                'affected_by_protect': move_data[8] & 0x02 != 0,
                'affected_by_magic_coat': move_data[8] & 0x04 != 0,
                'affected_by_snatch': move_data[8] & 0x08 != 0,
                'usable_with_mirror_move': move_data[8] & 0x10 != 0,
                'affected_by_kings_rock': move_data[8] & 0x20 != 0,
                'localised_names': InitialiseLocalisedString(),
                'localised_descriptions': InitialiseLocalisedString(),
            })

        english_file.seek(GetAddress('gMoveNames'))
        for i in range(355):
            moves_list[i]['name'] = string.capwords(ReadString(english_file))

    for language_code in 'DEFIJS':
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, 'rb') as localised_file:
            SetROM(localised_rom)

            if language_code == 'J':
                length_of_name = 8
            else:
                length_of_name = 13

            localised_file.seek(GetAddress('gMoveNames'))
            for i in range(355):
                moves_list[i]['localised_names'][language_code] = DecodeString(localised_file.read(length_of_name))

            localised_file.seek(GetAddress('gMoveDescriptionPointers'))
            for i in range(1, 355):
                description_pointer = int.from_bytes(localised_file.read(4), byteorder='little') - 0x0800_0000
                moves_list[i]['localised_descriptions'][language_code] = ReadString(localised_file, description_pointer)

    return moves_list


def ExtractSpecies(english_rom: ROM, localised_roms: dict[str, ROM], type_list: list[dict], ability_list: list[dict],
                   item_list: list[dict]) -> list[dict]:
    SetROM(english_rom)
    species_list = []

    egg_group_map = ['???', 'Monster', 'Water 1', 'Bug', 'Flying', 'Field', 'Fairy', 'Grass', 'Human-Like', 'Water 3',
                     'Mineral', 'Amorphous', 'Water 2', 'Ditto', 'Dragon', 'No Eggs']
    level_up_type_map = ['Medium Fast', 'Erratic', 'Fluctuating', 'Medium Slow', 'Fast', 'Slow']

    with open(english_rom.file, 'rb') as english_file:
        for i in range(412):
            name = string.capwords(ReadString(english_file, GetAddress('gSpeciesNames') + (i * 11)))
            if name == 'Ho-oh':
                name = 'Ho-Oh'

            english_file.seek(GetAddress('sSpeciesToNationalPokedexNum') + (i * 2 - 2))
            national_dex_number = int.from_bytes(english_file.read(2), byteorder='little')

            english_file.seek(GetAddress('sSpeciesToHoennPokedexNum') + (i * 2 - 2))
            hoenn_dex_number = int.from_bytes(english_file.read(2), byteorder='little')

            english_file.seek(GetAddress('gSpeciesInfo') + (i * 28))
            info = english_file.read(28)

            abilities = [ability_list[info[22]]['name']]
            if info[23]:
                abilities.append(ability_list[info[23]]['name'])

            item1 = int.from_bytes(info[12:14], byteorder='little')
            item2 = int.from_bytes(info[14:16], byteorder='little')
            if item1 == 0:
                held_items = []
            elif item1 == item2:
                held_items = [(item_list[item1]['name'], 1)]
            elif item2 == 0:
                held_items = [(item_list[item1]['name'], 0.5)]
            else:
                held_items = [(item_list[item1]['name'], 0.5), (item_list[item2]['name'], 0.05)]

            species_list.append({
                'name': name,
                'national_dex_number': national_dex_number,
                'hoenn_dex_number': hoenn_dex_number,
                'types': list({type_list[info[6]]['name'], type_list[info[7]]['name']}),
                'abilities': abilities,
                'held_items': held_items,
                'base_stats': {
                    'hp': info[0],
                    'attack': info[1],
                    'defence': info[2],
                    'speed': info[3],
                    'special_attack': info[4],
                    'special_defence': info[5]
                },
                'gender_ratio': info[16],
                'egg_cycles': info[17],
                'base_friendship': info[18],
                'catch_rate': info[6],
                'safari_zone_flee_probability': info[24],
                'level_up_type': level_up_type_map[info[19]],
                'egg_groups': list({egg_group_map[info[20]], egg_group_map[info[21]]}),
                'base_experience_yield': info[9],
                'ev_yield': {
                    'hp': (info[10] & 0b00000011) >> 0,
                    'attack': (info[10] & 0b00001100) >> 2,
                    'defence': (info[10] & 0b00110000) >> 4,
                    'speed': (info[10] & 0b11000000) >> 6,
                    'special_attack': (info[11] & 0b00000011) >> 0,
                    'special_defence': (info[11] & 0b00001100) >> 2,
                },
                'localised_names': InitialiseLocalisedString()
            })

    for language_code in 'DEFIJS':
        localised_rom = localised_roms[language_code]
        with open(localised_rom.file, 'rb') as localised_file:
            SetROM(localised_rom)

            if language_code == 'J':
                length_of_name = 6
            else:
                length_of_name = 11

            localised_file.seek(GetAddress('gSpeciesNames'))
            for i in range(412):
                species_list[i]['localised_names'][language_code] = DecodeString(localised_file.read(length_of_name))

    return species_list


if __name__ == '__main__':
    english_rom, localised_roms = FindROMs()

    extracted_data = {}
    extracted_data['items'] = ExtractItems(english_rom, localised_roms)
    extracted_data['abilities'] = ExtractAbilities(english_rom, localised_roms)
    extracted_data['types'] = ExtractTypes(english_rom, localised_roms)
    extracted_data['natures'] = ExtractNatures(english_rom, localised_roms)
    extracted_data['moves'] = ExtractMoves(english_rom, localised_roms, extracted_data['types'])
    extracted_data['species'] = ExtractSpecies(english_rom, localised_roms, extracted_data['types'],
                                               extracted_data['abilities'], extracted_data['items'])
    for key in extracted_data:
        file_path = Path(__file__).parent / f'{key}.json'
        print(f'Writing {str(file_path)}...')
        with open(file_path, 'w') as file:
            json.dump(extracted_data[key], file, indent=4)

    print('✅ Done!')
