from dataclasses import dataclass
from typing import Literal

import yaml

from modules.roms import ROM, ROMLanguage
from modules.runtime import get_data_path


@dataclass
class GameData:
    symbols: dict[str, tuple[int, int]]
    reverse_symbols: dict[int, tuple[str, str, int]]
    event_flags: dict[str, tuple[int, int]]
    reverse_event_flags: dict[int, str]
    event_vars: dict[str, int]
    reverse_event_vars: dict[int, str]
    character_table: list[str]


_loaded_game_data: dict[str, GameData] = {}
_character_table_international: list[str] = []
_character_table_japanese: list[str] = []

_current_game_data: GameData = GameData({}, {}, {}, {}, {}, {}, [])


def get_game_data(rom: ROM) -> GameData:
    global _loaded_game_data

    if rom.id in _loaded_game_data:
        return _loaded_game_data[rom.id]

    if len(_character_table_international) == 0:
        _prepare_character_tables()

    character_table = (
        _character_table_japanese if rom.language is ROMLanguage.Japanese else _character_table_international
    )
    game_data: GameData | None = None
    match rom.game_code:
        case "AXV":
            if rom.language is ROMLanguage.Japanese or (rom.language is ROMLanguage.English and rom.revision == 0):
                game_data = GameData(
                    *_load_symbols("pokeruby.sym", rom.language), *_load_event_flags_and_vars("rs.txt"), character_table
                )
            elif rom.language is ROMLanguage.German:
                game_data = GameData(
                    *_load_symbols("pokeruby_de.sym", rom.language),
                    *_load_event_flags_and_vars("rs.txt"),
                    character_table,
                )
            else:
                game_data = GameData(
                    *_load_symbols("pokeruby_rev1.sym", rom.language),
                    *_load_event_flags_and_vars("rs.txt"),
                    character_table,
                )

        case "AXP":
            if rom.language is ROMLanguage.Japanese or (rom.language is ROMLanguage.English and rom.revision == 0):
                game_data = GameData(
                    *_load_symbols("pokesapphire.sym", rom.language),
                    *_load_event_flags_and_vars("rs.txt"),
                    character_table,
                )
            elif rom.language is ROMLanguage.German:
                game_data = GameData(
                    *_load_symbols("pokesapphire_de.sym", rom.language),
                    *_load_event_flags_and_vars("rs.txt"),
                    character_table,
                )
            else:
                game_data = GameData(
                    *_load_symbols("pokesapphire_rev1.sym", rom.language),
                    *_load_event_flags_and_vars("rs.txt"),
                    character_table,
                )

        case "BPE":
            game_data = GameData(
                *_load_symbols("pokeemerald.sym", rom.language),
                *_load_event_flags_and_vars("emerald.txt"),
                character_table,
            )

        case "BPR":
            match rom.revision:
                case 0:
                    game_data = GameData(
                        *_load_symbols("pokefirered.sym", rom.language),
                        *_load_event_flags_and_vars("frlg.txt"),
                        character_table,
                    )
                case 1:
                    game_data = GameData(
                        *_load_symbols("pokefirered_rev1.sym", rom.language),
                        *_load_event_flags_and_vars("frlg.txt"),
                        character_table,
                    )

        case "BPG":
            match rom.revision:
                case 0:
                    game_data = GameData(
                        *_load_symbols("pokeleafgreen.sym", rom.language),
                        *_load_event_flags_and_vars("frlg.txt"),
                        character_table,
                    )
                case 1:
                    game_data = GameData(
                        *_load_symbols("pokeleafgreen_rev1.sym", rom.language),
                        *_load_event_flags_and_vars("frlg.txt"),
                        character_table,
                    )

    if game_data is None:
        raise RuntimeError("Could not figure out which symbols/event flags/event vars to load for this ROM.")

    _loaded_game_data[rom.id] = game_data

    return game_data


def _load_symbols(
    symbols_file: str, language: ROMLanguage
) -> tuple[dict[str, tuple[int, int]], dict[int, tuple[str, str, int]]]:
    symbols: dict[str, tuple[int, int]] = {}
    reverse_symbols: dict[int, tuple[str, str, int]] = {}

    for d in [get_data_path() / "symbols", get_data_path() / "symbols" / "patches"]:
        with open(d / symbols_file) as f:
            for s in f:
                address, _, length, label = s.split(" ")

                address = int(address, 16)
                length = int(length, 16)
                label = label.strip()

                # This label sometimes appear for the same memory address as others,
                # blocking the names we're actually interested in. Thus, we just
                # ignore those.
                if label == ".gcc2_compiled" or label == ".gcc2_compiled.":
                    continue

                symbols[label.upper()] = (address, length)
                reverse_symbols[address] = (label.upper(), label, length)

    language_code = str(language)
    language_patch_file = symbols_file.replace(".sym", ".yml")
    language_patch_path = get_data_path() / "symbols" / "patches" / "language" / language_patch_file
    if language_code in {"D", "I", "S", "F", "J"} and language_patch_path.is_file():
        with open(language_patch_path, "r") as file:
            language_patches = yaml.safe_load(file)
            for label, addr_mapping in language_patches.items():
                if language_code in addr_mapping:
                    addresses_list = addr_mapping[language_code]

                    if addresses_list is None:
                        continue

                    if isinstance(addresses_list, int):
                        addresses_list = [addresses_list]

                    if label.upper() in symbols:
                        existing_address = symbols[label.upper()][0]
                        if (
                            existing_address in reverse_symbols
                            and reverse_symbols[existing_address][0] == label.upper()
                        ):
                            reverse_symbols.pop(existing_address, None)

                    for addr in addresses_list:
                        if addr is not None:
                            symbols[label.upper()] = (
                                addr,
                                symbols[label.upper()][1] if label.upper() in symbols else 0,
                            )
                            reverse_symbols[addr] = (
                                label.upper(),
                                label,
                                symbols[label.upper()][1] if label.upper() in symbols else 0,
                            )

    return symbols, reverse_symbols


