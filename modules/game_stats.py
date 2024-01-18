from enum import Enum

from modules.context import context
from modules.memory import get_save_block, unpack_uint32


class GameStat(Enum):
    SAVED_GAME = 0
    FIRST_HOF_PLAY_TIME = 1
    STARTED_TRENDS = 2
    PLANTED_BERRIES = 3
    TRADED_BIKES = 4
    STEPS = 5
    GOT_INTERVIEWED = 6
    TOTAL_BATTLES = 7
    WILD_BATTLES = 8
    TRAINER_BATTLES = 9
    ENTERED_HOF = 10
    POKEMON_CAPTURES = 11
    FISHING_ENCOUNTERS = 12
    HATCHED_EGGS = 13
    EVOLVED_POKEMON = 14
    USED_POKECENTER = 15
    RESTED_AT_HOME = 16
    ENTERED_SAFARI_ZONE = 17
    USED_CUT = 18
    USED_ROCK_SMASH = 19
    MOVED_SECRET_BASE = 20
    POKEMON_TRADES = 21
    UNKNOWN_22 = 22
    LINK_BATTLE_WINS = 23
    LINK_BATTLE_LOSSES = 24
    LINK_BATTLE_DRAWS = 25
    USED_SPLASH = 26
    USED_STRUGGLE = 27
    SLOT_JACKPOTS = 28
    CONSECUTIVE_ROULETTE_WINS = 29
    ENTERED_BATTLE_TOWER = 30
    UNKNOWN_31 = 31
    BATTLE_TOWER_SINGLES_STREAK = 32
    POKEBLOCKS = 33
    POKEBLOCKS_WITH_FRIENDS = 34
    WON_LINK_CONTEST = 35
    ENTERED_CONTEST = 36
    WON_CONTEST = 37
    SHOPPED = 38
    USED_ITEMFINDER = 39
    GOT_RAINED_ON = 40
    CHECKED_POKEDEX = 41
    RECEIVED_RIBBONS = 42
    JUMPED_DOWN_LEDGES = 43
    WATCHED_TV = 44
    CHECKED_CLOCK = 45
    WON_POKEMON_LOTTERY = 46
    USED_DAYCARE = 47
    RODE_CABLE_CAR = 48
    ENTERED_HOT_SPRINGS = 49
    NUM_UNION_ROOM_BATTLES = 50
    PLAYED_BERRY_CRUSH = 51


def get_game_stat(game_stat: GameStat) -> int:
    if context.rom.is_rs:
        game_stats_offset = 0x1540
        encryption_key_offset = 0xAC
    elif context.rom.is_emerald:
        game_stats_offset = 0x159C
        encryption_key_offset = 0xAC
    else:
        game_stats_offset = 0x1200
        encryption_key_offset = 0xF20

    game_stats_offset += game_stat.value * 4
    encryption_key = unpack_uint32(get_save_block(2, encryption_key_offset, size=4))
    return unpack_uint32(get_save_block(1, game_stats_offset, size=4)) ^ encryption_key
