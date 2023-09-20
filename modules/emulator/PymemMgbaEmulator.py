import struct

from pymem import Pymem

from modules.emulator.BaseEmulator import Emulator


class PymemMgbaEmulator(Emulator):
    def __init__(self, proc: Pymem):
        self.proc = proc

        self.p_EWRAM = self._GetPointer(0x02849A28,
                                        offsets=[0x40, 0x58, 0x3D8, 0x10, 0x80, 0x28, 0x0])
        self.p_IWRAM = self._GetPointer(0x02849A28,
                                        offsets=[0x40, 0x28, 0x58, 0x10, 0xF0, 0x30, 0x0])
        self.p_ROM = self._GetPointer(0x02849A28,
                                      offsets=[0x40, 0x28, 0x58, 0x10, 0xb8, 0x38, 0x0])
        self.p_Input = self._GetPointer(0x02849A28,
                                        offsets=[0x20, 0x58, 0x6D8, 0x420, 0x168, 0x420, 0xDE4])
        self.p_Framecount = self._GetPointer(0x02849A28,
                                             offsets=[0x40, 0x58, 0x10, 0x1C0, 0x0, 0x90, 0xF0])
        self.game_version = int.from_bytes(self.proc.read_bytes(self.p_ROM + 0xBC, 1))

    def _GetPointer(self, base_offset, offsets):
        """
        This function will "follow a bouncing ball" of offsets and return a pointer to the desired memory location.
        When mGBA is launched, the locations of the GBA memory domains will be in a random location, this ensures that
        the same memory domain can be found reliably, every time.
        For more information check out: https://www.youtube.com/watch?v=YaFlh2pIKAg

        :param base_offset: offset from the base address
        :param offsets: memory offsets to follow
        :return: memory pointer to the desired address
        """
        addr = self.proc.read_longlong(self.proc.base_address + base_offset)
        for i in offsets:
            if i != offsets[-1]:
                addr = self.proc.read_longlong(addr + i)
        return addr + offsets[-1]

    def GetFrameCount(self) -> int:
        return struct.unpack('<I', self.proc.read_bytes(self.p_Framecount, length=4))[0]

    def GetGameCode(self) -> str:
        return self.proc.read_bytes(self.p_ROM + 0xAC, 4).decode('utf-8')

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
        return self.proc.read_bytes(self.p_ROM + offset, length)

    def ReadEWRAM(self, offset: int, length: int = 1) -> bytes:
        return self.proc.read_bytes(self.p_EWRAM + offset, length)

    def ReadIWRAM(self, offset: int, length: int = 1) -> bytes:
        return self.proc.read_bytes(self.p_IWRAM + offset, length)

    def WriteBus(self, address: int, data: bytes) -> None:
        bank = address >> 0x18
        if bank == 0x2:
            return self.WriteEWRAM(address & 0xFFFFFF, data)
        elif bank == 0x3:
            return self.WriteIWRAM(address & 0xFFFFFF, data)
        else:
            raise RuntimeError("Invalid memory address for writing: " + str(address))

    def WriteEWRAM(self, offset: int, data: bytes) -> None:
        self.proc.write_bytes(self.p_EWRAM + offset, data, len(data))

    def WriteIWRAM(self, offset: int, data: bytes) -> None:
        self.proc.write_bytes(self.p_IWRAM + offset, data, len(data))

    def GetInputs(self) -> int:
        return struct.unpack('h', self.proc.read_bytes(self.p_Input, 2))[0]

    def SetInputs(self, inputs: int):
        self.proc.write_bytes(self.p_Input, struct.pack('<H', inputs), 2)

    def RunSingleFrame(self) -> None:
        starting_frame_count = self.GetFrameCount()
        while self.GetFrameCount() == starting_frame_count:
            pass
