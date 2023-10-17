import json
import os.path

from modules.Files import ReadFile
from modules.Roms import ROM, ROMLanguage

_symbols: dict[str, tuple[int, int]] = {}
_reverse_symbols: dict[int, tuple[str, str, int]] = {}
_char_map: str = ""


def _LoadSymbols(symbols_file: str, language: ROMLanguage) -> None:
    global _symbols, _reverse_symbols

    _symbols.clear()
    _reverse_symbols.clear()
    for d in ["modules/data/symbols/", "modules/data/symbols/patches/"]:
        for s in open(f"{d}{symbols_file}").readlines():
            address, _, length, label = s.split(" ")

            address = int(address, 16)
            length = int(length, 16)
            label = label.strip()

            _symbols[label.upper()] = (address, length)
            if address not in _reverse_symbols or _reverse_symbols[address][2] == 0 and length > 0:
                _reverse_symbols[address] = (label.upper(), label, length)

    language_code = str(language)
    language_patch_file = symbols_file.replace(".sym", ".json")
    language_patch_path = f"modules/data/symbols/patches/language/{language_patch_file}"
    if language_code in ["D", "I", "S", "F", "J"] and os.path.exists(language_patch_path):
        language_patches = json.loads(ReadFile(language_patch_path))
        for item in language_patches:
            if language_code in language_patches[item]:
                _symbols[item.upper()] = (int(language_patches[item][language_code], 16), _symbols[item.upper()][1])
                _reverse_symbols[int(language_patches[item][language_code], 16)] = (
                    item.upper(),
                    item,
                    _symbols[item.upper()][1],
                )


def _LoadCharmap(charmap_index: str) -> None:
    global _char_map

    # https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)
    char_maps = json.loads(ReadFile("./modules/data/char-maps.json"))
    _char_map = char_maps[charmap_index]


def SetROM(rom: ROM) -> None:
    global _symbols, _char_map

    match rom.game_code:
        case "AXV":
            match rom.revision:
                case 0:
                    _LoadSymbols("pokeruby.sym", rom.language)
                case 1:
                    _LoadSymbols("pokeruby_rev1.sym", rom.language)
                case 2:
                    _LoadSymbols("pokeruby_rev2.sym", rom.language)

        case "AXP":
            match rom.revision:
                case 0:
                    _LoadSymbols("pokesapphire.sym", rom.language)
                case 1:
                    _LoadSymbols("pokesapphire_rev1.sym", rom.language)
                case 2:
                    _LoadSymbols("pokesapphire_rev2.sym", rom.language)

        case "BPE":
            _LoadSymbols("pokeemerald.sym", rom.language)

        case "BPR":
            match rom.revision:
                case 0:
                    _LoadSymbols("pokefirered.sym", rom.language)
                case 1:
                    _LoadSymbols("pokefirered_rev1.sym", rom.language)

        case "BPG":
            match rom.revision:
                case 0:
                    _LoadSymbols("pokeleafgreen.sym", rom.language)
                case 1:
                    _LoadSymbols("pokeleafgreen_rev1.sym", rom.language)

    if rom.language == ROMLanguage.Japanese:
        _LoadCharmap("j")
    else:
        _LoadCharmap("i")


def GetSymbol(symbol_name: str) -> tuple[int, int]:
    canonical_name = symbol_name.strip().upper()
    if canonical_name not in _symbols:
        raise RuntimeError("Unknown symbol: " + symbol_name)

    return _symbols[canonical_name]


def GetSymbolName(address: int, pretty_name: bool = False) -> str:
    """
    Get the name of a symbol based on the address

    :param address: address of the symbol

    :return: name of the symbol (str)
    """
    return _reverse_symbols.get(address, ("", ""))[0 if not pretty_name else 1]


def DecodeString(encoded_string: bytes) -> str:
    """
    Generation III Pokémon games use a proprietary character encoding to store text data.
    The Generation III encoding is greatly different from the encodings used in previous generations, with characters
    corresponding to different bytes.
    See for more information:  https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)

    :param encoded_string: bytes to decode to string
    :return: decoded bytes (string)
    """
    string = ""
    for i in encoded_string:
        c = int(i) - 16
        if c < 0 or c > len(_char_map):
            string = string + " "
        else:
            string = string + _char_map[c]
    return string.strip()


def EncodeString(string: str) -> bytes:
    """
    Generation III Pokémon games use a proprietary character encoding to store text data.
    The Generation III encoding is greatly different from the encodings used in previous generations, with characters
    corresponding to different bytes.
    See for more information:  https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)

    :param string: text string to encode to bytes
    :return: encoded text (bytes)
    """
    byte_str = bytearray(b"")
    for i in string:
        try:
            byte_str.append(_char_map.index(i) + 16)
        except:
            byte_str.append(0)
    return bytes(byte_str)
