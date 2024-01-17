"""Contains modes of operation for the bot."""

from ._interface import BotMode, BotModeError
from typing import Type

_bot_modes: list[Type[BotMode]] = []


def get_bot_modes() -> list[Type[BotMode]]:
    global _bot_modes

    if len(_bot_modes) == 0:
        from .ancient_legendaries import AncientLegendariesMode
        from .bunny_hop import BunnyHopMode
        from .fishing import FishingMode
        from .game_corner import GameCornerMode
        from .roamer_reset import RoamerResetMode
        from .spin import SpinMode
        from .starters import StartersMode
        from .sudowoodo import SudowoodoMode
        from .tower_duo import TowerDuoMode
        from .static_run_away import StaticRunAway
        from .static_gift_resets import StaticGiftResetsMode
        from .static_soft_resets import StaticSoftResetsMode

        _bot_modes = [
            SpinMode,
            StartersMode,
            FishingMode,
            BunnyHopMode,
            StaticSoftResetsMode,
            StaticGiftResetsMode,
            GameCornerMode,
            SudowoodoMode,
            TowerDuoMode,
            StaticRunAway,
            AncientLegendariesMode,
            RoamerResetMode,
        ]

    return _bot_modes


def get_bot_mode_names() -> list[str]:
    result = ["Manual"]
    for mode in get_bot_modes():
        result.append(mode.name())
    return result


def get_bot_mode_by_name(name: str) -> Type[BotMode] | None:
    for mode in get_bot_modes():
        if mode.name() == name:
            return mode
    return None
