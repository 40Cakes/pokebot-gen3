import asyncio
import io
import queue
import re
import sys
from threading import Thread
from typing import Callable, TypeVar

import aiohttp.client_exceptions
from aiohttp import web
from apispec import APISpec
from apispec.yaml_utils import load_operations_from_docstring

from modules.daycare import get_daycare_data
from modules.game import get_current_game_data

from modules.console import console
from modules.context import context
from modules.items import get_item_bag, get_item_storage
from modules.libmgba import inputs_to_strings
from modules.main import work_queue, submit_to_work_queue
from modules.map import get_map_data, get_effective_encounter_rates_for_current_map
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_event_flag, get_game_state
from modules.modes import get_bot_mode_names
from modules.player import get_player, get_player_avatar
from modules.pokedex import get_pokedex
from modules.pokemon_party import get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.runtime import get_base_path, is_bundled_app
from modules.state_cache import StateCacheItem
from modules.version import pokebot_version, pokebot_name
from modules.web.http_stream import add_subscriber

try:
    from modules.web import webrtc
except ModuleNotFoundError as error:
    # WebRTC is optional, so it's fine if its packages are missing (see `_get_webrtc_error()`.)
    # Any other missing module is a bug though.
    if error.name is None or error.name.split(".")[0] not in ("aiortc", "av"):
        raise
    webrtc = None

custom_state: dict = {}

T = TypeVar("T")


async def _run_via_work_queue(callback: Callable[[], T]) -> T:
    """
    Runs a callback in the main thread (in between two frames) and waits for it to
    finish, without blocking the event loop.

    The HTTP server runs in a separate thread, so it must not access the emulator (or
    change the bot's state) directly. Anything that does needs to go through here.

    :param callback: The function that should be run in the main thread.
    :return: Whatever the callback returned.
    """
    return await asyncio.wrap_future(submit_to_work_queue(callback))


async def _update_via_work_queue(
    state_cache_entry: StateCacheItem, update_callback: callable, maximum_age_in_frames: int = 5
) -> None:
    """
    Ensures that an entry in the State cache is up-to-date.

    If not, it executes an update call in the main thread's work queue and will
    suppress any errors that occur.

    The reason we use a work queue is that the HTTP server runs in a separate thread
    and so is not synchronous with the emulator core. So if it were to read emulator
    memory, it might potentially get incomplete/garbage data.

    The work queue is just a list of callbacks that the main thread will execute
    after the current frame is emulated.

    Because these data-updating callbacks might fail anyway (due to the game being in
    a weird state or something like that), this function will just ignore these errors
    and pretend that the data has been updated.

    This means that the HTTP API will potentially return some outdated data, but it's
    just a reporting tool anyway.

    :param state_cache_entry: The state cache item that needs to be up-to-date.
    :param update_callback: A callback that will update the data in the state cache.
    :param maximum_age_in_frames: Defines how many frames old the data may be to still
                                  be considered up-to-date. If the data is 'younger'
                                  than or equal to that number of frames, this function
                                  will do nothing.
    """
    if state_cache_entry.age_in_frames < maximum_age_in_frames:
        return

    try:
        await _run_via_work_queue(update_callback)
    except Exception:
        console.print_exception()


def _set_held_buttons(buttons: list) -> None:
    """
    Replaces the set of buttons that are being held down in the emulator (only if the
    bot is in Manual mode.)

    Entries that are not a valid button name (case-insensitive) will be ignored.

    :param buttons: List of names of the buttons that should be held down.
    """
    possible_buttons = ["A", "B", "Select", "Start", "Right", "Left", "Up", "Down", "R", "L"]
    buttons_to_press = []
    for button in buttons:
        if not isinstance(button, str):
            continue
        for possible_button in possible_buttons:
            if button.lower() == possible_button.lower():
                buttons_to_press.append(possible_button)

    def update_inputs():
        if context.bot_mode == "Manual":
            context.emulator.reset_held_buttons()
            for button_to_press in buttons_to_press:
                context.emulator.hold_button(button_to_press)

    work_queue.put_nowait(update_inputs)


