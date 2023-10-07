import struct

from modules.Console import console
from modules.Game import DecodeString
from modules.Memory import GetSaveBlock, ReadSymbol


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
        b_Save = GetSaveBlock(2, size=14)
        b_gTasks = ReadSymbol('gTasks', 0x57, 3)
        b_gObjectEvents = ReadSymbol('gObjectEvents', size=25)

        if b_Save is None:
            return {
                'name': '',
                'gender': '',
                'tid': 0,
                'sid': 0,
                'map': (0, 0),
                'coords': (0, 0),
                'on_bike': False,
                'facing': None
            }

        trainer = {
            'name': DecodeString(b_Save[0:7]),
            'gender': 'girl' if int(b_Save[8]) else 'boy',
            'tid': int(struct.unpack('<H', b_Save[10:12])[0]),
            'sid': int(struct.unpack('<H', b_Save[12:14])[0]),
            'map': (int(b_gTasks[2]), int(b_gTasks[1])),
            'coords': (int(b_gObjectEvents[16]) - 7, int(b_gObjectEvents[18]) - 7),
            'on_bike': True if int(b_gObjectEvents[5]) == 1 else False,
            'facing': FacingDir(int(b_gObjectEvents[24]))
        }
        return trainer
    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
