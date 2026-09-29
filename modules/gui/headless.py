from typing import Callable, Never

from modules.context import context


class PokebotHeadless:
    def __init__(self, on_exit: Callable[[], None]):
        self._on_exit = on_exit
        self.is_headless = True

    def run_profile_selection(self) -> Never:
        raise RuntimeError("Headless mode cannot be started without passing a profile name on the command line.")

    def run_profile(self) -> None:
        pass

    def on_settings_updated(self) -> None:
        pass

    def on_frame(self):
        if context.emulator._performance_tracker.time_since_last_render() >= (1 / 60) * 1_000_000_000:
            context.emulator._performance_tracker.track_render()
