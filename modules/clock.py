from dataclasses import dataclass

from modules.memory import read_symbol, unpack_uint16, get_save_block


@dataclass
class ClockTime:
    days: int
    hours: int
    minutes: int
    seconds: int

    def __str__(self):
        return f"{self.days} day{'s' if self.days != 1 else ''}, {self.hours:02d}:{self.minutes:02d}:{self.seconds:02d}"


def get_clock_time() -> ClockTime:
    """
    Returns the in-game time that clock events are based on. This clock is based on
    the GBA's/emulator's real-time clock, which in this bot is tied to the actual
    system clock.

    So regardless of the speed multiplier, this time will always advance in real time.

    :return: The current clock time as reported by the game. Note that the game does
             not update this value all the time, so it is normal for it to return the
             same value when called multiple times within a couple of seconds.
    """

    data = read_symbol("gLocalTime")
    return ClockTime(unpack_uint16(data[0:2]), data[2], data[3], data[4])


@dataclass
class PlayTime:
    hours: int
    minutes: int
    seconds: int
    frames: int

    def __str__(self):
        return f"{self.hours:02d}:{self.minutes:02d}:{self.seconds:02d} +{self.frames} frames"


def get_play_time() -> PlayTime:
    """
    Returns the play time counter. This gets advanced every frame and so is tied to
    the emulation speed as well.

    It's the time the game will display on the trainer card, while saving, etc.

    :return: Time played as reported by the game. This has a maximum value of 999 days,
             59 minutes, 59 seconds, and 59 frames. Once that value is reached, this
             time will not advance anymore.
    """
    save_block_time = get_save_block(2, offset=0x0E, size=0x5)
    return PlayTime(unpack_uint16(save_block_time[0:2]), save_block_time[2], save_block_time[3], save_block_time[4])
