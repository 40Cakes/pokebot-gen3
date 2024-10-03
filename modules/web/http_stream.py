import asyncio
import json
import queue
import threading
from enum import IntFlag, auto
from threading import Thread
from time import sleep, time

from modules.console import console
from modules.context import context
from modules.libmgba import inputs_to_strings
from modules.main import work_queue, inputs_each_frame
from modules.map import get_effective_encounter_rates_for_current_map
from modules.memory import GameState, get_game_state
from modules.player import get_player, get_player_avatar
from modules.pokedex import get_pokedex
from modules.pokemon import get_opponent, get_party
from modules.state_cache import state_cache

update_interval_in_ms = 1000 / 60
queue_size = 10


class DataSubscription(IntFlag):
    Player = auto()
    PlayerAvatar = auto()
    Party = auto()
    Pokedex = auto()
    Opponent = auto()
    WildEncounter = auto()
    FishingAttempt = auto()
    GameState = auto()
    Map = auto()
    MapTile = auto()
    MapEncounters = auto()
    BotMode = auto()
    Message = auto()
    EmulatorSettings = auto()
    Inputs = auto()
    PerformanceData = auto()

    @classmethod
    def all_names(cls):
        return cls.__members__.keys()


class ThreadSafeEvent(asyncio.Event):
    def __init__(self):
        super().__init__()
        self._event_loop = asyncio.get_event_loop()

    def set(self):
        self._event_loop.call_soon_threadsafe(super().set)


class ThreadSafeCounter:
    def __init__(self, initial_value: int = 0):
        self._value = initial_value
        self._lock = threading.Lock()

    def __int__(self):
        return self._value

    def __eq__(self, other):
        if isinstance(other, (int, ThreadSafeCounter)):
            return self._value == int(other)
        else:
            raise NotImplemented

    def __ne__(self, other):
        if isinstance(other, (int, ThreadSafeCounter)):
            return self._value != int(other)
        else:
            raise NotImplemented

    def __gt__(self, other):
        if isinstance(other, (int, ThreadSafeCounter)):
            return self._value > int(other)
        else:
            raise NotImplemented

    def __ge__(self, other):
        if isinstance(other, (int, ThreadSafeCounter)):
            return self._value >= int(other)
        else:
            raise NotImplemented

    def __lt__(self, other):
        if isinstance(other, (int, ThreadSafeCounter)):
            return self._value < int(other)
        else:
            raise NotImplemented

    def __le__(self, other):
        if isinstance(other, (int, ThreadSafeCounter)):
            return self._value <= int(other)
        else:
            raise NotImplemented

    def increment(self) -> int:
        with self._lock:
            self._value += 1
            return self._value

    def decrement(self) -> int:
        with self._lock:
            self._value -= 1
            return self._value

    @property
    def value(self) -> int:
        return self._value


timer_thread: Thread
subscribers: list[tuple[int, queue.Queue, int, callable, ThreadSafeEvent]] = []
subscriptions: dict[str, ThreadSafeCounter] = {name: ThreadSafeCounter() for name in DataSubscription.all_names()}
max_client_id: ThreadSafeCounter = ThreadSafeCounter()


def add_subscriber(subscribed_topics: list[str]) -> tuple[queue.Queue, callable, ThreadSafeEvent]:
    for topic in subscribed_topics:
        if topic not in DataSubscription.all_names():
            raise ValueError(f"Topic '{topic}' does not exist.")

    client_id = max_client_id.increment()

    def unsubscribe():
        for index in range(len(subscribers)):
            if subscribers[index][0] == client_id:
                global subscriptions
                for topic in subscribed_topics:
                    subscriptions[topic].decrement()
                del subscribers[index]
                return

    global subscriptions
    subscription_flags = 0
    for topic in subscribed_topics:
        subscription_flags |= getattr(DataSubscription, topic)
        subscriptions[topic].increment()

    message_queue = queue.Queue(maxsize=queue_size)
    new_message_event = ThreadSafeEvent()
    subscribers.append((client_id, message_queue, subscription_flags, unsubscribe, new_message_event))

    if len(subscribers) == 1:
        global timer_thread
        timer_thread = Thread(target=run_watcher)
        timer_thread.start()

    return message_queue, unsubscribe, new_message_event


