import struct
from enum import IntEnum

from modules.Console import console
from modules.Game import DecodeString
from modules.Gui import GetROM
from modules.Memory import GetSaveBlock, ReadSymbol
from modules.data.MapData import MapRSE, MapFRLG


class AvatarFlag(IntEnum):
    """
    The various states of the trainer pertaning to movement

    Reference: https://github.com/pret/pokeemerald/blob/104e81b359d287668cee613f6604020a6e7228a3/include/global.fieldmap.h
    """

    PLAYER_AVATAR_FLAG_ON_FOOT = 1 << 0
    PLAYER_AVATAR_FLAG_MACH_BIKE = 1 << 1
    PLAYER_AVATAR_FLAG_ACRO_BIKE = 1 << 2
    PLAYER_AVATAR_FLAG_SURFING = 1 << 3
    PLAYER_AVATAR_FLAG_UNDERWATER = 1 << 4
    PLAYER_AVATAR_FLAG_CONTROLLABLE = 1 << 5
    PLAYER_AVATAR_FLAG_FORCED_MOVE = 1 << 6
    PLAYER_AVATAR_FLAG_DASH = 1 << 7


ON_BIKE = AvatarFlag.PLAYER_AVATAR_FLAG_MACH_BIKE | AvatarFlag.PLAYER_AVATAR_FLAG_ACRO_BIKE


def FacingDir(direction: int) -> str:
    """
    Returns the direction the trainer is currently facing.

    :param direction: int
    :return: trainer facing direction (str)
    """
    match direction:
        case 0x11:
            return "Down"
        case 0x22:
            return "Up"
        case 0x33:
            return "Left"
        case 0x44:
            return "Right"


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
        b_gTasks = ReadSymbol("gTasks", offset=0x57, size=3)
        b_gObjectEvents = ReadSymbol("gObjectEvents", size=25)
        b_gPlayerAvatar = ReadSymbol("gPlayerAvatar")

        if b_Save is None:
            return {
                "name": "",
                "gender": "",
                "tid": 0,
                "sid": 0,
                "map": (0, 0),
                "map_name": "",
                "coords": (0, 0),
                "on_bike": False,
                "facing": None,
            }

        trainer = {
            "name": DecodeString(b_Save[0:7]),
            "gender": "girl" if int(b_Save[8]) else "boy",
            "tid": int(struct.unpack("<H", b_Save[10:12])[0]),
            "sid": int(struct.unpack("<H", b_Save[12:14])[0]),
            "map": (int(b_gTasks[2]), int(b_gTasks[1])),
            "map_name": "",
            "coords": (int(b_gObjectEvents[16]) - 7, int(b_gObjectEvents[18]) - 7),
            "on_bike": (int(b_gPlayerAvatar[0]) & ON_BIKE) != 0,
            "facing": FacingDir(int(b_gObjectEvents[24])),
        }

        try:
            if GetROM().game_title in ["POKEMON EMER", "POKEMON RUBY", "POKEMON SAPP"]:
                trainer["map_name"] = MapRSE(trainer["map"]).name
            else:
                trainer["map_name"] = MapFRLG(trainer["map"]).name
        except ValueError:
            trainer["map_name"] = "UNKNOWN"

        return trainer

    except SystemExit:
        raise
    except:
        console.print_exception(show_locals=True)
