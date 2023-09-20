import os
import platform
import time
import struct
from enum import IntEnum
from ruamel.yaml import YAML
from modules.Console import console
from modules.Game import game, SetGame, GetSymbol, GetSymbolName
from modules.emulator.BaseEmulator import Emulator

emulator: Emulator

# Importing `modules.Config` is not possible at this point as it would lead to a circular import.
# But we need the config to figure out the emulator mode.
with open('config/general.yml') as file:
    config_general = YAML().load(file)

if config_general['emulator_mode'] == 'pymem_mgba':
    if platform.system() != "Windows":
        raise RuntimeError('Emulator mode `pymem_mgba` is only supported on Windows, not on ' + platform.system())

    from modules.emulator.PymemMgbaEmulator import PymemMgbaEmulator
    import win32gui, win32process
    from pymem import Pymem

    while True:
        with console.status('[bold purple]Click on an mGBA instance to attach bot to...'):
            fg = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(fg)
            tid, pid = win32process.GetWindowThreadProcessId(fg)

            if 'mGBA' in title:
                proc = Pymem(pid)
                emulator = PymemMgbaEmulator(proc)
                SetGame(emulator.GetGameCode(), emulator.ReadROM(0xBC, 1)[0])
                if game.name:
                    console.print('Bot successfully attached to mGBA PID {}!'.format(pid))
                    console.print('Detected game: {} ({})'.format(
                        game.name,
                        emulator.GetGameCode()))
                    break
                else:
                    console.print('[bold red]Unsupported ROM detected![/]')
                    input('Press enter to exit...')
                    os._exit(1)
            time.sleep(0.5)
else:
    from modules.emulator.LibmgbaEmulator import LibMgbaEmulator

    if not os.path.isfile("emerald.gba"):
        console.print("ROM is missing: There should be a file called `emerald.gba` in the pokebot root directory.")
        os._exit(1)

    emulator = LibMgbaEmulator("emerald.gba")
    SetGame(emulator.GetGameCode(), emulator.ReadROM(0xBC, 1)[0])


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
        addr, length = GetSymbol(name)
        if size <= 0:
            size = length

        return emulator.ReadBus(addr + offset, size)
    except:
        console.print_exception(show_locals=True)


def WriteSymbol(name: str, data: bytes, offset: int = 0x0) -> bool:
    try:
        addr, length = GetSymbol(name)
        if len(data) + offset > length:
            raise Exception('{} bytes of data provided, is too large for symbol {} ({} bytes)!'.format(
                (len(data) + offset),
                addr,
                length
            ))

        emulator.WriteBus(addr + offset, data)
        return True
    except:
        console.print_exception(show_locals=True)
        os._exit(1)


def ParseTasks() -> list:
    try:
        gTasks = ReadSymbol('gTasks')
        tasks = []
        for x in range(16):
            name = GetSymbolName(int(struct.unpack('<I', gTasks[(x * 40):(x * 40 + 4)])[0]) - 1)
            if name == '':
                name = str(gTasks[(x * 40):(x * 40 + 4)])
            tasks.append({
                'func': name,
                'isActive': bool(gTasks[(x * 40 + 4)]),
                'prev': gTasks[(x * 40 + 5)],
                'next': gTasks[(x * 40 + 6)],
                'priority': gTasks[(x * 40 + 7)],
                'data': gTasks[(x * 40 + 8):(x * 40 + 40)]
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
            size = GetSymbol('GSAVEBLOCK{}'.format(num))[1]
        if game.name in ['Pokémon Emerald', 'Pokémon FireRed', 'Pokémon LeafGreen']:
            p_Trainer = struct.unpack('<I', ReadSymbol('gSaveBlock{}Ptr'.format(num)))[0]
            return emulator.ReadBus(p_Trainer + offset, size)
        else:
            return ReadSymbol('gSaveBlock{}'.format(num), offset=offset, size=size)
    except:
        console.print_exception(show_locals=True)


def GetItemOffsets() -> list[tuple[int, int]]:
    # Game specific offsets
    # Source: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Section_1_-_Team_.2F_Items
    if game.name in ['Pokémon FireRed', 'Pokémon LeafGreen']:
        return [(0x298, 120), (0x310, 168), (0x3B8, 120), (0x430, 52), (0x464, 232), (0x54C, 172)]
    elif game.name == 'Pokémon Emerald':
        return [(0x498, 200), (0x560, 120), (0x5D8, 120), (0x650, 64), (0x690, 256), (0x790, 184)]
    else:
        return [(0x498, 200), (0x560, 80), (0x5B0, 80), (0x600, 64), (0x640, 256), (0x740, 184)]


def GetItemKey() -> int:
    if game.name in ['Pokémon FireRed', 'Pokémon LeafGreen']:
        return struct.unpack('<H', GetSaveBlock(2, 0xF20, 2))[0]
    elif game.name == 'Pokémon Emerald':
        return struct.unpack('<H', GetSaveBlock(2, 0xAC, 2))[0]
    else:
        return 0


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
    callback2 = ReadSymbol('gMain', 4, 4)  # gMain.callback2
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
            # print(f"Unknown state: {state}")
            return GameState.UNKNOWN
