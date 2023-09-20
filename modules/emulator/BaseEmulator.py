class Emulator:
    def GetFrameCount(self) -> int:
        """
        Get the current frame count since the start of emulation.

        :return: frame count (int)
        """
        pass

    def GetGameCode(self) -> str:
        """
        Get the (short) game code as reported by the ROM -- without the
        `AGB-` prefix that every game uses.

        :return: The game code without `AGB-` prefix
        """
        pass

    def ReadBus(self, address: int, length: int = 1) -> bytes:
        """
        Reads a block of memory from an arbitrary address on the system
        bus. That means that you need to specify the full memory address
        rather than an offset relative to the start of a given memory
        area.

        This is helpful if you are working with the symbol table or
        pointers.

        :param address: The full memory address
        :param length: Number of bytes to be read
        :return: Data read from that memory location
        """
        pass

    def ReadROM(self, offset: int, length: int = 1) -> bytes:
        """
        Reads from ROM memory.

        :param offset: Starting address relative to the start of ROM memory
        :param length: Number of bytes to be read
        :return: Data read from that memory location
        """
        pass

    def ReadEWRAM(self, offset: int, length: int = 1) -> bytes:
        """
        Reads from EWRAM (the slower kind of RAM.)

        :param offset: Starting address relative to the start of EWRAM
        :param length: Number of bytes to be read
        :return: Data read from that memory location
        """
        pass

    def ReadIWRAM(self, offset: int, length: int = 1) -> bytes:
        """
        Reads from IWRAM (the faster kind of RAM.)

        :param offset: Starting address relative to the start of IWRAM
        :param length: Number of bytes to be read
        :return: Data read from that memory location
        """
        pass

    def WriteBus(self, address: int, data: bytes) -> None:
        """
        Writes to an arbitrary address on the system bus.
        See `ReadBus()` for what that means.

        :param address: The full memory address
        :param data: Data to write
        """
        pass

    def WriteEWRAM(self, offset: int, data: bytes) -> None:
        """
        Writes data to EWRAM (the slower kind of RAM.)

        :param offset: Starting address relative to the start of EWRAM
        :param data: Data to write
        """
        pass

    def WriteIWRAM(self, offset: int, data: bytes) -> None:
        """
        Writes data to IWRAM (the faster kind of RAM.)

        :param offset: Starting address relative to the start of IWRAM
        :param data: Data to write
        """
        pass

    def GetInputs(self) -> int:
        """
        :return: A bitfield with all the buttons that are currently being pressed
        """
        pass

    def SetInputs(self, inputs: int):
        """
        :param inputs: A bitfield with all the buttons that should now be pressed
        """
        pass

    def RunSingleFrame(self) -> None:
        """
        Runs (or waits for) a single frame and then returns to the caller.
        """
        pass
