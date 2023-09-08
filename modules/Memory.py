import os
import json
import time
import numpy
import struct
from pymem import Pymem
from enum import IntEnum
import win32gui, win32process
from modules.Console import console
from modules.Files import ReadFile


moves_list = json.loads(ReadFile('./modules/data/moves.json'))
names_list = json.loads(ReadFile('./modules/data/names.json'))
natures_list = json.loads(ReadFile('./modules/data/natures.json'))
nat_ids_list = json.loads(ReadFile('./modules/data/nat-ids.json'))
item_list = json.loads(ReadFile('./modules/data/items.json'))
exp_groups_list = json.loads(ReadFile('./modules/data/exp-groups.json'))
pokemon_list = json.loads(ReadFile('./modules/data/pokemon.json'))
location_list = json.loads(ReadFile('./modules/data/locations.json'))
hidden_powers_list = json.loads(ReadFile('./modules/data/hidden-powers.json'))

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
                if self.game_version == b'\x00':
                    self.sym_file = 'pokeruby.sym'
                elif self.game_version == b'\x01':
                    self.sym_file = 'pokeruby_rev1.sym'
                elif self.game_version == b'\x02':
                    self.sym_file = 'pokeruby_rev2.sym'
            case 'AXP':
                self.game = 'Pokémon Sapphire'
                if self.game_version == b'\x00':
                    self.sym_file = 'pokesapphire.sym'
                elif self.game_version == b'\x01':
                    self.sym_file = 'pokesapphire_rev1.sym'
                elif self.game_version == b'\x02':
                    self.sym_file = 'pokesapphire_rev2.sym'
            case 'BPE':
                self.game, self.sym_file = 'Pokémon Emerald', 'pokeemerald.sym'
            case 'BPR':
                self.game = 'Pokémon FireRed'
                if self.game_version == b'\x00':
                    self.sym_file = 'pokefirered.sym'
                elif self.game_version == b'\x01':
                    self.sym_file = 'pokefirered_rev1.sym'
            case 'BPG':
                self.game = 'Pokémon LeafGreen'
                if self.game_version == b'\x00':
                    self.sym_file = 'pokeleafgreen.sym'
                elif self.game_version == b'\x01':
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
            for s in open('modules/data/symbols/{}'.format(self.sym_file)).readlines():
                self.symbols[s.split(' ')[3].strip().upper()] = (
                    int(s.split(' ')[0], 16),
                    int(s.split(' ')[2], 16)
                )
        else:
            self.symbols = None

    def __init__(self, pid):
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
        self.game_version = self.proc.read_bytes(self.p_ROM + 0xBC, 1)
        self.__game()
        self.__symbols()


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
    name = name.upper()
    sym_addr = mGBA.symbols[name][0]
    match sym_addr >> 0x18:
        case 0x2:
            addr = mGBA.p_EWRAM + (sym_addr - mGBA.symbols['EWRAM_START'][0])
        case 0x3:
            addr = mGBA.p_IWRAM + (sym_addr - mGBA.symbols['IWRAM_START'][0])
        case 0x8:
            addr = mGBA.p_ROM + (sym_addr - mGBA.symbols['Start'][0])
        case _:
            return None
    if size > 0:
        return mGBA.proc.read_bytes(addr + offset, size)
    else:
        return mGBA.proc.read_bytes(addr + offset, mGBA.symbols[name][1])


def GetFrameCount():
    """
    Get the current mGBA frame count since the start of emulation.

    :return: framecount (int)
    """
    return struct.unpack('<I', mGBA.proc.read_bytes(mGBA.p_Framecount, length=4))[0]


def FacingDir(direction: int) -> str:
    """
    Returns the direction the trainer is currently facing.

    :param direction: int
    :return: trainer facing direction (str)
    """
    match direction:
        case 0x11:
            return 'Down'
        case 0x22:
            return 'Up'
        case 0x33:
            return 'Left'
        case 0x44:
            return 'Right'


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
            size = mGBA.symbols['gSaveblock{}'.format(num)][1]
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


class TrainerState(IntEnum):
    # TODO Need further investigation; many values have multiple meanings
    BAG_MENU = 0x0
    BATTLE = 0x2
    BATTLE_2 = 0x3
    FOE_DEFEATED = 0x5
    OVERWORLD = 0x50
    MISC_MENU = 0xFF


