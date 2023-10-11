import json
import struct
import numpy

from modules.Console import console
from modules.Files import ReadFile
from modules.Gui import GetEmulator
from modules.Inputs import WaitFrames
from modules.Items import item_list
from modules.Memory import ReadSymbol

moves_list = json.loads(ReadFile('./modules/data/moves.json'))
names_list = json.loads(ReadFile('./modules/data/names.json'))
natures_list = json.loads(ReadFile('./modules/data/natures.json'))
nat_ids_list = json.loads(ReadFile('./modules/data/nat-ids.json'))
exp_groups_list = json.loads(ReadFile('./modules/data/exp-groups.json'))
pokemon_list = json.loads(ReadFile('./modules/data/pokemon.json'))
location_list = json.loads(ReadFile('./modules/data/locations.json'))
hidden_powers_list = json.loads(ReadFile('./modules/data/hidden-powers.json'))


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
        pid = struct.unpack('<I', b_Pokemon[0:4])[0]
        ot = struct.unpack('<I', b_Pokemon[4:8])[0]

        # Unpack data substructures
        # https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_structure_(Generation_III)
        # https://bulbapedia.bulbagarden.net/wiki/Pok%C3%A9mon_data_substructures_(Generation_III)
        key = ot ^ pid
        data = b_Pokemon[32:80]
        order = pid % 0x18

        order_string = substructs[order]
        sections = {}
        checksum = 0
        for i in range(0, 4):
            section = order_string[i]
            section_data = data[(i*12):((i+1)*12)]
            decrypted = DecryptSubSection(section_data, key)
            sections[section] = decrypted
            for c in range(0, 6):
                checksum += struct.unpack('<H', decrypted[c*2:(c*2)+2])[0]
                checksum &= 0xFFFF

        valid = True if not (struct.unpack('<H', b_Pokemon[28:30])[0] ^ checksum) else False
        if not valid:
            return None

        tid = int(struct.unpack('<H', b_Pokemon[4:6])[0])
        sid = int(struct.unpack('<H', b_Pokemon[6:8])[0])
        id = int(struct.unpack('<H', sections['G'][0:2])[0])
        name = SpeciesName(id)
        flags = int(b_Pokemon[19])
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
        met_location = int(sections['M'][1])

        pokemon = {
            'name': name,
            'id': id,
            'natID': NationalDexID(id),
            'species': int(struct.unpack('<H', sections['G'][0:2])[0]),
            'pid': pid,
            'nature': natures_list[pid % 0x19] if pid % 0x19 < len(natures_list) else None,
            'language': Language(int(b_Pokemon[18])),
            'shinyValue': shiny_value,
            'shiny': True if shiny_value < 8 else False,
            'ot': {
                'tid': tid,
                'sid': sid
            },
            'checksum': struct.unpack('<H', b_Pokemon[28:30])[0],
            'calculatedChecksum': checksum,
            'hasSpecies': (flags >> 0x1) & 0x1,
            'isEgg': (flags >> 0x2) & 0x1,
            'level': int(b_Pokemon[84]) if len(b_Pokemon) > 80 else 0,
            'expGroup': exp_groups_list[id - 1] if id - 1 < len(exp_groups_list) else None,
            'item': {
                'id': item_id,
                'name': item_list[item_id] if item_id < len(item_list) else None
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
            } if len(b_Pokemon) > 80 else None,
            'stats': {
                'hp': int(b_Pokemon[86]),
                'maxHP': int(b_Pokemon[88]),
                'attack': int(b_Pokemon[90]),
                'defense': int(b_Pokemon[92]),
                'speed': int(b_Pokemon[94]),
                'spAttack': int(b_Pokemon[96]),
                'spDefense': int(b_Pokemon[98])
            } if len(b_Pokemon) > 80 else None,

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
            'metLocation': location_list[met_location] if met_location < len(location_list) else 'Traded',
            'origins': {
                'metLevel': int(struct.unpack('<H', sections['M'][2:4])[0]) & 0x7F,
                'hatched': False if int(struct.unpack('<H', sections['M'][2:4])[0]) & 0x7F else True,
                'game': OriginGame((int(struct.unpack('<H', sections['M'][2:4])[0]) >> 0x7) & 0xF),
                'ball': item_list[(int(struct.unpack('<H', sections['M'][2:4])[0]) >> 0xB) & 0xF] if \
                    (int(struct.unpack('<H', sections['M'][2:4])[0]) >> 0xB) & 0xF < len(item_list) else None
            },
            'ability': pokemon_list[name]['ability'][min(int(section_m >> 31) & 1, len(pokemon_list[name]['ability']) - 1)],
            'type': pokemon_list[name]['type'] if name in pokemon_list else None
        }
        return pokemon

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return None


def GetParty() -> list[dict]:
    """
    Checks how many Pokémon are in the trainer's party, decodes and returns them all.

    :return: party (list)
    """
    party = []
    party_count = int.from_bytes(ReadSymbol('gPlayerPartyCount', size=1))
    for p in range(party_count):
        o = p * 100
        mon = ParsePokemon(ReadSymbol('gPlayerParty', o, o+100))

        # It's possible for party data to be written while we are trying to read it, in which case
        # the checksum would be wrong and `ParsePokemon()` returns `None`.
        #
        # In order to still get a valid result, we will 'peek' into next frame's memory by
        # (1) advancing the emulation by one frame, (2) reading the memory, (3) restoring the previous
        # frame's state so we don't mess with frame accuracy.
        if mon is None:
            mon = GetEmulator().PeekFrame(lambda: ParsePokemon(ReadSymbol('gPlayerParty', o, o+100)))
            if mon is None:
                raise RuntimeError(f'Party Pokemon #{p+1} was invalid for two frames in a row.')

        party.append(mon)
    return party


def GetOpponent() -> dict:
    """
    Gets the current opponent/encounter from `gEnemyParty`, decodes and returns.

    :return: opponent (dict)
    """
    mon = ParsePokemon(ReadSymbol('gEnemyParty')[:100])

    # See comment in `GetParty()`
    if mon is None:
        mon = GetEmulator().PeekFrame(lambda: ParsePokemon(ReadSymbol('gEnemyParty')[:100]))
        if mon is None:
            raise RuntimeError(f'Opponent Pokemon was invalid for two frames in a row.')

    return mon


last_opid = b'\x00\x00\x00\x00' # ReadSymbol('gEnemyParty', size=4)


def OpponentChanged() -> bool:
    """
    Checks if the current opponent/encounter from `gEnemyParty` has changed since the function was last called.
    Very fast way to check as this only reads the first 4 bytes (PID) and does not decode the Pokémon data.

    :return: True if opponent changed, otherwise False (bool)
    """
    try:
        global last_opid
        opponent_pid = ReadSymbol('gEnemyParty', size=4)
        if opponent_pid != last_opid and opponent_pid != b'\x00\x00\x00\x00':
            last_opid = opponent_pid
            return True
        else:
            return False
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
        return False
