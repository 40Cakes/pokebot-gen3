from typing import TYPE_CHECKING

from modules.context import context
from modules.game import set_rom
from modules.libmgba import LibmgbaEmulator

if TYPE_CHECKING:
    from pokebot import StartupSettings


class PokebotHeadless:
    def __init__(self, main_loop: callable, on_exit: callable):
        self._main_loop = main_loop
        self._on_exit = on_exit
        self.is_headless = True

    def run(self, startup_settings: "StartupSettings"):
        if startup_settings.profile is None:
            raise RuntimeError("Headless mode cannot be started without selecting a profile.")

        context.profile = startup_settings.profile
        context.config.load(startup_settings.profile.path, strict=False)
        set_rom(startup_settings.profile.rom)
        context.emulator = LibmgbaEmulator(startup_settings.profile, self._on_frame)
        context.audio = not startup_settings.no_audio
        context.video = not startup_settings.no_video
        context.emulation_speed = startup_settings.emulation_speed
        context.debug = False
        context.bot_mode = startup_settings.bot_mode

        self._main_loop()

    def on_settings_updated(self) -> None:
        pass

    def _on_frame(self):
        if context.emulator._performance_tracker.time_since_last_render() >= (1 / 60) * 1_000_000_000:
            context.emulator._performance_tracker.track_render()