def _get_webrtc_error() -> str | None:
    """
    :return: A message explaining why WebRTC cannot be used, or `None` if it can.
    """
    if not context.config.http.webrtc.enabled:
        return "WebRTC is disabled. Set `webrtc.enabled` in `http.yml` to enable it."

    if webrtc is None:
        if is_bundled_app():
            return "WebRTC is not available in the bundled version of the bot."
        return (
            "WebRTC requires the `aiortc` package, which is not installed. You can install it with:\n"
            f'"{sys.executable}" -m pip install "aiortc~=1.10.0"'
        )

    return None


def http_server(host: str, port: int) -> web.AppRunner:
    """
    Run Flask server to make bot data available via HTTP requests.
    """

    if context.config.http.webrtc.enabled and (webrtc_error := _get_webrtc_error()) is not None:
        console.print(webrtc_error, style="yellow", markup=False, highlight=False, soft_wrap=True)

    server = web.Application()
    route = web.RouteTableDef()

    @route.get("/player")
    async def http_get_player(request: web.Request):
        """
        ---
        get:
          description:
            Returns player rarely-changing player data such as name, TID, SID etc.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - player
        """

        cached_player = context.state_cache.player
        await _update_via_work_queue(cached_player, get_player)

        try:
            data = cached_player.value.to_dict() if cached_player.value is not None else None
        except TypeError:
            data = None

        return web.json_response(data)

    @route.get("/player_avatar")
    async def http_get_player_avatar(request: web.Request):
        """
        ---
        get:
          description: Returns player avatar data, on-map character data such as map bank, map ID, X/Y coordinates
          responses:
            200:
              content:
                application/json: {}
          tags:
            - player
        """

        cached_avatar = context.state_cache.player_avatar
        await _update_via_work_queue(cached_avatar, get_player_avatar)

        data = cached_avatar.value.to_dict() if cached_avatar.value is not None else {}
        return web.json_response(data)

    @route.get("/items")
    async def http_get_bag(request: web.Request):
        """
        ---
        get:
          description: Returns a list of all items in the bag and PC, and their quantities.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - player
        """

        cached_bag = context.state_cache.item_bag
        cached_storage = context.state_cache.item_storage
        if cached_bag.age_in_seconds > 1:
            await _update_via_work_queue(cached_bag, get_item_bag)
        if cached_storage.age_in_seconds > 1:
            await _update_via_work_queue(cached_storage, get_item_storage)

        return web.json_response(
            {
                "bag": cached_bag.value.to_dict(),
                "storage": cached_storage.value.to_list(),
            }
        )

    @route.get("/party")
    async def http_get_party(request: web.Request):
        """
        ---
        get:
          description: Returns a detailed list of all Pokémon in the party.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - pokemon
        """
        cached_party = context.state_cache.party
        await _update_via_work_queue(cached_party, get_party)

        return web.json_response(cached_party.value.to_list())

    @route.get("/pokedex")
    async def http_get_pokedex(request: web.Request):
        """
        ---
        get:
          description: Returns the player's Pokédex (seen/caught).
          responses:
            200:
              content:
                application/json: {}
          tags:
            - pokemon
        """

        cached_pokedex = context.state_cache.pokedex
        if cached_pokedex.age_in_seconds > 1:
            await _update_via_work_queue(cached_pokedex, get_pokedex)

        return web.json_response(cached_pokedex.value.to_dict())

    @route.get("/pokemon_storage")
    async def http_get_pokemon_storage(request: web.Request):
        """
        ---
        get:
          description: Returns detailed information about all boxes in PC storage.
          parameters:
            - in: query
              name: format
              schema:
                type: string
              required: false
              description: >
                If this is set to `size-only` the endpoint will only report the
                number of Pokémon, not the full data.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - pokemon
        """

        cached_storage = context.state_cache.pokemon_storage
        await _update_via_work_queue(cached_storage, get_pokemon_storage)

        if "format" in request.query and request.query.getone("format") == "size-only":
            return web.json_response(
                {
                    "pokemon_stored": cached_storage.value.pokemon_count,
                    "boxes": [len(box.slots) for box in cached_storage.value.boxes],
                }
            )
        else:
            return web.json_response(cached_storage.value.to_dict())

    @route.get("/daycare")
    async def http_get_daycare(request: web.Request):
        """
        ---
        get:
          description: Returns information about which Pokémon have been deposited in the Daycare.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - pokemon
        """

        def get_daycare_dict():
            daycare_data = get_daycare_data()
            return daycare_data.to_dict() if daycare_data is not None else None

        return web.json_response(await _run_via_work_queue(get_daycare_dict))

    @route.get("/opponent")
    async def http_get_opponent(request: web.Request):
        """
        ---
        get:
          description: Returns detailed information about the current/recent encounter.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - pokemon
        """

        if context.state_cache.game_state.value != GameState.BATTLE:
            result = None
        else:
            cached_opponent = context.state_cache.opponent
            if cached_opponent.value is not None:
                result = cached_opponent.value[0].to_dict()
            else:
                result = None

        return web.json_response(result)

    @route.get("/map")
    async def http_get_map(request: web.Request):
        """
        ---
        get:
          description: Returns data about the map and current tile that the player avatar is standing on.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - map
        """

        cached_avatar = context.state_cache.player_avatar
        await _update_via_work_queue(cached_avatar, get_player_avatar)

        def get_map_dict():
            if cached_avatar.value is None:
                return None
            try:
                map_data = cached_avatar.value.map_location
                return {
                    "map": map_data.dict_for_map(),
                    "player_position": map_data.local_position,
                    "tiles": map_data.dicts_for_all_tiles(),
                }
            except (RuntimeError, TypeError):
                return None

        return web.json_response(await _run_via_work_queue(get_map_dict))

    @route.get("/map_encounters")
    async def http_get_map_encounters(request: web.Request):
        """
        ---
        get:
          description: >
            Returns a list of encounters (both regular and effective, i.e. taking into account
            Repel status and the lead Pokémon's level.)
          responses:
            200:
              content:
                application/json: {}
          tags:
            - map
        """

        effective_encounters = context.state_cache.effective_wild_encounters
        await _update_via_work_queue(effective_encounters, get_effective_encounter_rates_for_current_map)

        return web.json_response(effective_encounters.value.to_dict())

    @route.get("/map/{map_group:\\d+}/{map_number:\\d+}")
    async def http_get_map_by_group_and_number(request: web.Request):
        """
        ---
        get:
          description: Returns detailed information about a specific map.
          parameters:
            - in: path
              name: map_group
              schema:
                type: integer
              required: true
              default: 1
              description: Map Group ID
            - in: path
              name: map_number
              schema:
                type: integer
              required: true
              default: 1
              description: Map Number ID
          responses:
            200:
              content:
                application/json: {}
          tags:
            - map
        """

        map_group = int(request.match_info["map_group"])
        map_number = int(request.match_info["map_number"])
        maps_enum = MapRSE if context.rom.is_rse else MapFRLG
        try:
            maps_enum((map_group, map_number))
        except ValueError:
            return web.Response(text=f"No such map: {map_group}, {map_number}", status=404)

        def get_map_dict():
            map_data = get_map_data((map_group, map_number), local_position=(0, 0))
            return {
                "map": map_data.dict_for_map(),
                "tiles": map_data.dicts_for_all_tiles(),
            }

        return web.json_response(await _run_via_work_queue(get_map_dict))

    @route.get("/game_state")
    async def http_get_game_state(request: web.Request):
        """
        ---
        get:
          description: Returns game state information.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - game
        """
        game_state = await _run_via_work_queue(get_game_state)
        if game_state is not None:
            game_state = game_state.name

        return web.json_response(game_state)

    @route.get("/custom_state")
    async def http_get_custom_state(request: web.Request):
        """
        ---
        get:
          description: >
            Returns a dictionary that can be filled with arbitrary data by bot plugins.
            The bot itself will not use this.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - stats
        """
        return web.json_response(custom_state)

    @route.get("/event_flags")
    async def http_get_event_flags(request: web.Request):
        """
        ---
        get:
          description: Returns all event flags for the current save file (optional parameter `?flag=FLAG_NAME` to get a specific flag).
          parameters:
            - in: query
              name: flag
              schema:
                type: string
              required: false
              description: flag_name
          responses:
            200:
              content:
                application/json: {}
          tags:
            - game
        """

        flag = request.query.getone("flag", None)

        if flag and flag in get_current_game_data().event_flags:
            flags_to_read = [flag]
        else:
            flags_to_read = get_current_game_data().event_flags

        def read_event_flags():
            return {flag_name: get_event_flag(flag_name) for flag_name in flags_to_read}

        return web.json_response(await _run_via_work_queue(read_event_flags))

    @route.get("/encounter_log")
    async def http_get_encounter_log(request: web.Request):
        """
        ---
        get:
          description: Returns a detailed list of the recent 10 Pokémon encounters.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - stats
        """

        return web.json_response([pokemon.to_dict() for pokemon in context.stats.get_encounter_log()])

    @route.get("/shiny_log")
    async def http_get_shiny_log(request: web.Request):
        """
        ---
        get:
          description: Returns a detailed list of all shiny Pokémon encounters.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - stats
        """

        return web.json_response([phase.to_dict() for phase in context.stats.get_shiny_log()])

    @route.get("/encounter_rate")
    async def http_get_encounter_rate(request: web.Request):
        """
        ---
        get:
          description: Returns the current encounter rate (encounters per hour).
          responses:
            200:
              content:
                application/json: {}
          tags:
            - stats
        """

        return web.json_response({"encounter_rate": context.stats.encounter_rate})

    @route.get("/stats")
    async def http_get_stats(request: web.Request):
        """
        ---
        get:
          description: Returns returns current phase and total statistics.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - stats
        """

        return web.json_response(context.stats.get_global_stats().to_dict())

    @route.get("/fps")
    async def http_get_fps(request: web.Request):
        """
        ---
        get:
          description: Returns a list of emulator FPS (frames per second), in intervals of 1 second, for the previous 60 seconds.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - emulator
        """

        if context.emulator is None:
            return web.json_response(None)
        else:
            return web.json_response(list(reversed(context.emulator._performance_tracker.fps_history)))

    @route.get("/bot_modes")
    async def http_get_bot_modes(request: web.Request):
        """
        ---
        get:
          description: Returns a list of installed bot modes.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - emulator
        """
        return web.json_response(get_bot_mode_names())

    @route.get("/emulator")
    async def http_get_emulator(request: web.Request):
        """
        ---
        get:
          description: Returns information about the emulator core + the current loaded game/profile.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - emulator
        """

        if context.emulator is None:
            return web.json_response(None)
        else:
            return web.json_response(
                {
                    "emulation_speed": context.emulation_speed,
                    "video_enabled": context.video,
                    "audio_enabled": context.audio,
                    "bot_mode": context.bot_mode,
                    "current_message": context.message,
                    "frame_count": context.emulator.get_frame_count(),
                    "current_fps": context.emulator.get_current_fps(),
                    "current_time_spent_in_bot_fraction": context.emulator.get_current_time_spent_in_bot_fraction(),
                    "profile": {"name": context.profile.path.name},
                    "game": {
                        "title": context.rom.game_title,
                        "name": context.rom.game_name,
                        "language": str(context.rom.language),
                        "revision": context.rom.revision,
                    },
                }
            )

    @route.post("/emulator")
    async def http_post_emulator(request: web.Request):
        """
        ---
        post:
          description: Change some settings for the emulator. Accepts a JSON payload.
          requestBody:
            description: JSON payload
            content:
              application/json:
                schema: {}
                examples:
                  emulation_speed:
                    summary: Set emulation speed to 4x
                    value: {"emulation_speed": 4}
                  bot_mode:
                    summary: Set bot bode to spin
                    value: {"bot_mode": "Spin"}
                  video_enabled:
                    summary: Enable video
                    value: {"video_enabled": true}
                  audio_enabled:
                    summary: Disable audio
                    value: {"audio_enabled": false}
          responses:
            200:
              content:
                application/json: {}
          tags:
            - emulator
        """

        new_settings = await request.json()
        if not isinstance(new_settings, dict):
            return web.Response(text="This endpoint expects a JSON object as its payload.", status=422)

        # All settings are validated before any of them is applied, so that an invalid
        # request does not leave the settings half-changed.
        for key in new_settings:
            if key == "emulation_speed":
                if new_settings["emulation_speed"] not in [0, 1, 2, 3, 4, 8, 16, 32]:
                    return web.Response(
                        text=f"Setting `emulation_speed` contains an invalid value ('{new_settings['emulation_speed']}')",
                        status=422,
                    )
            elif key == "bot_mode":
                if new_settings["bot_mode"] not in get_bot_mode_names():
                    return web.Response(
                        text=f"Setting `bot_mode` contains an invalid value ('{new_settings['bot_mode']}'). Possible values are: {', '.join(get_bot_mode_names())}",
                        status=422,
                    )
            elif key == "video_enabled":
                if not isinstance(new_settings["video_enabled"], bool):
                    return web.Response(
                        text="Setting `video_enabled` did not contain a boolean value.",
                        status=422,
                    )
            elif key == "audio_enabled":
                if not isinstance(new_settings["audio_enabled"], bool):
                    return web.Response(
                        text="Setting `audio_enabled` did not contain a boolean value.",
                        status=422,
                    )
            else:
                return web.Response(text=f"Unrecognised setting: '{key}'.", status=422)

        # These setters change the emulator's audio/video setup and update the GUI,
        # so this must run in the main thread to avoid race conditions.
        def apply_settings():
            if "emulation_speed" in new_settings:
                context.emulation_speed = new_settings["emulation_speed"]
            if "bot_mode" in new_settings:
                context.bot_mode = new_settings["bot_mode"]
            if "video_enabled" in new_settings:
                context.video = new_settings["video_enabled"]
            if "audio_enabled" in new_settings:
                context.audio = new_settings["audio_enabled"]

        # If the client goes away while waiting, the settings should still be applied.
        await asyncio.shield(_run_via_work_queue(apply_settings))

        return await http_get_emulator(request)

    @route.get("/input")
    async def http_get_input(request: web.Request):
        """
        ---
        get:
          description: Returns a list of currently pressed buttons.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - emulator
        """
        return web.json_response(inputs_to_strings(await _run_via_work_queue(context.emulator.get_inputs)))

    @route.post("/input")
    async def http_post_input(request: web.Request):
        """
        ---
        post:
          description: Sets which buttons are being pressed. Accepts a JSON payload.
          requestBody:
            description: JSON payload
            content:
              application/json:
                schema: {}
                examples:
                  press_right_and_b:
                    summary: Press Right an B
                    value: ["B", "Right"]
                  release_all_buttons:
                    summary: Release all buttons
                    value: []
          responses:
            200:
              content:
                application/json: {}
          tags:
            - emulator
        """
        new_buttons = await request.json()
        if not isinstance(new_buttons, list):
            return web.Response(text="This endpoint expects a JSON array as its payload.", status=422)

        _set_held_buttons(new_buttons)

        return web.Response(status=204)

    @route.get("/stream_events")
    async def http_get_events_stream(request: web.Request):
        subscribed_topics = request.query.getall("topic")
        if len(subscribed_topics) == 0:
            return web.Response(
                text="You need to provide at least one `topic` parameter in the query.",
                status=422,
            )

        try:
            message_queue, unsubscribe, new_message_event = add_subscriber(subscribed_topics)
        except ValueError as e:
            return web.Response(text=str(e), status=422)

        response = web.StreamResponse(headers={"Content-Type": "text/event-stream"})
        await response.prepare(request)
        try:
            await response.write(b"retry: 2500\n\n")
            while True:
                await new_message_event.wait()
                try:
                    while True:
                        message = message_queue.get(block=False)
                        await response.write(str.encode(message) + b"\n\n")
                except queue.Empty:
                    pass
                new_message_event.clear()
        except GeneratorExit:
            await response.write_eof()
        except aiohttp.client_exceptions.ClientError:
            pass
        finally:
            unsubscribe()

        return response

    @route.get("/rtc/config")
    async def http_get_rtc_config(request: web.Request):
        """
        ---
        get:
          description: >
            Returns the ICE configuration (TURN servers and short-lived credentials) that a
            browser should use for its `RTCPeerConnection` before calling `/rtc`.
          responses:
            200:
              content:
                application/json: {}
            503:
              description: WebRTC is disabled or not installed.
          tags:
            - streams
        """
        if (error := _get_webrtc_error()) is not None:
            return web.Response(text=error, status=503, content_type="text/plain")

        return web.json_response(webrtc.get_client_config(), headers={"Cache-Control": "no-store"})

    @route.post("/rtc")
    async def http_post_rtc(request: web.Request):
        """
        ---
        post:
          description: >
            Answers a browser's WebRTC offer and sets up a connection that streams video and audio, and
            receives input via a data channel labelled `input`. The response contains the answer's `sdp`
            and `type`, as well as an `id` for the new connection that can be passed to `/rtc/close`.
          requestBody:
            description: The offer's session description.
            content:
              application/json:
                schema: {}
          responses:
            200:
              content:
                application/json: {}
            503:
              description: WebRTC is disabled or not installed.
          tags:
            - streams
        """
        if (error := _get_webrtc_error()) is not None:
            return web.Response(text=error, status=503, content_type="text/plain")

        params = await request.json()
        answer = await webrtc.answer_offer(params["sdp"], params["type"], _set_held_buttons)
        return web.json_response(answer)

    @route.post("/rtc/close")
    async def http_post_rtc_close(request: web.Request):
        """
        ---
        post:
          description: >
            Closes WebRTC connections, given the IDs that `/rtc` returned for them. Any buttons held
            down by those connections are released. Returns the IDs of the connections that have
            been closed; unknown IDs (e.g. of connections that have already been closed) are ignored.
          requestBody:
            description: JSON array of connection IDs
            content:
              application/json:
                schema: {}
                examples:
                  close_one_connection:
                    summary: Close one connection
                    value: ["0b7c3f4e-5d2a-4c8e-9f1b-2a6d8e4c1f3a"]
          responses:
            200:
              content:
                application/json: {}
            422:
              description: The payload is not a JSON array of strings.
            503:
              description: WebRTC is disabled or not installed.
          tags:
            - streams
        """
        if (error := _get_webrtc_error()) is not None:
            return web.Response(text=error, status=503, content_type="text/plain")

        try:
            connection_ids = await request.json()
        except ValueError:
            connection_ids = None
        if not isinstance(connection_ids, list) or not all(isinstance(id, str) for id in connection_ids):
            return web.Response(text="This endpoint expects a JSON array of connection IDs as its payload.", status=422)

        return web.json_response(await webrtc.close_connections(connection_ids))

    @route.post("/rtc/close_all")
    async def http_post_rtc_close_all(request: web.Request):
        """
        ---
        post:
          description: >
            Closes all WebRTC connections and releases any buttons they held down. Returns the IDs of
            the connections that have been closed.
          responses:
            200:
              content:
                application/json: {}
            503:
              description: WebRTC is disabled or not installed.
          tags:
            - streams
        """
        if (error := _get_webrtc_error()) is not None:
            return web.Response(text=error, status=503, content_type="text/plain")

        return web.json_response(await webrtc.close_all_connections())

    @route.get("/stream_video")
    async def http_get_video_stream(request: web.Request):
        """
        ---
        get:
          description: Stream emulator video.
          parameters:
            - in: query
              name: fps
              schema:
                type: integer
              required: true
              description: fps
              default: 30
          responses:
            200:
              content:
                text/event-stream:
                  schema:
                    type: array
          tags:
            - streams
        """
        fps = request.query.getone("fps", "30")
        fps = int(fps) if fps.isdigit() else 30
        fps = min(fps, 60)

        response = web.StreamResponse(headers={"Content-Type": "multipart/x-mixed-replace; boundary=frame"})
        await response.prepare(request)

        sleep_after_frame = 1 / fps
        png_data = io.BytesIO()
        try:
            while True:
                if context.video:
                    png_data.seek(0)
                    context.emulator.get_current_screen_image().convert("RGB").save(png_data, format="PNG")
                    png_data.seek(0)
                    await response.write(b"\r\n--frame\r\nContent-Type: image/png\r\n\r\n" + png_data.read())
                await asyncio.sleep(sleep_after_frame)
        except aiohttp.client_exceptions.ClientError:
            pass

        return response

    swagger_url = "/docs"
    api_url = f"http://{host}:{port}/docs"

    spec = APISpec(
        title=f"{pokebot_name} API",
        version=pokebot_version,
        openapi_version="3.0.3",
        info=dict(
            description=f"{pokebot_name} API",
            version=pokebot_version,
            license=dict(
                name="GNU General Public License v3.0",
                url="https://github.com/40Cakes/pokebot-gen3/blob/main/LICENSE",
            ),
        ),
        servers=[
            dict(
                description=f"{pokebot_name} server",
                url=f"http://{host}:{port}",
            )
        ],
    )

    # Everything until here is considered an API route that should be documented in Swagger.
    for api_route in route:
        if isinstance(api_route, web.RouteDef):
            path = re.sub("\\{([_a-zA-Z0-9]+)(:[^}]*)?}", "{\\1}", api_route.path)
            operations = load_operations_from_docstring(api_route.handler.__doc__)
            spec.path(path=path, operations=operations)

    # From here on out, any additional routes will NOT be documented in Swagger.
    @route.get("/api.json")
    async def http_get_api_json(request: web.Request):
        api_docs = spec.to_dict()
        api_docs["servers"][0]["url"] = f"http://{request.headers['host']}"

        return web.json_response(api_docs)

    @route.get("/docs")
    async def http_docs(request: web.Request):
        raise web.HTTPFound(location="/static/api-doc.html")

    @route.get("/stream-overlay")
    @route.get("/static/stream-overlay")
    @route.get("/static/stream-overlay/")
    async def http_stream_overlay_redirect(request: web.Request):
        return web.HTTPFound(location="/static/stream-overlay/index.html")

    @route.get("/")
    async def http_index(request: web.Request):
        raise web.HTTPFound(location="/static/index.html")

    route.static("/static", get_base_path() / "modules" / "web" / "static")

    server = web.Application()
    server.add_routes(route)

    return web.AppRunner(server)


def start_http_server(host: str, port: int):
    web_app = http_server(host, port)

    def run_server(runner: web.AppRunner):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(runner.setup())
        server = web.TCPSite(runner, host, port)
        loop.run_until_complete(server.start())
        loop.run_forever()

    Thread(target=run_server, args=(web_app,)).start()