def GetTrainer() -> dict:
    """
    Reads trainer data from memory.
    See: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Section_0_-_Trainer_Info

    name: Trainer's (decoded) name
    gender: boy/girl
    tid: Trainer ID
    sid: Secret ID
    state: ??
    map: tuple (`MapBank`, `MapID`)
    coords: tuple (`xPos`, `yPos`)
    facing: trainer facing direction `Left`/`Right`/`Down`/`Up`
    :return: Trainer (dict)
    """
    try:
        b_Save = GetSaveBlock(2, size=0xE)
        b_gTasks = ReadSymbol('gTasks', 0x57, 0x3)
        b_gObjectEvents = ReadSymbol('gObjectEvents', 0x10, 0x9)
        trainer = {
            'name': DecodeString(b_Save[0:7]),
            'gender': 'girl' if int(b_Save[8]) else 'boy',
            'tid': int(struct.unpack('<H', b_Save[10:12])[0]),
            'sid': int(struct.unpack('<H', b_Save[12:14])[0]),
            'state': int(b_gTasks[0]),
            'map': (int(b_gTasks[2]), int(b_gTasks[1])),
            'coords': (int(b_gObjectEvents[0]) - 7, int(b_gObjectEvents[2]) - 7),
            'facing': FacingDir(int(b_gObjectEvents[8]))
        }
        return trainer
    except:
        console.print_exception(show_locals=True)


