import os
import json
import time
import struct
from pymem import Pymem
from enum import IntEnum
import win32gui, win32process
from modules.Console import console
from modules.Files import ReadFile

# https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)
char_maps = json.loads(ReadFile('./modules/data/char-maps.json'))
char_map_i = char_maps['i']
char_map_j = char_maps['j']


def GetPointer(proc, base, offsets) -> int:
    """
    This function will "follow a bouncing ball" of offsets and return a pointer to the desired memory location.
    When mGBA is launched, the locations of the GBA memory domains will be in a random location, this ensures that
    the same memory domain can be found reliably, every time.
    For more information check out: https://www.youtube.com/watch?v=YaFlh2pIKAg

    :param proc: an initialised Pymem class
    :param base: base address
    :param offsets: memory offsets to follow
    :return: memory pointer to the desired address
    """

    addr = proc.read_longlong(base)
    for i in offsets:
        if i != offsets[-1]:
            addr = proc.read_longlong(addr + i)
    return addr + offsets[-1]


class Emulator:
    """
    The `Emulator` class contains the Pymem class + game specific information/symbols/offsets:

    game: Game title (e.g. `Pokémon Emerald`)
    game_code: Game code from the loaded ROM (e.g. `BPEE` = `BPE` = Emerald, `E` = English)
    char_map: Character map for in-game text (Internation or Japanese)
    see: https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)#Character_sets
    sym_file: Symbol table file to load from `./modules/data/symbols`, these files contain lists of pointers to
    important locations in GBA memory
    symbols: Parsed symbol table, list of tuples (address, size)
    proc: Pymem class, attached to mGBA.exe process
    p_EWRAM: mGBA.exe pointer to EWRAM memory domain
    p_IWRAM: mGBA.exe pointer to IWRAM memory domain
    p_ROM: mGBA.exe pointer to ROM memory domain
    p_Input: mGBA.exe pointer to mGBA's input register
    p_Framecount: mGBA.exe pointer to mGBA's framecount
    """
    def __game(self):
        match self.game_code[0:3]:  # Game release
            case 'AXV':
                self.game = 'Pokémon Ruby'
                match self.game_version:
                    case 0:
                        self.sym_file = 'pokeruby.sym'
                    case 1:
                        self.sym_file = 'pokeruby_rev1.sym'
                    case 2:
                        self.sym_file = 'pokeruby_rev2.sym'

            case 'AXP':
                self.game = 'Pokémon Sapphire'
                match self.game_version:
                    case 0:
                        self.sym_file = 'pokesapphire.sym'
                    case 1:
                        self.sym_file = 'pokesapphire_rev1.sym'
                    case 2:
                        self.sym_file = 'pokesapphire_rev2.sym'
            case 'BPE':
                self.game, self.sym_file = 'Pokémon Emerald', 'pokeemerald.sym'

            case 'BPR':
                self.game = 'Pokémon FireRed'
                match self.game_version:
                    case 0:
                        self.sym_file = 'pokefirered.sym'
                    case 1:
                        self.sym_file = 'pokefirered_rev1.sym'

            case 'BPG':
                self.game = 'Pokémon LeafGreen'
                match self.game_version:
                    case 0:
                        self.sym_file = 'pokeleafgreen.sym'
                    case 1:
                        self.sym_file = 'pokeleafgreen_rev1.sym'
            case _:
                self.game, self.sym_file = None, None
        match self.game_code[3]:  # Game language
            case 'E' | 'D' | 'S' | 'F' | 'I':
                self.char_map = char_map_i
            case 'J':
                self.char_map = char_map_j

    def __symbols(self):
        if self.sym_file:
            self.symbols = {}
            for d in ['modules/data/symbols/', 'modules/data/symbols/patches/']:
                for s in open('{}{}'.format(d, self.sym_file)).readlines():
                    self.symbols[s.split(' ')[3].strip().upper()] = (
                        int(s.split(' ')[0], 16),
                        int(s.split(' ')[2], 16)
                    )
        else:
            self.symbols = None

    def __init__(self, pid):
        try:
            self.proc = Pymem(pid)
            self.p_EWRAM = GetPointer(self.proc, self.proc.base_address + 0x02849A28,
                                      offsets=[0x40, 0x58, 0x3D8, 0x10, 0x80, 0x28, 0x0])
            self.p_IWRAM = GetPointer(self.proc, self.proc.base_address + 0x02849A28,
                                      offsets=[0x40, 0x28, 0x58, 0x10, 0xF0, 0x30, 0x0])
            self.p_ROM = GetPointer(self.proc, self.proc.base_address + 0x02849A28,
                                    offsets=[0x40, 0x28, 0x58, 0x10, 0xb8, 0x38, 0x0])
            self.p_Input = GetPointer(self.proc, self.proc.base_address + 0x02849A28,
                                      offsets=[0x20, 0x58, 0x6D8, 0x420, 0x168, 0x420, 0xDE4])
            self.p_Framecount = GetPointer(self.proc, self.proc.base_address + 0x02849A28,
                                           offsets=[0x40, 0x58, 0x10, 0x1C0, 0x0, 0x90, 0xF0])
            self.game_code = self.proc.read_bytes(self.p_ROM + 0xAC, 4).decode('utf-8')
            self.game_version = int.from_bytes(self.proc.read_bytes(self.p_ROM + 0xBC, 1))
            self.__game()
            self.__symbols()
        except:
            console.print_exception(show_locals=True)
            console.print('[red]Ensure you are using mGBA 0.10.2 [bold]64-bit[/], not [bold]32-bit[/]!')
            os._exit(1)


