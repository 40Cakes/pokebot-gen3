from enum import IntEnum  # https://docs.python.org/3/library/enum.html


class GameState(IntEnum):
    OVERWORLD = 80
    MISC_MENU = 255
    BAG_MENU = 0
    # Needs further investigation; these values have multiple meanings
    BATTLE = 3
    # BATTLE_2 = 2
    # FOE_DEFEATED = 5
