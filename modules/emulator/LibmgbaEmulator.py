import atexit
import os.path
import time

import mgba.core
import mgba.gba
import mgba.image
import mgba.log
import mgba.png
import mgba.vfs

from mgba import libmgba_version_string
from modules.emulator.BaseEmulator import Emulator
from modules.Gui import Gui
from modules.Profiles import Profile


class PerformanceTracker:
    last_render_time: float = 0.0
    last_frame_time: float = 0.0

    current_fps: int = 0
    frame_counter: int = 0
    frame_counter_time: int = 0

    def TrackRender(self) -> None:
        self.last_render_time = time.time()

    def TimeSinceLastRender(self) -> float:
        return time.time() - self.last_render_time

    def TrackFrame(self) -> None:
        self.last_frame_time = time.time()
        current_second = int(time.time())
        if self.frame_counter_time != current_second:
            self.current_fps = self.frame_counter
            self.frame_counter = 0
            self.frame_counter_time = current_second

        self.frame_counter += 1

    def TimeSinceLastFrame(self) -> float:
        return time.time() - self.last_frame_time


class LibMgbaEmulator(Emulator):
    def __init__(self, profile: Profile):
        print(f"Running {libmgba_version_string()}")

        # Prevents relentless spamming to stdout by libmgba
        mgba.log.silence()

        self._profile = profile
        self._core = mgba.core.load_path(str(profile.rom.file))
        if not self._core:
            raise RuntimeError("Could not load ROM file " + str(profile.rom.file))

        self._current_save_path = profile.path / "current_save.sav"
        if not self._current_save_path.exists():
            with open(self._current_save_path, "w"): pass
        self._save = mgba.vfs.open_path(str(self._current_save_path), "r+")
        self._core.load_save(self._save)

        self._screen = mgba.image.Image(*self._core.desired_video_dimensions())
        self._core.set_video_buffer(self._screen)
        self._core.reset()

        self._current_state_path = profile.path / "current_state.ss1"
        if self._current_state_path.exists():
            state_file = mgba.vfs.open_path(str(self._current_state_path))
            self._core.load_state(state_file)

        self._memory: mgba.gba.GBAMemory = self._core.memory

        self._gui = Gui(self, self._core.desired_video_dimensions())

        self._performance_tracker = PerformanceTracker()
        self._throttled = False

        # How often a frame should be emulated
        self._target_seconds_per_frame = 1 / 60

        # How often a frame should be drawn to the screen (can be less frequent than the emulation rate)
        self._target_seconds_per_render = 1 / 60

        atexit.register(self.Shutdown)

        def OnSavedataUpdated():
            with open(self._current_save_path, "rb") as save_file:
                saves_directory = profile.path / "saves"
                if not saves_directory.exists():
                    saves_directory.mkdir()
                with open(saves_directory / time.strftime("%Y-%m-%d_%H-%M-%S.sav"), "wb") as backup_file:
                    backup_file.write(save_file.read())

        # self._core._callbacks.core_crashed.append(lambda: print('core crash'))
        self._core._callbacks.savedata_updated.append(OnSavedataUpdated)
        # self._core._callbacks.sleep.append(lambda: print('sleep'))
        # self._core._callbacks.video_frame_ended.append(lambda: print('frame ended'))
        # self._core._callbacks.video_frame_started.append(lambda: print('frame started'))
        # self._core._callbacks.keys_read.append(lambda: print('keys read'))

    def Shutdown(self) -> None:
        print("Shutting down...")
        state = self._core.save_state()
        states_directory = self._profile.path / "states"
        if not states_directory.exists():
            states_directory.mkdir()
        backup_path = states_directory / (time.strftime("%Y-%m-%d_%H-%M-%S") + ".ss1")
        with open(backup_path, "wb") as state_file:
            state_file.write(state)
        if backup_path.stat().st_size > 0:
            with open(self._current_state_path, "wb") as state_file:
                state_file.write(state)

    def GetFrameCount(self) -> int:
        return self._core.frame_counter

    def GetGameCode(self) -> str:
        # The [4:8] range strips off the `AGB-` prefix that every game has.
        return self._core.game_code[4:8]

    def GetThrottle(self) -> bool:
        return self._throttled

    def SetThrottle(self, is_throttled: bool) -> None:
        self._throttled = is_throttled
        if is_throttled:
            self._target_seconds_per_render = 1 / 60
        else:
            self._target_seconds_per_render = 1 / 20

    def SetTargetSecondsPerFrame(self, seconds_per_frame) -> None:
        self._target_seconds_per_frame = seconds_per_frame

    def SaveState(self) -> None:
        self._core.save_state(1)

    def ReadBus(self, address: int, length: int = 1) -> bytes:
        bank = address >> 0x18
        if bank == 0x2:
            return self.ReadEWRAM(address & 0xFFFFFF, length)
        elif bank == 0x3:
            return self.ReadIWRAM(address & 0xFFFFFF, length)
        elif bank >= 0x8:
            return self.ReadROM(address - 0x8000000, length)
        else:
            raise RuntimeError("Invalid memory address for reading: " + str(address))

    def ReadROM(self, offset: int, length: int = 1) -> bytes:
        return self._memory.rom[slice(offset, offset + length)]

    def ReadEWRAM(self, offset: int, length: int = 1) -> bytes:
        return self._memory.wram[slice(offset, offset + length)]

    def ReadIWRAM(self, offset: int, length: int = 1) -> bytes:
        return self._memory.iwram[slice(offset, offset + length)]

    def WriteBus(self, address: int, data: bytes) -> None:
        bank = address >> 0x18
        if bank == 0x2:
            return self.WriteEWRAM(address & 0xFFFFFF, data)
        elif bank == 0x3:
            return self.WriteIWRAM(address & 0xFFFFFF, data)
        else:
            raise RuntimeError("Invalid memory address for writing: " + str(address))

    def WriteEWRAM(self, offset: int, data: bytes) -> None:
        self._memory.wram.u8[slice(offset, len(data))] = data

    def WriteIWRAM(self, offset: int, data: bytes) -> None:
        self._memory.iwram.u8[slice(offset, len(data))] = data

    def GetInputs(self) -> int:
        return self._core._core.getKeys(self._core._core)

    def SetInputs(self, inputs: int):
        self._core._core.setKeys(self._core._core, inputs)

    def TakeScreenshot(self):
        png_directory = self._profile.path / "screenshots"
        if not png_directory.exists():
            png_directory.mkdir()
        png_path = png_directory / (time.strftime("%Y-%m-%d_%H-%M-%S") + "_" + str(self.GetFrameCount()) + ".png")
        with open(png_path, "wb") as file:
            self._screen.to_pil().convert("RGB").save(file, format="PNG")

    def RunSingleFrame(self) -> None:
        self._core.run_frame()

        if self._performance_tracker.TimeSinceLastRender() >= self._target_seconds_per_render:
            self._gui.UpdateImage(self._screen.to_pil())
            self._performance_tracker.TrackRender()

        if self._throttled and self._performance_tracker.TimeSinceLastFrame() < self._target_seconds_per_frame:
            time.sleep(max(0.0, self._target_seconds_per_frame - self._performance_tracker.TimeSinceLastFrame()))

        self._performance_tracker.TrackFrame()