while True:
    with console.status('[bold purple]Click on an mGBA instance to attach bot to...'):
        fg = win32gui.GetForegroundWindow()
        title = win32gui.GetWindowText(fg)
        tid, pid = win32process.GetWindowThreadProcessId(fg)

        if 'mGBA' in title:
            mGBA = Emulator(pid)
            if mGBA.game:
                console.print('Bot successfully attached to mGBA PID {}!'.format(pid))
                console.print('Detected game: {} ({})'.format(
                    mGBA.game,
                    mGBA.game_code))
                break
            else:
                console.print('[bold red]Unsupported ROM detected![/]')
                input('Press enter to exit...')
                os._exit(1)
        time.sleep(0.5)


def SymbolOffset(addr: int) -> int:
    """
    Calculate and return mGBA process memory offset + GBA memory domain offset

    :param addr: GBA memory offset
    :return: mGBA process offset
    """
    match addr >> 0x18:
        case 0x2:
            return mGBA.p_EWRAM + (addr - mGBA.symbols['EWRAM_START'][0])
        case 0x3:
            return mGBA.p_IWRAM + (addr - mGBA.symbols['IWRAM_START'][0])
        case 0x8:
            return mGBA.p_ROM + (addr - mGBA.symbols['START'][0])


def ReadSymbol(name: str, offset: int = 0x0, size: int = 0x0) -> bytes:
    """
    This function uses the symbol tables from the Pokémon decompilation projects found here: https://github.com/pret
    Symbol tables are loaded and parsed as a dict in the `Emulator` class, the .sym files for each game can be found
    in `modules/data/symbols`.

    Format of symbol tables:
    `020244ec g 00000258 gPlayerParty`
    020244ec     - memory address
    g            - (l,g,,!) local, global, neither, both
    00000258     - size in bytes (base 16) (0x258 = 600 bytes)
    gPlayerParty - name of the symbol

    GBA memory domains: https://corrupt.wiki/consoles/gameboy-advance/bizhawk-memory-domains
    0x02000000 - 0x02030000 - 256 KB EWRAM (general purpose RAM external to the CPU)
    0x03000000 - 0x03007FFF - 32 KB IWRAM (general purpose RAM internal to the CPU)
    0x08000000 - 0x???????? - Game Pak ROM (0 to 32 MB)

    :param name: name of the symbol to read
    :param offset: (optional) add n bytes to the address of symbol
    :param size: (optional) override the size to read n bytes
    :return: (bytes)
    """
    try:
        name = name.upper()
        addr = SymbolOffset(mGBA.symbols[name][0])
        if size > 0:
            return mGBA.proc.read_bytes(addr + offset, size)
        else:
            return mGBA.proc.read_bytes(addr + offset, mGBA.symbols[name][1])
    except:
        console.print_exception(show_locals=True)


