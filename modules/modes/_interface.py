"""
Contains definitions for the `BotMode` base class as well as the `BotModeError` type, so we
can import that anywhere without having to worry about circular import issues.
"""

from typing import Generator


class BotMode:
    @staticmethod
    def name() -> str:
        """
        :return: The name of this mode that will be displayed in the bot mode selection drop-down.
        """
        ...

    def disable_default_battle_handler(self) -> bool:
        """
        Indicates whether the default battle handler should be used in this mode, or whether
        this mode has its own battle-handling code.
        """
        return False

    def run(self) -> Generator:
        """
        Contains the actual handling code.

        This should be a Generator function (i.e. a function that uses the `yield` keyword)
        which will be called once per frame -- so each time it calls `yield`, the emulator
        will process another frame and only then the function resumes.

        The generator might not be called for every frame: If a battle started, by default
        the battle handler will be used instead until the battle finishes. This behaviour
        can be prevented by making `self.disable_default_battle_handler()` return `True`,
        in which case this Generator function will also be called inside of battles.
        """
        ...

    def __init__(self):
        self._iterator = self.run()

    def __next__(self):
        return next(self._iterator)


class BotModeError(Exception):
    pass
