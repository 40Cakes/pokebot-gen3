import io
import json
import time
from pathlib import Path

import waitress
from apispec import APISpec
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask, Response, jsonify, redirect, request
from flask_cors import CORS
from flask_swagger_ui import get_swaggerui_blueprint
from jinja2 import Template

from modules.console import console
from modules.context import context
from modules.files import read_file
from modules.game import _event_flags
from modules.items import get_item_bag, get_item_storage
from modules.libmgba import inputs_to_strings
from modules.main import work_queue
from modules.map import get_map_data, get_wild_encounters_for_map
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_event_flag, get_game_state
from modules.modes import get_bot_mode_names
from modules.player import get_player, get_player_avatar
from modules.pokedex import get_pokedex
from modules.pokemon import get_party
from modules.pokemon_storage import get_pokemon_storage
from modules.state_cache import state_cache, StateCacheItem
from modules.stats import total_stats
from modules.version import pokebot_name, pokebot_version
from modules.web.http_stream import DataSubscription, add_subscriber


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


def http_server() -> None:
    """
    Run Flask server to make bot data available via HTTP requests.
    """

    server = Flask(__name__)
    CORS(server)

    swagger_url = "/docs"
    api_url = f"http://{context.config.http.http_server.ip}:{context.config.http.http_server.port}/swagger"
    docs_dir = Path(__file__).parent / "docs"

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
                url=f"http://{context.config.http.http_server.ip}:{context.config.http.http_server.port}",
            )
        ],
        plugins=[FlaskPlugin()],
    )

    swaggerui_blueprint = get_swaggerui_blueprint(swagger_url, api_url, config={"app_name": f"{pokebot_name} API"})

    @server.route("/player", methods=["GET"])
    def http_get_player():
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

        return jsonify(data)

    @server.route("/player_avatar", methods=["GET"])
    def http_get_player_avatar():
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
        return jsonify(data)

    @server.route("/items", methods=["GET"])
    def http_get_bag():
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

        return jsonify(
            {
                "bag": cached_bag.value.to_dict(),
                "storage": cached_storage.value.to_list(),
            }
        )

    @server.route("/party", methods=["GET"])
    def http_get_party():
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

        return jsonify([p.to_dict() for p in cached_party.value])

    @server.route("/pokedex", methods=["GET"])
    def http_get_pokedex():
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

        return jsonify(cached_pokedex.value.to_dict())

    @server.route("/pokemon_storage", methods=["GET"])
    def http_get_pokemon_storage():
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

        return jsonify(cached_storage.value.to_dict())

    @server.route("/opponent", methods=["GET"])
    def http_get_opponent():
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
                result = cached_opponent.value.to_dict()
            else:
                result = None

        return jsonify(result)

    @server.route("/map", methods=["GET"])
    def http_get_map():
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
                    "player_position": map_data.local_position,
                    "map": map_data.dict_for_map(),
                    "tiles": map_data.dicts_for_all_tiles(),
                    "encounters": get_wild_encounters_for_map(map_data.map_group, map_data.map_number).to_dict(),
                }
            except (RuntimeError, TypeError):
                data = None
        else:
            data = None

        return jsonify(data)

    @server.route("/map/<int:map_group>/<int:map_number>")
    def http_get_map_by_group_and_number(map_group: int, map_number: int):
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

        maps_enum = MapRSE if context.rom.is_rse else MapFRLG
        try:
            maps_enum((map_group, map_number))
        except ValueError:
            return Response(f"No such map: {map_group}, {map_number}", status=404)

        map_data = get_map_data((map_group, map_number), local_position=(0, 0))
        return jsonify(
            {
                "map": map_data.dict_for_map(),
                "tiles": map_data.dicts_for_all_tiles(),
                "encounters": get_wild_encounters_for_map(map_group, map_number).to_dict(),
            }
        )

    @server.route("/game_state", methods=["GET"])
    def http_get_game_state():
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

        return jsonify(game_state)

    @server.route("/event_flags", methods=["GET"])
    def http_get_event_flags():
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

        flag = request.args.get("flag")

        if flag and flag in _event_flags:
            return jsonify({flag: get_event_flag(flag)})
        result = {}

        for flag in _event_flags:
            result[flag] = get_event_flag(flag)

        return result

    @server.route("/encounter_log", methods=["GET"])
    def http_get_encounter_log():
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

        return jsonify(total_stats.get_encounter_log()[::-1])

    @server.route("/shiny_log", methods=["GET"])
    def http_get_shiny_log():
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

        return jsonify(total_stats.get_shiny_log()[::-1])

    @server.route("/encounter_rate", methods=["GET"])
    def http_get_encounter_rate():
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

        return jsonify({"encounter_rate": total_stats.get_encounter_rate()})

    @server.route("/stats", methods=["GET"])
    def http_get_stats():
        """
        ---
        get:
          description: Returns Pokémon, current phase and total statistics.
          parameters:
            - in: query
              name: type
              required: false
              schema:
                type: string
                enum:
                  - pokemon
                  - totals
            - in: query
              name: pokemon
              required: false
              schema:
                type: string
              description: Specify the Pokémon name to return statistics, use when `?type=pokemon`.
          responses:
            200:
              content:
                application/json: {}
          tags:
            - stats
        """
        query_type = request.args.get("type")
        query_pokemon = request.args.get("pokemon")

        stats = total_stats.get_total_stats()

        if query_type == "pokemon":
            if stats["pokemon"].get(query_pokemon, False):
                return stats["pokemon"][query_pokemon]
            else:
                return stats["pokemon"]
        return stats["totals"] if query_type == "totals" else jsonify(stats)

    @server.route("/fps", methods=["GET"])
    def http_get_fps():
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
            return jsonify(None)
        else:
            return jsonify(list(reversed(context.emulator._performance_tracker.fps_history)))

    @server.route("/bot_modes", methods=["GET"])
    def http_get_bot_modes():
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
        return jsonify(get_bot_mode_names())

    @server.route("/emulator", methods=["GET"])
    def http_get_emulator():
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
            return jsonify(None)
        else:
            return jsonify(
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

    @server.route("/emulator", methods=["POST"])
    def http_post_emulator():
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

        new_settings = request.json
        if not isinstance(new_settings, dict):
            return Response("This endpoint expects a JSON object as its payload.", status=422)

        for key in new_settings:
            if key == "emulation_speed":
                if new_settings["emulation_speed"] not in [0, 1, 2, 3, 4]:
                    return Response(
                        f"Setting `emulation_speed` contains an invalid value ('{new_settings['emulation_speed']}')",
                        status=422,
                    )
                context.emulation_speed = new_settings["emulation_speed"]
            elif key == "bot_mode":
                if new_settings["bot_mode"] not in get_bot_mode_names():
                    return Response(
                        f"Setting `bot_mode` contains an invalid value ('{new_settings['bot_mode']}'). Possible values are: {', '.join(get_bot_mode_names())}",
                        status=422,
                    )
                context.bot_mode = new_settings["bot_mode"]
            elif key == "video_enabled":
                if not isinstance(new_settings["video_enabled"], bool):
                    return Response(
                        "Setting `video_enabled` did not contain a boolean value.",
                        status=422,
                    )
                context.video = new_settings["video_enabled"]
            elif key == "audio_enabled":
                if not isinstance(new_settings["audio_enabled"], bool):
                    return Response(
                        "Setting `audio_enabled` did not contain a boolean value.",
                        status=422,
                    )
                context.audio = new_settings["audio_enabled"]
            else:
                return Response(f"Unrecognised setting: '{key}'.", status=422)

        return http_get_emulator()

    @server.route("/input", methods=["GET"])
    def http_get_input():
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
        return jsonify(inputs_to_strings(context.emulator.get_inputs()))

    @server.route("/input", methods=["POST"])
    def http_post_input():
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
        new_buttons = request.json
        if not isinstance(new_buttons, list):
            return Response("This endpoint expects a JSON array as its payload.", status=422)

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

        return Response(status=204)

    @server.route("/stream_events", methods=["GET"])
    def http_get_events_stream():
        subscribed_topics = request.args.getlist("topic")
        if len(subscribed_topics) == 0:
            return Response(
                "You need to provide at least one `topic` parameter in the query.",
                status=422,
            )

        try:
            queue, unsubscribe = add_subscriber(subscribed_topics)
        except ValueError as e:
            return Response(str(e), status=422)

        def stream():
            try:
                yield "retry: 2500\n\n"
                while True:
                    yield queue.get()
                    yield "\n\n"
            except GeneratorExit:
                unsubscribe()

        return Response(stream(), mimetype="text/event-stream")

    doc_http_get_events_stream = """
        ---
        get:
          description: |
            # Available Topics:
            {% for index in range(DataSubscription | length) %}
            - `{{ DataSubscription[index] }}`
            {% endfor %}
            {{ readme | indent(12) }}
          parameters:
            - in: query
              name: topic
              schema:
                type: string
              required: true
              description: topic
          responses:
            200:
              content:
                text/event-stream:
                  schema:
                    type: array
          tags:
            - streams
        """

    http_get_events_stream.__doc__ = Template(doc_http_get_events_stream).render(
        readme=read_file(docs_dir / "event_stream.md"),
        DataSubscription=list(DataSubscription.all_names()),
    )

    @server.route("/stream_video", methods=["GET"])
    def http_get_video_stream():
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
        fps = request.args.get("fps", "30")
        fps = int(fps) if fps.isdigit() else 30
        fps = min(fps, 60)

        def stream():
            sleep_after_frame = 1 / fps
            png_data = io.BytesIO()
            yield "--frame\r\n"
            while True:
                if context.video:
                    png_data.seek(0)
                    context.emulator.get_current_screen_image().convert("RGB").save(png_data, format="PNG")
                    png_data.seek(0)
                    yield "Content-Type: image/png\r\n\r\n"
                    yield png_data.read()
                    yield "\r\n--frame\r\n"
                time.sleep(sleep_after_frame)

        return Response(stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @server.route("/", methods=["GET"])
    def http_index():
        return redirect("static/index.html", code=302)

    @server.route("/swagger", methods=["GET"])
    def http_get_swagger_json():
        return Response(
            json.dumps(spec.to_dict(), indent=4),
            content_type="application/json; charset=utf-8",
        )

    with server.test_request_context():
        spec.path(view=http_get_player)
        spec.path(view=http_get_player_avatar)
        spec.path(view=http_get_bag)
        spec.path(view=http_get_party)
        spec.path(view=http_get_map)
        spec.path(view=http_get_map_by_group_and_number)
        spec.path(view=http_get_pokedex)
        spec.path(view=http_get_pokemon_storage)
        spec.path(view=http_get_opponent)
        spec.path(view=http_get_game_state)
        spec.path(view=http_get_encounter_log)
        spec.path(view=http_get_shiny_log)
        spec.path(view=http_get_encounter_rate)
        spec.path(view=http_get_stats)
        spec.path(view=http_get_event_flags)
        spec.path(view=http_get_fps)
        spec.path(view=http_get_emulator)
        spec.path(view=http_post_emulator)
        spec.path(view=http_get_events_stream)
        spec.path(view=http_get_video_stream)

    server.register_blueprint(swaggerui_blueprint)

    waitress.serve(
        server,
        host=context.config.http.http_server.ip,
        port=context.config.http.http_server.port,
        threads=8,
        ident=f"{pokebot_name}/{pokebot_version} (waitress)",
    )