def WriteSymbol(name: str, data: bytes, offset: int = 0x0) -> bool:
    try:
        name = name.upper()
        addr = SymbolOffset(mGBA.symbols[name][0])
        if (len(data) + offset) > mGBA.symbols[name][1]:
            raise Exception('{} bytes of data provided, is too large for symbol {} ({} bytes)!'.format(
                (len(data) + offset),
                mGBA.symbols[name][0],
                mGBA.symbols[name][1]
            ))
        else:
            mGBA.proc.write_bytes(addr + offset, data, len(data))
            return True
    except:
        console.print_exception(show_locals=True)
        os._exit(1)


def GetSymbolName(address: int) -> str:
    """
    Get the name of a symbol based on the address

    :param address: address of the symbol
    
    :return: name of the symbol (str)
    """
    for key, (value, _) in mGBA.symbols.items():
        if value == address:
            return key
    return ''


def ParseTasks() -> list:
    try:
        gTasks = ReadSymbol('gTasks')
        tasks = []
        for x in range(16):
            name = GetSymbolName(int(struct.unpack('<I', gTasks[(x*40):(x*40+4)])[0]) - 1)
            if name == '':
                name = str(gTasks[(x*40):(x*40+4)])
            tasks.append({
                'func': name,
                'isActive': bool(gTasks[(x*40+4)]),
                'prev': gTasks[(x*40+5)],
                'next': gTasks[(x*40+6)],
                'priority': gTasks[(x*40+7)],
                'data': gTasks[(x*40+8):(x*40+40)]
            })
        return tasks
    except:
        console.print_exception(show_locals=True)


def GetTask(func: str) -> dict:
    tasks = ParseTasks()
    for task in tasks:
        if task['func'] == func:
            return task
    return {}


def GetFrameCount():
    """
    Get the current mGBA frame count since the start of emulation.

    :return: framecount (int)
    """
    return struct.unpack('<I', mGBA.proc.read_bytes(mGBA.p_Framecount, length=4))[0]


def DecodeString(b: bytes) -> str:
    """
    Generation III Pokémon games use a proprietary character encoding to store text data.
    The Generation III encoding is greatly different from the encodings used in previous generations, with characters
    corresponding to different bytes.
    See for more information:  https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)

    :param b: bytes to decode to string
    :return: decoded bytes (string)
    """
    string = ''
    for i in b:
        c = int(i) - 16
        if c < 0 or c > len(mGBA.char_map):
            string = string + ' '
        else:
            string = string + mGBA.char_map[c]
    return string.strip()


def EncodeString(t: str) -> bytes:
    """
    Generation III Pokémon games use a proprietary character encoding to store text data.
    The Generation III encoding is greatly different from the encodings used in previous generations, with characters
    corresponding to different bytes.
    See for more information:  https://bulbapedia.bulbagarden.net/wiki/Character_encoding_(Generation_III)

    :param t: text string to encode to bytes
    :return: encoded text (bytes)
    """
    byte_str = bytearray(b'')
    for i in t:
        try:
            byte_str.append(mGBA.char_map.index(i) + 16)
        except:
            byte_str.append(0)
    return bytes(byte_str)


