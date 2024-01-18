import time
from typing import Generic, TypeVar, TYPE_CHECKING

from modules.context import context

if TYPE_CHECKING:
    from modules.items import ItemBag, ItemStorage
    from modules.memory import GameState
    from modules.player import Player, PlayerAvatar
    from modules.pokemon import Pokemon
    from modules.pokemon_storage import PokemonStorage
    from modules.pokedex import Pokedex
    from modules.tasks import TaskList, ScriptContext

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
        self._player_avatar: StateCacheItem["PlayerAvatar | None"] = StateCacheItem(None)
        self._pokedex: StateCacheItem["Pokedex | None"] = StateCacheItem(None)
        self._pokemon_storage: StateCacheItem["PokemonStorage | None"] = StateCacheItem(None)
        self._item_bag: StateCacheItem["ItemBag | None"] = StateCacheItem(None)
        self._item_storage: StateCacheItem["ItemStorage | None"] = StateCacheItem(None)
        self._tasks: StateCacheItem["TaskList | None"] = StateCacheItem(None)
        self._global_script_context: StateCacheItem["ScriptContext | None"] = StateCacheItem(None)
        self._immediate_script_context: StateCacheItem["ScriptContext | None"] = StateCacheItem(None)
        self._game_state: StateCacheItem["GameState | None"] = StateCacheItem(None)
        self._last_encounter_log: StateCacheItem["dict | None"] = StateCacheItem(None)
        self._last_shiny_log: StateCacheItem["dict | None"] = StateCacheItem(None)

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
        if self._player.value is None or player != self._player.value:
            self._player.value = player
        else:
            self._player.checked()

    @property
    def player_avatar(self) -> StateCacheItem["PlayerAvatar | None"]:
        return self._player_avatar

    @player_avatar.setter
    def player_avatar(self, player_avatar: "PlayerAvatar"):
        if self._player_avatar.value is None or player_avatar != self._player_avatar.value:
            self._player_avatar.value = player_avatar
        else:
            self._player_avatar.checked()

    @property
    def pokedex(self) -> StateCacheItem["Pokedex | None"]:
        return self._pokedex

    @pokedex.setter
    def pokedex(self, pokedex: "Pokedex"):
        if self._pokedex.value != pokedex:
            self._pokedex.value = pokedex
        else:
            self._pokedex.checked()

    @property
    def pokemon_storage(self) -> StateCacheItem["PokemonStorage | None"]:
        return self._pokemon_storage

    @pokemon_storage.setter
    def pokemon_storage(self, pokemon_storage: "PokemonStorage"):
        if self._pokemon_storage.value is None or self._pokemon_storage.value != pokemon_storage:
            self._pokemon_storage.value = pokemon_storage
        else:
            self._pokemon_storage.checked()

    @property
    def item_bag(self) -> StateCacheItem["ItemBag | None"]:
        return self._item_bag

    @item_bag.setter
    def item_bag(self, item_bag: "ItemBag"):
        if self._item_bag.value is None or self._item_bag.value != item_bag:
            self._item_bag.value = item_bag
        else:
            self._item_bag.checked()

    @property
    def item_storage(self) -> StateCacheItem["ItemStorage | None"]:
        return self._item_storage

    @item_storage.setter
    def item_storage(self, item_storage: "ItemStorage"):
        if self._item_storage.value is None or self._item_storage.value != item_storage:
            self._item_storage.value = item_storage
        else:
            self._item_storage.checked()

    @property
    def tasks(self) -> StateCacheItem["TaskList | None"]:
        return self._tasks

    @tasks.setter
    def tasks(self, tasks: "TaskList"):
        if self._tasks.value != tasks:
            self._tasks.value = tasks
        else:
            self._tasks.checked()

    @property
    def global_script_context(self) -> StateCacheItem["ScriptContext | None"]:
        return self._global_script_context

    @global_script_context.setter
    def global_script_context(self, script_context: "ScriptContext"):
        if self._global_script_context.value != script_context:
            self._global_script_context.value = script_context
        else:
            self._global_script_context.checked()

    @property
    def immediate_script_context(self) -> StateCacheItem["ScriptContext | None"]:
        return self._immediate_script_context

    @immediate_script_context.setter
    def immediate_script_context(self, script_context: "ScriptContext"):
        if self._immediate_script_context.value != script_context:
            self._immediate_script_context.value = script_context
        else:
            self._immediate_script_context.checked()

    @property
    def game_state(self) -> StateCacheItem["GameState | None"]:
        return self._game_state

    @game_state.setter
    def game_state(self, new_game_state: "GameState"):
        if self._game_state.value != new_game_state:
            self._game_state.value = new_game_state
        else:
            self._game_state.checked()

    @property
    def last_encounter_log(self) -> StateCacheItem["dict | None"]:
        return self._last_encounter_log

    @last_encounter_log.setter
    def last_encounter_log(self, new_encounter_log: dict):
        if self._last_encounter_log.value != new_encounter_log:
            self._last_encounter_log.value = new_encounter_log
        else:
            self._last_encounter_log.checked()

    @property
    def last_shiny_log(self) -> StateCacheItem["dict | None"]:
        return self._last_shiny_log

    @last_shiny_log.setter
    def last_shiny_log(self, new_shiny_log: dict):
        if self._last_shiny_log.value != new_shiny_log:
            self._last_shiny_log.value = new_shiny_log
        else:
            self._last_shiny_log.checked()


state_cache: StateCache = StateCache()
