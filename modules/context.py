from typing import Generator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.gui import PokebotGui
    from modules.libmgba import LibmgbaEmulator
    from modules.profiles import Profile
    from modules.roms import ROM

from modules.config import Config


class BotContext:
    def __init__(self, initial_bot_mode: str = "Manual"):
        self.config = Config()

        self.emulator: Optional["LibmgbaEmulator"] = None
        self.gui: Optional["PokebotGui"] = None
        self.profile: Optional["Profile"] = None
        self.debug: bool = False

        self._current_message: str = ""

        self.controller_stack: list[Generator] = []
        self.debug_action_stack: list[str] = []
        self.frame: int = 0
        self._current_bot_mode: str = initial_bot_mode
        self._previous_bot_mode: str = "Manual"

    def reload_config(self) -> None:
        """
        Triggers a config reload, reload the global config then specific profile config.
        """
        from modules.console import console

        try:
            new_config = Config()
            new_config.load(self.config.config_dir, strict=False)
            self.config = new_config
            console.print("[cyan]Profile settings loaded.[/]")
        except Exception as error:
            if self.debug:
                raise error
            console.print(
                "[bold red]The configuration could not be loaded, no changes have been made.[/]\n"
                "[bold yellow]This is probably due to a malformed file."
                "For more information run the bot with the --debug flag.[/]"
            )
        return

    @property
    def message(self) -> str:
        return self._current_message

    @message.setter
    def message(self, new_message: str) -> None:
        self._current_message = new_message
        self._update_gui()

    @property
    def emulation_speed(self) -> float:
        return self.emulator.get_speed_factor() if self.emulator.get_throttle() else 0

    @emulation_speed.setter
    def emulation_speed(self, new_speed: float) -> None:
        if self.emulator:
            if new_speed == 0:
                self.emulator.set_throttle(False)
            else:
                self.emulator.set_throttle(True)
                self.emulator.set_speed_factor(new_speed)
            self._update_gui()

    @property
    def bot_mode(self) -> str:
        return self._current_bot_mode

    @bot_mode.setter
    def bot_mode(self, new_bot_mode: str) -> None:
        if self._current_bot_mode != new_bot_mode:
            self._previous_bot_mode = self._current_bot_mode
            self._current_bot_mode = new_bot_mode
            self._update_gui()

    def toggle_manual_mode(self) -> None:
        if self._current_bot_mode == "Manual":
            self._current_bot_mode = self._previous_bot_mode
            self._previous_bot_mode = "Manual"
        else:
            self._previous_bot_mode = self._current_bot_mode
            self.set_manual_mode(enable_video_and_slow_down=False)
        self._update_gui()

    def set_manual_mode(self, enable_video_and_slow_down: bool = True) -> None:
        self.bot_mode = "Manual"
        self.emulator.reset_held_buttons()
        if enable_video_and_slow_down:
            from modules.gui.desktop_notification import desktop_notification

            self.emulation_speed = 1
            self.video = True
            desktop_notification(title="Manual Mode", message="The bot has switched to manual mode.")

    def debug_stepping_mode(self) -> None:
        if self.debug and self.gui and self.gui._emulator_screen:
            from modules.gui.desktop_notification import desktop_notification

            self.gui._emulator_screen.toggle_stepping_mode()
            self.video = True
            desktop_notification(title="Manual Mode", message="The bot has switched to stepping mode.")

    @property
    def audio(self) -> bool:
        return self.emulator.get_audio_enabled() if self.emulator else False

    @audio.setter
    def audio(self, audio_on: bool) -> None:
        if self.emulator:
            self.emulator.set_audio_enabled(audio_on)
            self._update_gui()

    def toggle_audio(self) -> None:
        if self.emulator:
            self.emulator.set_audio_enabled(not self.emulator.get_audio_enabled())
            self._update_gui()

    @property
    def video(self) -> bool:
        return self.emulator.get_video_enabled() if self.emulator else False

    @video.setter
    def video(self, video_on: bool) -> None:
        if self.emulator:
            self.emulator.set_video_enabled(video_on)
            self._update_gui()

    def toggle_video(self):
        if self.emulator:
            self.emulator.set_video_enabled(not self.emulator.get_video_enabled())
            self._update_gui()

    @property
    def rom(self) -> Optional["ROM"]:
        return self.profile.rom if self.profile else None

    def _update_gui(self) -> None:
        if self.gui:
            self.gui.on_settings_updated()


context = BotContext()