def GetSaveBlock(num: int = 1, offset: int = 0, size: int = 0) -> bytes:
    """
    The Generation III save file is broken up into two game save blocks, this function will return sections from these
    save blocks. Emerald, FireRed and LeafGreen SaveBlocks will randomly move around in memory, which requires following
     a pointer to find them reliably.

    :param num: 1 or 2 (gSaveblock1 or gSaveblock2)
    see: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Game_save_A.2C_Game_save_B
    :param offset: Read n bytes offset from beginning of the save block, use with `size` - useful to reduce amount of
    bytes read if only specific memory region is required.
    :param size: Read n bytes from the offset
    :return: SaveBlock (bytes)
    """
    # https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)
    try:
        if not size:
            size = mGBA.symbols['GSAVEBLOCK{}'.format(num)][1]
        if mGBA.game in ['Pokémon Emerald', 'Pokémon FireRed', 'Pokémon LeafGreen']:
            p_Trainer = mGBA.p_EWRAM + (
                    struct.unpack('<I', ReadSymbol('gSaveBlock{}Ptr'.format(num)))[0] - mGBA.symbols['EWRAM_START'][0])
            return mGBA.proc.read_bytes(p_Trainer + offset, size)
        else:
            return ReadSymbol('gSaveBlock{}'.format(num), offset=offset, size=size)
    except:
        console.print_exception(show_locals=True)


# Game specific offsets
# Source: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Section_1_-_Team_.2F_Items
if mGBA.game in ['Pokémon FireRed', 'Pokémon LeafGreen']:
    setattr(mGBA, 'item_offsets', [(0x298, 120), (0x310, 168), (0x3B8, 120), (0x430, 52), (0x464, 232), (0x54C, 172)])
    setattr(mGBA, 'item_key', struct.unpack('<H', GetSaveBlock(2, 0xF20, 2))[0])
elif mGBA.game == 'Pokémon Emerald':
    setattr(mGBA, 'item_offsets', [(0x498, 200), (0x560, 120), (0x5D8, 120), (0x650, 64), (0x690, 256), (0x790, 184)])
    setattr(mGBA, 'item_key', struct.unpack('<H', GetSaveBlock(2, 0xAC, 2))[0])
else:
    setattr(mGBA, 'item_offsets', [(0x498, 200), (0x560, 80), (0x5B0, 80), (0x600, 64), (0x640, 256), (0x740, 184)])
    setattr(mGBA, 'item_key', 0)


class GameState(IntEnum):
    # Menus
    BAG_MENU = 100
    CHOOSE_STARTER = 101
    PARTY_MENU = 102
    # Battle related
    BATTLE = 200
    BATTLE_STARTING = 201
    BATTLE_ENDING = 202
    # Misc
    OVERWORLD = 900
    CHANGE_MAP = 901
    TITLE_SCREEN = 902
    UNKNOWN = 999

def GetGameState() -> GameState:
    callback2 = ReadSymbol('gMain', 4, 4)  #gMain.callback2
    addr = int(struct.unpack('<I', callback2)[0]) - 1
    state = GetSymbolName(addr)

    match state:
        case 'CB2_OVERWORLD':
            return GameState.OVERWORLD
        case 'BATTLEMAINCB2':
            return GameState.BATTLE
        case 'CB2_BAGMENURUN' | 'SUB_80A3118':
            return GameState.BAG_MENU
        case 'CB2_UPDATEPARTYMENU' | 'CB2_PARTYMENUMAIN':
            return GameState.PARTY_MENU
        case 'CB2_INITBATTLE' | 'CB2_HANDLESTARTBATTLE':
            return GameState.BATTLE_STARTING
        case 'CB2_ENDWILDBATTLE':
            return GameState.BATTLE_ENDING
        case 'CB2_LOADMAP' | 'CB2_LOADMAP2' | 'CB2_DOCHANGEMAP' | 'SUB_810CC80':
            return GameState.CHANGE_MAP
        case 'CB2_STARTERCHOOSE' | 'CB2_CHOOSESTARTER':
            return GameState.CHOOSE_STARTER
        case 'CB2_INITCOPYRIGHTSCREENAFTERBOOTUP' | 'CB2_WAITFADEBEFORESETUPINTRO' | 'CB2_SETUPINTRO' | 'CB2_INTRO' | \
             'CB2_INITTITLESCREEN' | 'CB2_TITLESCREENRUN' | 'CB2_INITCOPYRIGHTSCREENAFTERTITLESCREEN' | \
             'CB2_INITMAINMENU' | 'CB2_MAINMENU':
            return GameState.TITLE_SCREEN
        case _:
            return GameState.UNKNOWN
