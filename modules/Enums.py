from enum import IntEnum


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
    MAIN_MENU = 903
    WHITEOUT = 904
    GARBAGE_COLLECTION = 905
    EVOLUTION = 906
    UNKNOWN = 999


class TaskFunc(IntEnum):
    # Menus
    LEARN_MOVE = 1
    START_MENU = 2
    PARTY_MENU = 3
    # Misc
    DUMMY_TASK = 0


class CursorOptionEFRLG(IntEnum):
    SUMMARY = 0
    SWITCH = 1
    CANCEL_1 = 2
    ITEM = 3
    GIVE_ITEM = 4
    TAKE_ITEM = 5
    MAIL = 6
    TAKE_MAIL = 7
    READ = 8
    CANCEL_2 = 9
    SHIFT = 10
    SEND_OUT = 11
    ENTER = 12
    NO_ENTRY = 13
    STORE = 14
    REGISTER = 15
    TRADE_1 = 16
    TRADE_2 = 17
    TOSS = 18
    CUT = 19
    FLASH = 20
    ROCK_SMASH = 21
    STRENGTH = 22
    SURF = 23
    FLY = 24
    DIVE = 25
    WATERFALL = 26
    TELEPORT = 27
    DIG = 28
    SECRET_POWER = 29
    MILK_DRINK = 30
    SOFTBOILED = 31
    SWEET_SCENT = 32


class CursorOptionRS(IntEnum):
    SUMMARY = 0
    SWITCH = 1
    ITEM = 2
    CANCEL_1 = 3
    GIVE_ITEM = 4
    TAKE_ITEM = 5
    TAKE_MAIL = 6
    MAIL = 7
    READ = 8
    CANCEL_2 = 9
    CUT = 10
    FLASH = 11
    ROCK_SMASH = 12
    STRENGTH = 13
    SURF = 14
    FLY = 15
    DIVE = 16
    WATERFALL = 17
    TELEPORT = 18
    DIG = 19
    SECRET_POWER = 20
    MILK_DRINK = 21
    SOFTBOILED = 22
    SWEET_SCENT = 23


class StartMenuOptionHoenn(IntEnum):
    POKEDEX = 0
    POKEMON = 1
    BAG = 2
    POKENAV = 3
    PLAYER = 4
    SAVE = 5
    OPTION = 6
    EXIT = 7
    RETIRE = 8
    PLAYER2 = 9


class StartMenuOptionKanto(IntEnum):
    POKEDEX = 0
    POKEMON = 1
    BAG = 2
    PLAYER = 3
    SAVE = 4
    OPTION = 5
    EXIT = 6
    RETIRE = 7
    PLAYER2 = 8
    MAX_STARTMENU_ITEMS = 8


class BattleState(IntEnum):
    # out-of-battle states
    OVERWORLD = 0
    EVOLVING = 1

    # battle states
    ACTION_SELECTION = 10
    MOVE_SELECTION = 11
    PARTY_MENU = 12
    SWITCH_POKEMON = 13
    LEARNING = 14

    # misc undetected state (move animations, buffering, etc)
    OTHER = 20
