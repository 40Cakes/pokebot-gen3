from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from modules.gui import PokebotGui
    from modules.libmgba import LibmgbaEmulator
    from modules.profiles import Profile
    from modules.roms import ROM


class BotContext:
    def __init__(self, initial_bot_mode: str = 'manual'):
        self.emulator: Optional["LibmgbaEmulator"] = None
        self.gui: Optional["PokebotGui"] = None
        self.profile: Optional["Profile"] = None
        self.debug: bool = False

        self._current_message: str = ''

        self._current_bot_mode: str = initial_bot_mode
        self._previous_bot_mode: str = 'manual'

    @property
    def message(self) -> str:
        return self._current_message

    @message.setter
    def message(self, new_message: str) -> None:
        self._current_message = new_message
        self._update_gui()

    @property
    def emulation_speed(self) -> float:
        if not self.emulator.get_throttle():
            return 0
        else:
            return self.emulator.get_speed_factor()

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
        if self._current_bot_mode == "manual":
            self._current_bot_mode = self._previous_bot_mode
            self._previous_bot_mode = "manual"
        else:
            self._previous_bot_mode = self._current_bot_mode
            self._current_bot_mode = "manual"
        self._update_gui()

    @property
    def audio(self) -> bool:
        if self.emulator:
            return self.emulator.get_audio_enabled()
        else:
            return False

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
        if self.emulator:
            return self.emulator.get_video_enabled()
        else:
            return False

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
        if self.profile:
            return self.profile.rom
        else:
            return None

    def _update_gui(self) -> None:
        if self.gui:
            self.gui.on_settings_updated()


context = BotContext()