def ParsePokemon(b_Pokemon: bytes) -> dict:
    """
    Parses raw Pokémon byte data.
    See: https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_III)

    :param b_Pokemon: Pokémon bytes (100 bytes) !TODO - PC mons are only 80 bytes
    :return: Pokémon (dict)
    """
    # https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)#Substructure_order
    substructs = ['GAEM', 'GAME', 'GEAM', 'GEMA', 'GMAE', 'GMEA', 'AGEM', 'AGME', 'AEGM', 'AEMG', 'AMGE', 'AMEG',
                  'EGAM', 'EGMA', 'EAGM', 'EAMG', 'EMGA', 'EMAG', 'MGAE', 'MGEA', 'MAGE', 'MAEG', 'MEGA', 'MEAG']

    def SpeciesName(value: int) -> str:
        if value > len(names_list):
            return ''
        return names_list[value - 1]

    def NationalDexID(value: int) -> int:
        if value <= 251:
            return value
        if value >= 413:
            return 201
        ix = value - 277
        if ix < len(nat_ids_list):
            return nat_ids_list[ix]

    def Language(value: int) -> str:
        match value:
            case 1:
                return 'J'
            case 2:
                return 'E'
            case 3:
                return 'F'
            case 4:
                return 'I'
            case 5:
                return 'D'
            case 7:
                return 'S'

    def OriginGame(value: int) -> str:
        match value:
            case 1:
                return 'Sapphire'
            case 2:
                return 'Ruby'
            case 3:
                return 'Emerald'
            case 4:
                return 'FireRed'
            case 5:
                return 'LeafGreen'
            case 15:
                return 'Colosseum/XD'

    def Moves(value: bytes) -> list:
        moves = []
        for i in range(0, 4):
            move_id = int(struct.unpack('<H', value[(i * 2):((i + 1) * 2)])[0])
            if id == 0:
                continue
            moves.append(moves_list[move_id])
            moves[i]['remaining_pp'] = int(value[(i + 8)])
        return moves

    # https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)#Encryption
    def DecryptSubSection(data: bytes, key: int):
        return struct.pack('<III',
                           struct.unpack('<I', data[0:4])[0] ^ key,
                           struct.unpack('<I', data[4:8])[0] ^ key,
                           struct.unpack('<I', data[8:12])[0] ^ key)

    try:
        flags = int(b_Pokemon[19])
        pid = struct.unpack('<I', b_Pokemon[0:4])[0]
        ot = struct.unpack('<I', b_Pokemon[4:8])[0]
        tid = int(struct.unpack('<H', b_Pokemon[4:6])[0])
        sid = int(struct.unpack('<H', b_Pokemon[6:8])[0])

        # Unpack data substructures
        # https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_III)
        # https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)
        key = ot ^ pid
        data = b_Pokemon[32:80]
        order = pid % 0x18
        order_string = substructs[order]
        sections = {}
        for i in range(0, 4):
            section = order_string[i]
            section_data = data[(i * 12):((i + 1) * 12)]
            decrypted = DecryptSubSection(section_data, key)
            sections[section] = decrypted
        id = int(struct.unpack('<H', sections['G'][0:2])[0])
        name = SpeciesName(id)
        section_m = int(struct.unpack('<I', sections['M'][4:8])[0])
        ivs = {
            'hp': int(section_m & 0x1F),
            'attack': int((section_m >> 5) & 0x1F),
            'defense': int((section_m >> 10) & 0x1F),
            'speed': int((section_m >> 15) & 0x1F),
            'spAttack': int((section_m >> 20) & 0x1F),
            'spDefense': int((section_m >> 25) & 0x1F)
        }
        item_id = int(struct.unpack('<H', sections['G'][2:4])[0])
        shiny_value = int(tid ^ sid ^ struct.unpack('<H', b_Pokemon[0:2])[0] ^ struct.unpack('<H', b_Pokemon[2:4])[0])
        shiny = True if shiny_value < 8 else False

        pokemon = {
            'name': name,
            'id': id,
            'natID': NationalDexID(id),
            'species': int(struct.unpack('<H', sections['G'][0:2])[0]),
            'pid': pid,
            'nature': natures_list[pid % 0x19],
            'language': Language(int(b_Pokemon[18])),
            'shinyValue': shiny_value,
            'shiny': shiny,
            'ot': {
                'tid': tid,
                'sid': sid
            },
            'isBadEgg': flags & 0x1,
            'hasSpecies': (flags >> 0x1) & 0x1,
            'isEgg': (flags >> 0x2) & 0x1,
            'level': int(b_Pokemon[84]),
            'expGroup': exp_groups_list[id - 1],
            'item': {
                'id': item_id,
                'name': item_list[item_id]
            },
            'friendship': int(sections['G'][9]),
            'moves': Moves(sections['A']),
            'markings': {
                'circle': True if b_Pokemon[27] & (1 << 0) else False,
                'square': True if b_Pokemon[27] & (1 << 1) else False,
                'triangle': True if b_Pokemon[27] & (1 << 2) else False,
                'heart': True if b_Pokemon[27] & (1 << 3) else False
            },
            'status': {
                'sleep': int(struct.unpack('<I', b_Pokemon[80:84])[0]) & 0x7,
                'poison': True if int(struct.unpack('<I', b_Pokemon[80:84])[0]) & (1 << 3) else False,
                'burn': True if int(struct.unpack('<I', b_Pokemon[80:84])[0]) & (1 << 4) else False,
                'freeze': True if int(struct.unpack('<I', b_Pokemon[80:84])[0]) & (1 << 5) else False,
                'paralysis': True if int(struct.unpack('<I', b_Pokemon[80:84])[0]) & (1 << 6) else False,
                'badPoison': True if int(struct.unpack('<I', b_Pokemon[80:84])[0]) & (1 << 7) else False
            },
            'stats': {
                'hp': int(b_Pokemon[86]),
                'maxHP': int(b_Pokemon[88]),
                'attack': int(b_Pokemon[90]),
                'defense': int(b_Pokemon[92]),
                'speed': int(b_Pokemon[94]),
                'spAttack': int(b_Pokemon[96]),
                'spDefense': int(b_Pokemon[98])
            },

            # Substruct G - Growth
            'experience': int(struct.unpack('<I', sections['G'][4:8])[0]),

            # Substruct A - Attacks

            # Substruct E - EVs & Condition
            'EVs': {
                'hp': int(sections['E'][0]),
                'attack': int(sections['E'][1]),
                'defence': int(sections['E'][2]),
                'speed': int(sections['E'][3]),
                'spAttack': int(sections['E'][4]),
                'spDefense': int(sections['E'][5])
            },
            'condition': {
                'cool': int(sections['E'][6]),
                'beauty': int(sections['E'][7]),
                'cute': int(sections['E'][8]),
                'smart': int(sections['E'][9]),
                'tough': int(sections['E'][10]),
                'feel': int(sections['E'][11])
            },

            # Substruct M - Miscellaneous
            'IVs': ivs,
            'IVSum': sum(ivs.values()),
            'hiddenPower': hidden_powers_list[int(numpy.floor((((ivs['hp'] % 2) +
                                                           (2 * (ivs['attack'] % 2)) +
                                                           (4 * (ivs['defense'] % 2)) +
                                                           (8 * (ivs['speed'] % 2)) +
                                                           (16 * (ivs['spAttack'] % 2)) +
                                                           (32 * (ivs['spDefense'] % 2))) * 15) / 63))],
            'pokerus': {
                'days': int(sections['M'][0]) & 0xF,
                'strain': int(sections['M'][0]) >> 0x4,
            },
            'metLocation': location_list[int(sections['M'][1])],
            'origins': {
                'metLevel': int(struct.unpack('<H', sections['M'][2:4])[0]) & 0x7F,
                'hatched': False if int(struct.unpack('<H', sections['M'][2:4])[0]) & 0x7F else True,
                'game': OriginGame((int(struct.unpack('<H', sections['M'][2:4])[0]) >> 0x7) & 0xF),
                'ball': item_list[(int(struct.unpack('<H', sections['M'][2:4])[0]) >> 0xB) & 0xF]
            },
            'ability': pokemon_list[name]['ability'][min(int(section_m >> 31) & 1, len(pokemon_list[name]['ability']) - 1)],
            'type': pokemon_list[name]['type']
        }
        return pokemon

    except:
        console.print_exception(show_locals=True)


