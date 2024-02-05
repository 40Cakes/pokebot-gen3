"""Contains modes of operation for the bot."""

from typing import Type, TYPE_CHECKING

from ._interface import BotMode, BotModeError, FrameInfo, BotListener, BattleAction

if TYPE_CHECKING:
    from modules.roms import ROM

_bot_modes: list[Type[BotMode]] = []


def get_bot_modes() -> list[Type[BotMode]]:
    global _bot_modes

    if len(_bot_modes) == 0:
        from .bunny_hop import BunnyHopMode
        from .fishing import FishingMode
        from .game_corner import GameCornerMode
        from .nugget_bridge import NuggetBridgeMode
        from .puzzle_solver import PuzzleSolverMode
        from .roamer_reset import RoamerResetMode
        from .rock_smash import RockSmashMode
        from .spin import SpinMode
        from .starters import StartersMode
        from .sudowoodo import SudowoodoMode
        from .static_run_away import StaticRunAway
        from .static_gift_resets import StaticGiftResetsMode
        from .static_soft_resets import StaticSoftResetsMode
        from .random import RandomMode

        _bot_modes = [
            BunnyHopMode,
            FishingMode,
            GameCornerMode,
            NuggetBridgeMode,
            PuzzleSolverMode,
            RandomMode,
            RoamerResetMode,
            RockSmashMode,
            SpinMode,
            StartersMode,
            StaticRunAway,
            StaticGiftResetsMode,
            StaticSoftResetsMode,
            SudowoodoMode,
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


def get_bot_listeners(rom: "ROM") -> list[BotListener]:
    from ._listeners import (
        BattleListener,
        PokenavListener,
        EggHatchListener,
        TrainerApproachListener,
        RepelListener,
        PoisonListener,
        SafariZoneListener,
        WhiteoutListener,
    )

    listeners = [
        BattleListener(),
        EggHatchListener(),
        TrainerApproachListener(),
        RepelListener(),
        PoisonListener(),
        SafariZoneListener(),
        WhiteoutListener(),
    ]
    if rom.is_emerald:
        listeners.append(PokenavListener())
    return listeners
