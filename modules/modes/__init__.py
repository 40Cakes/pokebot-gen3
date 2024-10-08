"""Contains modes of operation for the bot."""

from typing import TYPE_CHECKING, Type

from ._interface import BattleAction, BotListener, BotMode, BotModeError, FrameInfo
from ..plugins import plugin_get_additional_bot_listeners, plugin_get_additional_bot_modes

if TYPE_CHECKING:
    from modules.roms import ROM

_bot_modes: list[Type[BotMode]] = []


def get_bot_modes() -> list[Type[BotMode]]:
    global _bot_modes

    if len(_bot_modes) == 0:
        from .berry_blend import BerryBlendMode
        from .bunny_hop import BunnyHopMode
        from .daycare import DaycareMode
        from .feebas import FeebasMode
        from .fishing import FishingMode
        from .game_corner import GameCornerMode
        from .kecleon import KecleonMode
        from .level_grind import LevelGrindMode
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
        from .sweet_scent import SweetScentMode

        _bot_modes = [
            BerryBlendMode,
            BunnyHopMode,
            DaycareMode,
            FeebasMode,
            FishingMode,
            GameCornerMode,
            KecleonMode,
            LevelGrindMode,
            NuggetBridgeMode,
            PuzzleSolverMode,
            RoamerResetMode,
            RockSmashMode,
            SpinMode,
            StartersMode,
            StaticRunAway,
            StaticGiftResetsMode,
            StaticSoftResetsMode,
            SweetScentMode,
            SudowoodoMode,
        ]

        for mode in plugin_get_additional_bot_modes():
            _bot_modes.append(mode)

    return _bot_modes


def get_bot_mode_names() -> list[str]:
    result = ["Manual"]
    result.extend(mode.name() for mode in get_bot_modes())
    return result


def get_bot_mode_by_name(name: str) -> Type[BotMode] | None:
    return next((mode for mode in get_bot_modes() if mode.name() == name), None)


def get_bot_listeners(rom: "ROM") -> list[BotListener]:
    from ._listeners import (
        BattleListener,
        FishingListener,
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
        FishingListener(),
        EggHatchListener(),
        TrainerApproachListener(),
        RepelListener(),
        PoisonListener(),
        SafariZoneListener(),
        WhiteoutListener(),
    ]
    if rom.is_emerald:
        listeners.append(PokenavListener())
    for listener in plugin_get_additional_bot_listeners():
        listeners.append(listener)
    return listeners