def run_watcher():
    update_interval = update_interval_in_ms / 1000
    previous_second = int(time())

    if state_cache.player_avatar.value is not None:
        map_group_and_number = state_cache.player_avatar.value.map_group_and_number
        map_local_coordinates = state_cache.player_avatar.value.local_coordinates
    else:
        map_group_and_number = (-1, -1)
        map_local_coordinates = (-1, -1)

    previous_game_state = {
        "party": state_cache.party.frame,
        "pokedex": state_cache.pokedex.frame,
        "opponent": state_cache.opponent.frame,
        "wild_encounter": context.stats.last_encounter.encounter_id if context.stats.last_encounter is not None else 0,
        "fishing_attempt": state_cache.fishing_attempt.frame,
        "player": state_cache.player.frame,
        "player_avatar": state_cache.player_avatar.frame,
        "map_group_and_number": map_group_and_number,
        "map_local_coordinates": map_local_coordinates,
        "map_encounters": state_cache.effective_wild_encounters.frame,
        "game_state": get_game_state(),
    }
    previous_emulator_state = {
        "bot_mode": context.bot_mode,
        "emulation_speed": context.emulation_speed,
        "audio_enabled": context.audio,
        "video_enabled": context.video,
        "inputs": context.emulator.get_inputs(),
        "message": context.message,
    }

    while len(subscribers) > 0:
        current_second = int(time())
        current_game_state = get_game_state()

        if current_second != previous_second and subscriptions["PerformanceData"] > 0:
            send_message(
                DataSubscription.PerformanceData,
                data={
                    "fps": context.emulator.get_current_fps(),
                    "frame_count": context.emulator.get_frame_count(),
                    "current_time_spent_in_bot_fraction": context.emulator.get_current_time_spent_in_bot_fraction(),
                    "encounter_rate": context.stats.encounter_rate,
                },
                event_type="PerformanceData",
            )

        if subscriptions["Player"] > 0:
            if state_cache.player.age_in_frames >= 60:
                # If the cached party data is too old, tell the main thread to update it at the next
                # possible opportunity.
                work_queue.put_nowait(get_player)
            if state_cache.player.frame > previous_game_state["player"]:
                previous_game_state["player"] = state_cache.player.frame
                send_message(DataSubscription.Player, data=state_cache.player.value.to_dict(), event_type="Player")

        if subscriptions["PlayerAvatar"] > 0:
            if state_cache.player_avatar.age_in_frames > 4:
                # If the cached player avatar data is too old, tell the main thread to update it at the next
                # possible opportunity.
                work_queue.put_nowait(get_player_avatar)
            if state_cache.player_avatar.frame > previous_game_state["player_avatar"]:
                previous_game_state["player_avatar"] = state_cache.player_avatar.frame
                send_message(
                    DataSubscription.PlayerAvatar,
                    data=state_cache.player_avatar.value.to_dict(),
                    event_type="PlayerAvatar",
                )

        if subscriptions["Party"] > 0:
            if state_cache.party.age_in_frames >= 60:
                # If the cached party data is too old, tell the main thread to update it at the next
                # possible opportunity.
                work_queue.put_nowait(get_party)
            if state_cache.party.frame > previous_game_state["party"]:
                previous_game_state["party"] = state_cache.party.frame
                data = list(map(lambda x: x.to_dict() if x is not None else None, state_cache.party.value))
                send_message(DataSubscription.Party, data=data, event_type="Party")

        if subscriptions["Pokedex"] > 0:
            if state_cache.pokedex.age_in_seconds > 0:
                # If the cached Pokédex data is too old, tell the main thread to update it at the next
                # possible opportunity.
                work_queue.put_nowait(get_pokedex)
            if state_cache.pokedex.frame > previous_game_state["pokedex"]:
                previous_game_state["pokedex"] = state_cache.pokedex.frame
                send_message(DataSubscription.Pokedex, data=state_cache.pokedex.value.to_dict(), event_type="Pokedex")

        if subscriptions["Opponent"] > 0:
            if current_game_state == GameState.BATTLE:
                if state_cache.opponent.age_in_frames >= 60:
                    # If the cached opponent data is too old, tell the main thread to update it at the next
                    # possible opportunity.
                    work_queue.put_nowait(get_opponent)
                if state_cache.opponent.frame > previous_game_state["opponent"]:
                    previous_game_state["opponent"] = state_cache.opponent.frame
                    data = state_cache.opponent.value[0]
                    if data is not None:
                        data = data.to_dict()
                    send_message(DataSubscription.Opponent, data=data, event_type="Opponent")
            elif previous_game_state["game_state"] == GameState.BATTLE:
                send_message(DataSubscription.Opponent, data=None, event_type="Opponent")

        if subscriptions["WildEncounter"] > 0:
            if context.stats.last_encounter.encounter_id != previous_game_state["wild_encounter"]:
                send_message(
                    DataSubscription.WildEncounter,
                    data=context.stats.last_encounter.to_dict(),
                    event_type="WildEncounter",
                )
                previous_game_state["wild_encounter"] = context.stats.last_encounter.encounter_id

        if subscriptions["FishingAttempt"] > 0:
            if state_cache.fishing_attempt.value != context.stats.last_fishing_attempt:
                state_cache.fishing_attempt = context.stats.last_fishing_attempt
                send_message(
                    DataSubscription.FishingAttempt,
                    data=context.stats.last_fishing_attempt.to_dict(),
                    event_type="FishingAttempt",
                )

        if subscriptions["GameState"] > 0 and current_game_state != previous_game_state["game_state"]:
            send_message(DataSubscription.GameState, data=current_game_state.name, event_type="GameState")

        if (subscriptions["Map"] > 0 or subscriptions["MapTile"] > 0) and current_game_state == GameState.OVERWORLD:
            if state_cache.player_avatar.age_in_frames > 4:
                # If the cached player avatar data is too old, tell the main thread to update it at the next
                # possible opportunity.
                work_queue.put_nowait(get_player_avatar)
            elif state_cache.player_avatar.value is not None:
                previous_game_state["player_avatar"] = state_cache.player_avatar.frame
                current_map = state_cache.player_avatar.value.map_group_and_number
                current_coords = state_cache.player_avatar.value.local_coordinates
                if current_map != previous_game_state["map_group_and_number"]:
                    map_data = state_cache.player_avatar.value.map_location
                    data = {
                        "map": map_data.dict_for_map(),
                        "player_position": map_data.local_position,
                        "tiles": map_data.dicts_for_all_tiles(),
                    }

                    if subscriptions["MapEncounters"] > 0:
                        work_queue.put_nowait(get_effective_encounter_rates_for_current_map)

                    send_message(DataSubscription.Map, data=data, event_type="MapChange")
                    previous_game_state["map_group_and_number"] = current_map
                if current_coords != previous_game_state["map_local_coordinates"]:
                    send_message(DataSubscription.Map, data=current_coords, event_type="MapTileChange")
                    previous_game_state["map_local_coordinates"] = current_coords

        if subscriptions["MapEncounters"] > 0:
            if state_cache.effective_wild_encounters.age_in_frames >= 300:
                # If the cached encounter data is too old, tell the main thread to update it at the next
                # possible opportunity.
                work_queue.put_nowait(get_effective_encounter_rates_for_current_map)
            if state_cache.effective_wild_encounters.frame > previous_game_state["map_encounters"]:
                encounters = state_cache.effective_wild_encounters.value
                previous_game_state["map_encounters"] = state_cache.effective_wild_encounters.frame
                send_message(DataSubscription.MapEncounters, data=encounters.to_dict(), event_type="MapEncounters")

        if subscriptions["BotMode"] > 0 and context.bot_mode != previous_emulator_state["bot_mode"]:
            previous_emulator_state["bot_mode"] = context.bot_mode
            send_message(DataSubscription.BotMode, data=context.bot_mode, event_type="BotMode")

        if subscriptions["Message"] > 0 and context.message != previous_emulator_state["message"]:
            previous_emulator_state["message"] = context.message
            send_message(DataSubscription.Message, data=context.message, event_type="Message")

        if subscriptions["Inputs"] > 0:
            combined_inputs = 0
            for _ in range(len(inputs_each_frame)):
                combined_inputs |= inputs_each_frame.popleft()

            if combined_inputs != previous_emulator_state["inputs"]:
                previous_emulator_state["inputs"] = combined_inputs
                send_message(DataSubscription.Inputs, data=inputs_to_strings(combined_inputs), event_type="Inputs")

        if subscriptions["EmulatorSettings"] > 0:
            if context.emulation_speed != previous_emulator_state["emulation_speed"]:
                previous_emulator_state["emulation_speed"] = context.emulation_speed
                send_message(
                    DataSubscription.EmulatorSettings, data=context.emulation_speed, event_type="EmulationSpeed"
                )

            if context.audio != previous_emulator_state["audio_enabled"]:
                previous_emulator_state["audio_enabled"] = context.audio
                send_message(DataSubscription.EmulatorSettings, data=context.audio, event_type="AudioEnabled")

            if context.video != previous_emulator_state["video_enabled"]:
                previous_emulator_state["video_enabled"] = context.video
                send_message(DataSubscription.EmulatorSettings, data=context.video, event_type="VideoEnabled")

        if current_game_state != previous_game_state["game_state"]:
            previous_game_state["game_state"] = current_game_state

        if current_second != previous_second:
            previous_second = current_second

        sleep(update_interval)


def send_message(
    subscription_flag: DataSubscription,
    data: str | list | tuple | dict | int | float | None,
    event_type: str | None = None,
) -> None:
    if event_type is not None:
        message = f"event: {event_type}\ndata: {json.dumps(data)}"
    else:
        message = f"data: {json.dumps(data)}"

    for index in reversed(range(len(subscribers))):
        if subscribers[index][2] & subscription_flag:
            try:
                subscribers[index][1].put_nowait(message)
                subscribers[index][4].set()
            except queue.Full:
                console.print(f"[yellow]Queue for client [bold]{subscribers[index][0]}[/] was full. Disconnecting.[/]")
                subscribers[index][3]()
