import asyncio
import io
import queue
import re
import time
from queue import Queue
from threading import Thread
from typing import Union

import aiohttp.client_exceptions
from aiohttp import web
from aiortc import MediaStreamTrack, VideoStreamTrack, RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRelay
from apispec import APISpec
from apispec.yaml_utils import load_operations_from_docstring
from av import VideoFrame, Packet, AudioFrame
from av.frame import Frame

from modules.console import console
from modules.context import context
from modules.game import _event_flags
from modules.items import get_item_bag, get_item_storage
from modules.libmgba import inputs_to_strings
from modules.main import work_queue
from modules.map import get_map_data, get_effective_encounter_rates_for_current_map
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_event_flag, get_game_state
from modules.modes import get_bot_mode_names
from modules.player import get_player, get_player_avatar
from modules.pokedex import get_pokedex
from modules.pokemon import get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.runtime import get_base_path
from modules.state_cache import state_cache, StateCacheItem
from modules.version import pokebot_version, pokebot_name
from modules.web.http_stream import add_subscriber


# from apispec import APISpec


def _update_via_work_queue(
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

    def do_update():
        try:
            update_callback()
        except Exception:
            console.print_exception()

    try:
        work_queue.put_nowait(do_update)
        work_queue.join()
    except Exception:
        console.print_exception()
        return


def http_server(host: str, port: int) -> web.AppRunner:
    """
    Run Flask server to make bot data available via HTTP requests.
    """

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

        cached_player = state_cache.player
        _update_via_work_queue(cached_player, get_player)

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

        cached_avatar = state_cache.player_avatar
        _update_via_work_queue(cached_avatar, get_player_avatar)

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

        cached_bag = state_cache.item_bag
        cached_storage = state_cache.item_storage
        if cached_bag.age_in_seconds > 1:
            _update_via_work_queue(cached_bag, get_item_bag)
        if cached_storage.age_in_seconds > 1:
            _update_via_work_queue(cached_storage, get_item_storage)

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
        cached_party = state_cache.party
        _update_via_work_queue(cached_party, get_party)

        return web.json_response([p.to_dict() for p in cached_party.value])

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

        cached_pokedex = state_cache.pokedex
        if cached_pokedex.age_in_seconds > 1:
            _update_via_work_queue(cached_pokedex, get_pokedex)

        return web.json_response(cached_pokedex.value.to_dict())

    @route.get("/pokemon_storage")
    async def http_get_pokemon_storage(request: web.Request):
        """
        ---
        get:
          description: Returns detailed information about all boxes in PC storage.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - pokemon
        """

        cached_storage = state_cache.pokemon_storage
        _update_via_work_queue(cached_storage, get_pokemon_storage)

        return web.json_response(cached_storage.value.to_dict())

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

        if state_cache.game_state.value != GameState.BATTLE:
            result = None
        else:
            cached_opponent = state_cache.opponent
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

        cached_avatar = state_cache.player_avatar
        _update_via_work_queue(cached_avatar, get_player_avatar)

        if cached_avatar.value is not None:
            try:
                map_data = cached_avatar.value.map_location
                data = {
                    "map": map_data.dict_for_map(),
                    "player_position": map_data.local_position,
                    "tiles": map_data.dicts_for_all_tiles(),
                }
            except (RuntimeError, TypeError):
                data = None
        else:
            data = None

        return web.json_response(data)

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

        effective_encounters = state_cache.effective_wild_encounters
        _update_via_work_queue(effective_encounters, get_effective_encounter_rates_for_current_map)

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

        map_data = get_map_data((map_group, map_number), local_position=(0, 0))
        return web.json_response(
            {
                "map": map_data.dict_for_map(),
                "tiles": map_data.dicts_for_all_tiles(),
            }
        )

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
        game_state = get_game_state()
        if game_state is not None:
            game_state = game_state.name

        return web.json_response(game_state)

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

        if flag and flag in _event_flags:
            return web.json_response({flag: get_event_flag(flag)})
        result = {}

        for flag in _event_flags:
            result[flag] = get_event_flag(flag)

        return web.json_response(result)

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

        for key in new_settings:
            if key == "emulation_speed":
                if new_settings["emulation_speed"] not in [0, 1, 2, 3, 4]:
                    return web.Response(
                        text=f"Setting `emulation_speed` contains an invalid value ('{new_settings['emulation_speed']}')",
                        status=422,
                    )
                context.emulation_speed = new_settings["emulation_speed"]
            elif key == "bot_mode":
                if new_settings["bot_mode"] not in get_bot_mode_names():
                    return web.Response(
                        text=f"Setting `bot_mode` contains an invalid value ('{new_settings['bot_mode']}'). Possible values are: {', '.join(get_bot_mode_names())}",
                        status=422,
                    )
                context.bot_mode = new_settings["bot_mode"]
            elif key == "video_enabled":
                if not isinstance(new_settings["video_enabled"], bool):
                    return web.Response(
                        text="Setting `video_enabled` did not contain a boolean value.",
                        status=422,
                    )
                context.video = new_settings["video_enabled"]
            elif key == "audio_enabled":
                if not isinstance(new_settings["audio_enabled"], bool):
                    return web.Response(
                        text="Setting `audio_enabled` did not contain a boolean value.",
                        status=422,
                    )
                context.audio = new_settings["audio_enabled"]
            else:
                return web.Response(text=f"Unrecognised setting: '{key}'.", status=422)

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
        return web.json_response(inputs_to_strings(context.emulator.get_inputs()))

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

        possible_buttons = ["A", "B", "Select", "Start", "Right", "Left", "Up", "Down", "R", "L"]
        buttons_to_press = []
        for button in new_buttons:
            for possible_button in possible_buttons:
                if button.lower() == possible_button.lower():
                    buttons_to_press.append(possible_button)

        def update_inputs():
            if context.bot_mode == "Manual":
                context.emulator.reset_held_buttons()
                for button_to_press in buttons_to_press:
                    context.emulator.hold_button(button_to_press)

        work_queue.put_nowait(update_inputs)

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

    rtc_connections: set[RTCPeerConnection] = set()

    class EmuVideo(VideoStreamTrack):
        def __init__(self):
            super().__init__()

        async def recv(self) -> Union[Frame, Packet]:
            pts, time_base = await self.next_timestamp()

            frame = VideoFrame.from_image(context.emulator.get_current_screen_image())
            frame.pts = pts
            frame.time_base = time_base

            return frame

    class EmuAudio(MediaStreamTrack):
        kind = "audio"

        def __init__(self):
            super().__init__()
            self._queue: Queue[bytes] = context.emulator.get_last_audio_data()
            self._start: float | None = None
            self._timestamp: float = 0

        async def recv(self) -> Union[Frame, Packet]:
            sample_rate = context.emulator.get_sample_rate()
            data = b""
            while len(data) == 0:
                try:
                    part = self._queue.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(1 / 480)
                    continue
                data += part

            if self._start is None:
                self._start = time.time()

            frame = AudioFrame(format="s16", layout="stereo", samples=len(data) // 4)
            frame.planes[0].update(data)
            frame.pts = self._timestamp
            frame.sample_rate = sample_rate

            self._timestamp += len(data) // 4

            return frame

    relay = MediaRelay()
    emu_audio = None
    emu_video = None

    @route.post("/rtc")
    async def http_post_rtc(request: web.Request):
        nonlocal rtc_connections, emu_video, emu_audio

        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

        connection = RTCPeerConnection()
        rtc_connections.add(connection)

        @connection.on("datachannel")
        def on_datachannel(channel):
            @channel.on("message")
            def on_message(message):
                if isinstance(message, str) and message.startswith("ping"):
                    channel.send("pong" + message[4:])

        @connection.on("connectionstatechange")
        async def on_connection_state_change():
            if connection.connectionState == "failed":
                await connection.close()
                rtc_connections.discard(connection)

        if emu_video is None:
            emu_video = EmuVideo()

        if emu_audio is None:
            emu_audio = EmuAudio()

        connection.addTrack(relay.subscribe(emu_video))
        connection.addTrack(relay.subscribe(emu_audio))

        await connection.setRemoteDescription(offer)

        answer = await connection.createAnswer()
        await connection.setLocalDescription(answer)

        return web.json_response({"sdp": connection.localDescription.sdp, "type": connection.localDescription.type})

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
        raise web.HTTPFound(location="static/api-doc.html")

    @route.get("/")
    async def http_index(request: web.Request):
        raise web.HTTPFound(location="static/index.html")

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
