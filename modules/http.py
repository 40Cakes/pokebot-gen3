import io
import time
from pathlib import Path

from flask import Flask, jsonify, request, Response
from flask_cors import CORS

from modules.config import available_bot_modes
from modules.context import context
from modules.data.map import MapRSE, MapFRLG
from modules.game import _event_flags
from modules.http_stream import add_subscriber
from modules.items import get_items
from modules.main import work_queue
from modules.map import get_map_data
from modules.memory import get_event_flag, get_game_state, GameState
from modules.pokemon import get_party
from modules.stats import total_stats
from modules.state_cache import state_cache
from modules.player import get_player, get_player_avatar


def http_server() -> None:
    """
    Run Flask server to make bot data available via HTTP requests.
    """
    server = Flask(__name__)
    CORS(server)

    @server.route("/stream_events", methods=["GET"])
    def http_get_events_stream():
        subscribed_topics = request.args.getlist("topic")
        if len(subscribed_topics) == 0:
            return Response("You need to provide at least one `topic` parameter in the query.", status=422)

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

    @server.route("/stream_video", methods=["GET"])
    def http_get_video_stream():
        fps = request.args.get("fps", "30")
        if not fps.isdigit():
            fps = 30
        else:
            fps = int(fps)
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

    @server.route("/player", methods=["GET"])
    def http_get_player():
        cached_player = state_cache.player
        if cached_player.age_in_frames > 5:
            work_queue.put_nowait(get_player)
            while cached_player.age_in_frames > 5:
                time.sleep(0.05)

        if cached_player.value is not None:
            data = cached_player.value.to_dict()
        else:
            data = {}
        return jsonify(data)

    @server.route("/player_avatar", methods=["GET"])
    def http_get_player_avatar():
        cached_avatar = state_cache.player_avatar
        if cached_avatar.age_in_frames > 5:
            work_queue.put_nowait(get_player_avatar)
            while cached_avatar.age_in_frames > 5:
                time.sleep(0.05)

        if cached_avatar.value is not None:
            data = cached_avatar.value.to_dict()
        else:
            data = {}
        return jsonify(data)

    @server.route("/items", methods=["GET"])
    def http_get_bag():
        return jsonify(get_items())

    @server.route("/map", methods=["GET"])
    def http_get_map():
        cached_avatar = state_cache.player_avatar
        if cached_avatar.age_in_frames > 5:
            work_queue.put_nowait(get_player_avatar)
            while cached_avatar.age_in_frames > 5:
                time.sleep(0.05)

        if cached_avatar.value is not None:
            map_data = cached_avatar.value.map_location
            data = {
                "map": map_data.dict_for_map(),
                "player_position": map_data.local_position,
                "tiles": map_data.dicts_for_all_tiles(),
            }
        else:
            data = None

        return jsonify(data)

    @server.route("/map/<int:map_group>/<int:map_number>")
    def http_get_map_by_group_and_number(map_group: int, map_number: int):
        if context.rom.game_title in ["POKEMON EMER", "POKEMON RUBY", "POKEMON SAPP"]:
            maps_enum = MapRSE
        else:
            maps_enum = MapFRLG

        try:
            maps_enum((map_group, map_number))
        except ValueError:
            return Response(f"No such map: {str(map_group)}, {str(map_number)}", status=404)

        map_data = get_map_data(map_group, map_number, local_position=(0, 0))
        return jsonify(
            {
                "map": map_data.dict_for_map(),
                "tiles": map_data.dicts_for_all_tiles(),
            }
        )

    @server.route("/party", methods=["GET"])
    def http_get_party():
        cached_party = state_cache.party
        if cached_party.age_in_frames > 5:
            work_queue.put_nowait(get_party)
            while cached_party.age_in_frames > 5:
                time.sleep(0.05)

        return jsonify([p.to_dict() for p in cached_party.value])

    @server.route("/opponent", methods=["GET"])
    def http_get_opponent():
        if state_cache.game_state.value != GameState.BATTLE:
            result = None
        else:
            cached_opponent = state_cache.opponent
            if cached_opponent.value is not None:
                result = cached_opponent.value.to_dict()
            else:
                result = None

        return jsonify(result)

    @server.route("/game_state", methods=["GET"])
    def http_get_game_state():
        return jsonify(get_game_state().name)

    @server.route("/encounter_log", methods=["GET"])
    def http_get_encounter_log():
        return jsonify(total_stats.get_encounter_log())

    @server.route("/shiny_log", methods=["GET"])
    def http_get_shiny_log():
        return jsonify(total_stats.get_shiny_log())

    @server.route("/encounter_rate", methods=["GET"])
    def http_get_encounter_rate():
        return jsonify({"encounter_rate": total_stats.get_encounter_rate()})

    @server.route("/stats", methods=["GET"])
    def http_get_stats():
        return jsonify(total_stats.get_total_stats())

    @server.route("/event_flags", methods=["GET"])
    def http_get_event_flags():
        flag = request.args.get("flag")

        if flag and flag in _event_flags:
            return jsonify({flag: get_event_flag(flag)})
        else:
            result = {}

            for flag in _event_flags:
                result[flag] = get_event_flag(flag)

            return result

    @server.route("/emulator", methods=["GET"])
    def http_get_emulator():
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

    @server.route("/fps", methods=["GET"])
    def http_get_fps():
        if context.emulator is None:
            return jsonify(None)
        else:
            return jsonify(list(reversed(context.emulator._performance_tracker.fps_history)))

    @server.route("/emulator", methods=["POST"])
    def http_post_emulator():
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
                if new_settings["bot_mode"] not in available_bot_modes:
                    return Response(
                        f"Setting `bot_mode` contains an invalid value ('{new_settings['bot_mode']}'). Possible values are: {', '.join(available_bot_modes)}",
                        status=422,
                    )
                context.bot_mode = new_settings["bot_mode"]
            elif key == "video_enabled":
                if not isinstance(new_settings["video_enabled"], bool):
                    return Response("Setting `video_enabled` did not contain a boolean value.", status=422)
                context.video = new_settings["video_enabled"]
            elif key == "audio_enabled":
                if not isinstance(new_settings["audio_enabled"], bool):
                    return Response("Setting `audio_enabled` did not contain a boolean value.", status=422)
                context.audio = new_settings["audio_enabled"]
            else:
                return Response(f"Unrecognised setting: '{key}'.", status=422)

        return http_get_emulator()

    @server.route("/routes", methods=["GET"])
    def http_get_routes():
        routes = {}

        for route in server.url_map._rules:
            routes[route.rule] = {}
            routes[route.rule]["functionName"] = route.endpoint
            routes[route.rule]["methods"] = list(route.methods)

        routes.pop("/static/<path:filename>")

        return jsonify(routes)

    @server.route("/", methods=["GET"])
    def http_index():
        index_file = Path(__file__).parent / "web" / "http_example.html"
        with open(index_file, "rb") as file:
            return Response(file.read(), content_type="text/html; charset=utf-8")

    server.run(
        debug=False,
        threaded=True,
        host=context.config.obs.http_server.ip,
        port=context.config.obs.http_server.port,
    )
