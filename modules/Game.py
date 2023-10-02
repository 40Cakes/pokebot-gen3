import json
import os.path

from modules.Files import ReadFile
from modules.Roms import ROM, ROMLanguage

_symbols: dict[str, tuple[int, int]] = {}
_char_map: str = ""


def _LoadSymbols(symbols_file: str, language: ROMLanguage) -> None:
    global _symbols

    _symbols.clear()
    for d in ['modules/data/symbols/', 'modules/data/symbols/patches/']:
        for s in open('{}{}'.format(d, symbols_file)).readlines():
            _symbols[s.split(' ')[3].strip().upper()] = (
                int(s.split(' ')[0], 16),
                int(s.split(' ')[2], 16)
            )

    language_code = str(language)
    language_patch_file = symbols_file.replace('.sym', '.json')
    language_patch_path = f'modules/data/symbols/patches/language/{language_patch_file}'
    if language_code in ['D', 'I', 'S', 'F', 'J'] and os.path.exists(language_patch_path):
        language_patches = json.loads(ReadFile(language_patch_path))
        for item in language_patches:
            if language_code in language_patches[item]:
                _symbols[item.upper()] = (
                    int(language_patches[item][language_code], 16),
                    _symbols[item.upper()][1]
                )


def _LoadCharmap(charmap_index: str) -> None:
    global _char_map

    # https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)
    char_maps = json.loads(ReadFile('./modules/data/char-maps.json'))
    _char_map = char_maps[charmap_index]


def SetROM(rom: ROM) -> None:
    global _symbols, _char_map

    match rom.game_code:
        case 'AXV':
            match rom.revision:
                case 0:
                    _LoadSymbols('pokeruby.sym', rom.language)
                case 1:
                    _LoadSymbols('pokeruby_rev1.sym', rom.language)
                case 2:
                    _LoadSymbols('pokeruby_rev2.sym', rom.language)

        case 'AXP':
            match rom.revision:
                case 0:
                    _LoadSymbols('pokesapphire.sym', rom.language)
                case 1:
                    _LoadSymbols('pokesapphire_rev1.sym', rom.language)
                case 2:
                    _LoadSymbols('pokesapphire_rev2.sym', rom.language)

        case 'BPE':
            _LoadSymbols('pokeemerald.sym', rom.language)

        case 'BPR':
            match rom.revision:
                case 0:
                    _LoadSymbols('pokefirered.sym', rom.language)
                case 1:
                    _LoadSymbols('pokefirered_rev1.sym', rom.language)

        case 'BPG':
            match rom.revision:
                case 0:
                    _LoadSymbols('pokeleafgreen.sym', rom.language)
                case 1:
                    _LoadSymbols('pokeleafgreen_rev1.sym', rom.language)

    if rom.language == ROMLanguage.Japanese:
        _LoadCharmap('j')
    else:
        _LoadCharmap('i')


def GetSymbol(symbol_name: str) -> tuple[int, int]:
    canonical_name = symbol_name.strip().upper()
    if canonical_name not in _symbols:
        raise RuntimeError("Unknown symbol: " + symbol_name)

    return _symbols[canonical_name]


def GetSymbolName(address: int) -> str:
    """
    Get the name of a symbol based on the address

    :param address: address of the symbol

    :return: name of the symbol (str)
    """
    for key, (value, _) in _symbols.items():
        if value == address:
            return key
    return ''


def DecodeString(encoded_string: bytes) -> str:
    """
    Generation III Pokémon games use a proprietary character encoding to store text data.
    The Generation III encoding is greatly different from the encodings used in previous generations, with characters
    corresponding to different bytes.
    See for more information:  https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)

    :param encoded_string: bytes to decode to string
    :return: decoded bytes (string)
    """
    string = ''
    for i in encoded_string:
        c = int(i) - 16
        if c < 0 or c > len(_char_map):
            string = string + ' '
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
    byte_str = bytearray(b'')
    for i in string:
        try:
            byte_str.append(_char_map.index(i) + 16)
        except:
            byte_str.append(0)
    return bytes(byte_str)
