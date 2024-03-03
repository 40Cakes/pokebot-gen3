"""Contains modes of operation for the bot."""

from typing import TYPE_CHECKING, Type

from ._interface import BattleAction, BotListener, BotMode, BotModeError, FrameInfo

if TYPE_CHECKING:
    from modules.roms import ROM

_bot_modes: list[Type[BotMode]] = []


def get_bot_modes() -> list[Type[BotMode]]:
    global _bot_modes

    if len(_bot_modes) == 0:
        from .bunny_hop import BunnyHopMode
        from modules.modes.daycare import DaycareMode
        from .feebas import FeebasMode
        from .fishing import FishingMode
        from .game_corner import GameCornerMode
        from .kecleon import KecleonMode
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
        from .pokecenterloop import PokecenterLoopMode

        _bot_modes = [
            BunnyHopMode,
            DaycareMode,
            FeebasMode,
            FishingMode,
            GameCornerMode,
            KecleonMode,
            NuggetBridgeMode,
            PuzzleSolverMode,
            RoamerResetMode,
            RockSmashMode,
            SpinMode,
            StartersMode,
            StaticRunAway,
            StaticGiftResetsMode,
            StaticSoftResetsMode,
            SudowoodoMode,
            PokecenterLoopMode,
        ]

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