def GetParty() -> dict:
    """
    Checks how many Pokémon are in the trainer's party, decodes and returns them all.

    :return: party (dict)
    """
    try:
        party = {}
        party_count = int.from_bytes(ReadSymbol('gPlayerPartyCount', size=1))
        if party_count:
            for p in range(party_count):
                o = p * 100
                while not (mon := ParsePokemon(ReadSymbol('gPlayerParty', o, o+100))):
                    continue
                else:
                    party[p] = mon
            return party
        return {}
    except:
        console.print_exception(show_locals=True)


def GetOpponent() -> dict:
    """
    Gets the current opponent/encounter from `gEnemyParty`, decodes and returns.

    :return: opponent (dict)
    """
    try:
        return ParsePokemon(ReadSymbol('gEnemyParty')[:100])
    except:
        console.print_exception(show_locals=True)


last_opid = ReadSymbol('gEnemyParty', size=4)


def OpponentChanged() -> bool:
    """
    Checks if the current opponent/encounter from `gEnemyParty` has changed since the function was last called.
    Very fast way to check as this only reads the first 4 bytes (PID) and does not decode the Pokémon data.

    :return: True if opponent changed, otherwise False (bool)
    """
    try:
        global last_opid
        opponent_pid = ReadSymbol('gEnemyParty', size=4)
        if opponent_pid != last_opid:
            last_opid = opponent_pid
            return True
        else:
            return False
    except:
        console.print_exception(show_locals=True)
        return False


def GetItems() -> dict:
    """
    Get all items and their quantities from the PC, Items pocket, Key Items pocket, Poké Balls pocket, TMs & HMs pocket,
    Berries pocket.

    :return: trainer's items (dict)
    """
    try:
        items = {}
        pockets = ['PC', 'Items', 'Key Items', 'Poké Balls', 'TMs & HMs', 'Berries']
        for pocket in pockets:
            items[pocket] = {}

        b_Items = GetSaveBlock(1, mGBA.item_offsets[0][0], mGBA.item_offsets[4][0] + mGBA.item_offsets[4][1])

        for i in range(6):
            p = mGBA.item_offsets[i][0] - mGBA.item_offsets[0][0]
            for j in range(0, int(mGBA.item_offsets[i][1] / 4)):
                q = struct.unpack('<H', b_Items[p+(j*4+2):p+(j*4+4)])[0]
                quantity = int(q ^ mGBA.item_key) if i != 0 else q
                item = {
                    'name': item_list[int(struct.unpack('<H', b_Items[p+(j*4):p+(j*4+2)])[0])],
                    'quantity': quantity
                }
                items[pockets[i]][j] = item
        return items
    except:
        console.print_exception(show_locals=True)