def _load_event_flags_and_vars(
    file_name: str,
) -> tuple[
    dict[str, tuple[int, int]], dict[int, str], dict[str, int], dict[int, str]
]:  # TODO Japanese ROMs not working
    event_flags: dict[str, tuple[int, int]] = {}
    reverse_event_flags: dict[int, str] = {}
    event_vars: dict[str, int] = {}
    reverse_event_vars: dict[int, str] = {}

    match file_name:
        case "rs.txt":
            flags_offset = 0x1220
            vars_offset = 0x1340
        case "emerald.txt":
            flags_offset = 0x1270
            vars_offset = 0x139C
        case "frlg.txt":
            flags_offset = 0x0EE0
            vars_offset = 0x1000
        case _:
            raise RuntimeError("Invalid argument to _load_event_flags_and_vars()")

    with open(get_data_path() / "event_flags" / file_name) as file_handle:
        for s in file_handle:
            number, name = s.strip().split(" ")
            event_flags[name] = (int(number) // 8) + flags_offset, int(number) % 8
            reverse_event_flags[int(number)] = name

    with open(get_data_path() / "event_vars" / file_name) as file_handle:
        for s in file_handle:
            number, name = s.strip().split(" ")
            event_vars[name] = int(number) * 2 + vars_offset
            reverse_event_vars[int(number)] = name

    return event_flags, reverse_event_flags, event_vars, reverse_event_vars


def _prepare_character_tables() -> None:
    global _character_table_international, _character_table_japanese

    _character_table_international.clear()
    _character_table_japanese.clear()

    character_table_japanese = (
        " あいうえおかきくけこさしすせそ"
        "たちつてとなにぬねのはひふへほま"
        "みむめもやゆよらりるれろわをんぁ"
        "ぃぅぇぉゃゅょがぎぐげござじずぜ"
        "ぞだぢづでどばびぶべぼぱぴぷぺぽ"
        "っアイウエオカキクケコサシスセソ"
        "タチツテトナニヌネノハヒフヘホマ"
        "ミムメモヤユヨラリルレロワヲンァ"
        "ィゥェォャュョガギグゲゴザジズゼ"
        "ゾダヂヅデドバビブベボパピプペポ"
        "ッ0123456789！？。ー・"
        " 『』「」♂♀円.×/ABCDE"
        "FGHIJKLMNOPQRSTU"
        "VWXYZabcdefghijk"
        "lmnopqrstuvwxyz▶"
        ":ÄÖÜäöü⬆⬇⬅      "
    )
    for i in character_table_japanese:
        _character_table_japanese.append(i)

    character_table_international = (
        " ÀÁÂÇÈÉÊËÌ ÎÏÒÓÔ"
        + "ŒÙÚÛÑßàá çèéêëì "
        + "îïòóôœùúûñºªᵉ&+ "
        + "    L=;         "
        + "                "
        + "▯¿¡       Í%()  "
        + "        â      í"
        + "         ⬆⬇⬅➡***"
        + "****ᵉ<>         "
        + "                "
        + " 0123456789!?.-・"
        + "…“”‘’♂♀$,×/ABCDE"
        + "FGHIJKLMNOPQRSTU"
        + "VWXYZabcdefghijk"
        + "lmnopqrstuvwxyz▶"
        + ":ÄÖÜäöü         "
    )

    for i in character_table_international:
        _character_table_international.append(i)
    _character_table_international[0x34] = "Lv"
    _character_table_international[0x53] = "Pk"
    _character_table_international[0x54] = "Mn"
    _character_table_international[0x55] = "Po"
    _character_table_international[0x56] = "Ké"
    _character_table_international[0x57] = "BL"
    _character_table_international[0x58] = "OC"
    _character_table_international[0x59] = "K"
    _character_table_international[0xA0] = "re"


def set_rom(rom: ROM) -> None:
    global _current_game_data
    _current_game_data = get_game_data(rom)


def get_current_game_data() -> GameData:
    return _current_game_data


def get_symbol(symbol_name: str) -> tuple[int, int]:
    canonical_name = symbol_name.strip().upper()
    if canonical_name not in _current_game_data.symbols:
        raise RuntimeError(f"Unknown symbol: {symbol_name}!")

    return _current_game_data.symbols[canonical_name]


def get_symbol_name(address: int, pretty_name: bool = False) -> str:
    """
    Get the name of a symbol based on the address

    :param address: address of the symbol
    :param pretty_name: Whether to return the symbol name all-uppercase (False) or
                        with 'natural' case (True)

    :return: name of the symbol (str)
    """
    return _current_game_data.reverse_symbols.get(address, ("", "", 0))[(1 if pretty_name else 0)]


def get_symbol_name_before(address: int, pretty_name: bool = False) -> str:
    """
    Looks up the name of the symbol that comes at or before a memory address (i.e.
    the name of the symbol that this address supposedly belongs to.)

    :param address: Address to look up
    :param pretty_name: Whether to return the symbol name all-uppercase (False) or
                        with 'natural' case (True)
    :return: name of the symbol (str)
    """
    maximum_lookahead = 1024
    return next(
        (
            _current_game_data.reverse_symbols[address - lookahead][(1 if pretty_name else 0)]
            for lookahead in range(maximum_lookahead)
            if address - lookahead in _current_game_data.reverse_symbols
        ),
        hex(address),
    )


def event_flag_exists(flag_name: str) -> bool:
    return flag_name in _current_game_data.event_flags


def get_event_flag_offset(flag_name: str) -> tuple[int, int]:
    return _current_game_data.event_flags[flag_name]


def get_event_flag_name(flag_number: int) -> str:
    if flag_number == 0:
        return ""
    return _current_game_data.reverse_event_flags.get(flag_number, str(flag_number))


def event_var_exists(flag_name: str) -> bool:
    return flag_name in _current_game_data.event_vars


def get_event_var_offset(var_name: str) -> int:
    return _current_game_data.event_vars[var_name]


def get_event_var_name(var_number: int) -> str:
    return _current_game_data.reverse_event_vars.get(var_number, str(var_number))


def decode_string(
    encoded_string: bytes,
    replace_newline: bool = True,
    character_set: Literal["international", "japanese", "rom_default"] = "rom_default",
) -> str:
    """
    Generation III Pokémon games use a proprietary character encoding to store text data.
    The Generation III encoding is greatly different from the encodings used in previous generations, with characters
    corresponding to different bytes.
    See for more information:  https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)

    :param encoded_string: bytes to decode to string
    :param replace_newline: Whether a newline should be returned as such (False), or substituted with a space (True)
    :param character_set: Which character set should be used for decoding; defaults to the ROM language
    :return: decoded bytes (string)
    """
    if character_set == "rom_default":
        character_table = _current_game_data.character_table
    elif character_set == "international":
        character_table = _character_table_international
    elif character_set == "japanese":
        character_table = _character_table_japanese
    else:
        raise RuntimeError(f"Invalid value for character set: '{character_set}'.")

    string = ""
    cursor = 0
    while cursor < len(encoded_string):
        i = encoded_string[cursor]
        cursor += 1
        if i == 0xFF:
            # 0xFF marks the end of a string, like 0x00 in C-style strings
            break
        elif i == 0xFE:
            # Newline character. These are hardcoded to fit inside the text boxes,
            # so by default we replace them with a space.
            if not replace_newline:
                string += "\n"
            # If the previous character was a '-', the words before and after
            # the newline probably belong together (such as 'red-\nglowing'),
            # so we should not add a space in that case.
            elif len(string) <= 0 or string[-1] != "-":
                string += " "
        elif i == 0xFD:
            if cursor >= len(encoded_string):
                return string

            # Marks a variable (the following byte indicates which variable should
            # be substituted.)
            i = encoded_string[cursor]
            cursor += 1
            if i == 0x01:
                string += "{PlayerName}"
            elif i == 0x06:
                string += "{RivalName}"
            else:
                string += "{Var" + str(i - 1) + "}"
        elif i == 0xFC:
            if cursor >= len(encoded_string):
                return string

            # Text formatting codes, which can be followed by 1, 2, or 3 bytes.
            i = encoded_string[cursor]
            if i in [0x04, 0x0C, 0x10]:
                cursor += 3
            elif i in [0x01, 0x02, 0x03, 0x06, 0x08, 0x0D]:
                cursor += 2
            else:
                cursor += 1
        elif i in [0xFB, 0xFA]:
            # Controls text box behaviour which we do not care about.
            continue
        else:
            # Actual printable characters
            string += character_table[i]
    return string


def encode_string(
    string: str,
    character_set: Literal["international", "japanese", "rom_default"] = "rom_default",
    ignore_errors: bool = False,
) -> bytes:
    if character_set == "rom_default":
        character_table = _current_game_data.character_table
    elif character_set == "international":
        character_table = _character_table_international
    elif character_set == "japanese":
        character_table = _character_table_japanese
    else:
        raise RuntimeError(f"Invalid value for character set: '{character_set}'.")

    result = b""
    for index in range(len(string)):
        character = string[index]
        if character not in character_table:
            if not ignore_errors:
                raise ValueError(f"Cannot encode '{character}'.")
            else:
                continue
        code = character_table.index(character)
        result += int.to_bytes(code)
    return result
