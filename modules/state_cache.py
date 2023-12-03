import time
from typing import Generic, TypeVar, TYPE_CHECKING

from modules.context import context

if TYPE_CHECKING:
    from modules.memory import GameState
    from modules.player import Player
    from modules.pokemon import Pokemon

T = TypeVar("T")


class StateCacheItem(Generic[T]):
    def __init__(self, initial_value: T):
        self._value: T = initial_value
        self.frame: int = 0
        self.time: float = time.time()
        self._last_check_frame: int = 0

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, new_value: T):
        self._value = new_value
        self.frame = context.emulator.get_frame_count()
        self.time = time.time()
        self._last_check_frame = self.frame

    @property
    def age_in_seconds(self) -> float | None:
        return time.time() - self.time

    @property
    def age_in_frames(self) -> int | None:
        return context.emulator.get_frame_count() - self._last_check_frame

    def checked(self) -> None:
        self._last_check_frame = context.emulator.get_frame_count()


class StateCache:
    def __init__(self):
        self._party: StateCacheItem[list["Pokemon"]] = StateCacheItem([])
        self._opponent: StateCacheItem["Pokemon | None"] = StateCacheItem(None)
        self._player: StateCacheItem["Player | None"] = StateCacheItem(None)
        self._game_state: StateCacheItem["GameState | None"] = StateCacheItem(None)

    @property
    def party(self) -> StateCacheItem[list["Pokemon"]]:
        return self._party

    @party.setter
    def party(self, party: list["Pokemon"]):
        if len(self._party.value) != len(party):
            self._party.value = party
            return

        for i in range(len(self._party.value)):
            if self._party.value[i] != party[i]:
                self._party.value = party
                return

        self._party.checked()

    @property
    def opponent(self) -> StateCacheItem["Pokemon | None"]:
        return self._opponent

    @opponent.setter
    def opponent(self, opponent: "Pokemon | None"):
        if self._opponent.value != opponent:
            self._opponent.value = opponent
        else:
            self._opponent.checked()

    @property
    def player(self) -> StateCacheItem["Player | None"]:
        return self._player

    @player.setter
    def player(self, player: "Player"):
        if self._opponent.value is None or player != self._opponent.value:
            self._player.value = player

    @property
    def game_state(self) -> StateCacheItem["GameState | None"]:
        return self._game_state

    @game_state.setter
    def game_state(self, new_game_state: "GameState"):
        if self._game_state.value != new_game_state:
            self._game_state.value = new_game_state
        else:
            self._game_state.checked()


state_cache: StateCache = StateCache()
