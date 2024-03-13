import json
from typing import Literal

from modules.roms import ROM, ROMLanguage
from modules.runtime import get_data_path

_symbols: dict[str, tuple[int, int]] = {}
_reverse_symbols: dict[int, tuple[str, str, int]] = {}
_event_flags: dict[str, tuple[int, int]] = {}
_reverse_event_flags: dict[int, str] = {}
_event_vars: dict[str, int] = {}
_reverse_event_vars: dict[int, str] = {}
_character_table_international: list[str] = []
_character_table_japanese: list[str] = []
_current_character_table: list[str] = []


def _load_symbols(symbols_file: str, language: ROMLanguage) -> None:
    global _symbols, _reverse_symbols

    _symbols.clear()
    _reverse_symbols.clear()
    for d in [get_data_path() / "symbols", get_data_path() / "symbols" / "patches"]:
        for s in open(d / symbols_file):
            address, _, length, label = s.split(" ")

            address = int(address, 16)
            length = int(length, 16)
            label = label.strip()

            _symbols[label.upper()] = (address, length)
            if address not in _reverse_symbols or _reverse_symbols[address][2] == 0 and length > 0:
                _reverse_symbols[address] = (label.upper(), label, length)

    language_code = str(language)
    language_patch_file = symbols_file.replace(".sym", ".json")
    language_patch_path = get_data_path() / "symbols" / "patches" / "language" / language_patch_file
    if language_code in {"D", "I", "S", "F", "J"} and language_patch_path.is_file():
        with open(language_patch_path, "r") as file:
            language_patches = json.load(file)
        for label in language_patches:
            if language_code in language_patches[label]:
                _reverse_symbols.pop(_symbols[label.upper()][0])
                addresses = language_patches[label][language_code]
                if type(addresses) is not list:
                    addresses = [addresses]
                for addr in addresses:
                    _symbols[label.upper()] = (int(addr, 16), _symbols[label.upper()][1])
                    _reverse_symbols[int(addr, 16)] = (
                        label.upper(),
                        label,
                        _symbols[label.upper()][1],
                    )


def _load_event_flags_and_vars(file_name: str) -> None:  # TODO Japanese ROMs not working
    global _event_flags, _reverse_event_flags, _event_vars, _reverse_event_vars

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

    _event_flags.clear()
    _reverse_event_flags.clear()
    for s in open(get_data_path() / "event_flags" / file_name):
        number, name = s.strip().split(" ")
        _event_flags[name] = (int(number) // 8) + flags_offset, int(number) % 8
        _reverse_event_flags[int(number)] = name

    _event_vars.clear()
    _reverse_event_vars.clear()
    for s in open(get_data_path() / "event_vars" / file_name):
        number, name = s.strip().split(" ")
        _event_vars[name] = int(number) * 2 + vars_offset
        _reverse_event_vars[int(number)] = name


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
        + " “”‘’♂♀$,×/ABCDE"
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
    global _symbols, _current_character_table

    match rom.game_code:
        case "AXV":
            match rom.revision:
                case 0:
                    match rom.language:
                        case "D":
                            _load_symbols("pokeruby_de.sym", rom.language)
                        case _:
                            _load_symbols("pokeruby.sym", rom.language)
                case 1:
                    match rom.language:
                        case "D":
                            _load_symbols("pokeruby_de_rev1.sym", rom.language)
                        case _:
                            _load_symbols("pokeruby_rev1.sym", rom.language)
                case 2:
                    _load_symbols("pokeruby_rev2.sym", rom.language)
            _load_event_flags_and_vars("rs.txt")

        case "AXP":
            match rom.revision:
                case 0:
                    match rom.language:
                        case "D":
                            _load_symbols("pokesapphire_de.sym", rom.language)
                        case _:
                            _load_symbols("pokesapphire.sym", rom.language)
                case 1:
                    match rom.language:
                        case "D":
                            _load_symbols("pokesapphire_de_rev1.sym", rom.language)
                        case _:
                            _load_symbols("pokesapphire_rev1.sym", rom.language)
                case 2:
                    _load_symbols("pokesapphire_rev2.sym", rom.language)
            _load_event_flags_and_vars("rs.txt")

        case "BPE":
            _load_symbols("pokeemerald.sym", rom.language)
            _load_event_flags_and_vars("emerald.txt")

        case "BPR":
            match rom.revision:
                case 0:
                    _load_symbols("pokefirered.sym", rom.language)
                case 1:
                    _load_symbols("pokefirered_rev1.sym", rom.language)
            _load_event_flags_and_vars("frlg.txt")

        case "BPG":
            match rom.revision:
                case 0:
                    _load_symbols("pokeleafgreen.sym", rom.language)
                case 1:
                    _load_symbols("pokeleafgreen_rev1.sym", rom.language)
            _load_event_flags_and_vars("frlg.txt")

    _prepare_character_tables()
    if rom.language == ROMLanguage.Japanese:
        _current_character_table = _character_table_japanese
    else:
        _current_character_table = _character_table_international


def get_symbol(symbol_name: str) -> tuple[int, int]:
    canonical_name = symbol_name.strip().upper()
    if canonical_name not in _symbols:
        raise RuntimeError(f"Unknown symbol: {symbol_name}!")

    return _symbols[canonical_name]


def get_symbol_name(address: int, pretty_name: bool = False) -> str:
    """
    Get the name of a symbol based on the address

    :param address: address of the symbol
    :param pretty_name: Whether to return the symbol name all-uppercase (False) or
                        with 'natural' case (True)

    :return: name of the symbol (str)
    """
    return _reverse_symbols.get(address, ("", ""))[(1 if pretty_name else 0)]


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
            _reverse_symbols[address - lookahead][(1 if pretty_name else 0)]
            for lookahead in range(maximum_lookahead)
            if address - lookahead in _reverse_symbols
        ),
        hex(address),
    )


def get_event_flag_offset(flag_name: str) -> tuple[int, int]:
    return _event_flags[flag_name]


def get_event_flag_name(flag_number: int) -> str:
    if flag_number == 0:
        return ""
    return _reverse_event_flags.get(flag_number, str(flag_number))


def get_event_var_offset(var_name: str) -> int:
    return _event_vars[var_name]


def get_event_var_name(var_number: int) -> str:
    return _reverse_event_vars.get(var_number, str(var_number))


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
        character_table = _current_character_table
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
                return

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
                return

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
