from typing import Generator

from modules.debug import debug


@debug.track
def wait_for_n_frames(number_of_frames: int) -> Generator:
    """
    This will wait for a certain number of frames to pass.
    """
    for _ in range(number_of_frames):
        yield
