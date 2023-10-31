from flask_cors import CORS
from flask import Flask, abort, jsonify

from modules.config import config
from modules.console import console
from modules.context import context
from modules.items import get_items
from modules.pokemon import get_party
from modules.stats import get_encounter_rate, encounter_log, stats, shiny_log


def http_server() -> None:
    """
    Run Flask server to make bot data available via HTTP requests.
    """
    try:
        server = Flask(__name__)
        CORS(server)

        @server.route("/trainer", methods=["GET"])
        def http_get_trainer():
            from modules.trainer import trainer

            try:
                trainer = {
                    "name": trainer.get_name(),
                    "gender": trainer.get_gender(),
                    "tid": trainer.get_tid(),
                    "sid": trainer.get_sid(),
                    "map": trainer.get_map(),
                    "map_name": trainer.get_map_name(),
                    "coords": trainer.get_coords(),
                    "on_bike": trainer.get_on_bike(),
                    "facing": trainer.get_facing_direction(),
                }
                if trainer:
                    return jsonify(trainer)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/items", methods=["GET"])
        def http_get_bag():
            try:
                items = get_items()
                if items:
                    return jsonify(items)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/party", methods=["GET"])
        def http_get_party():
            try:
                party = get_party()
                if party:
                    return jsonify([p.to_json() for p in party])
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/encounter_log", methods=["GET"])  # TODO add parameter to get encounter by list index
        def http_get_encounter_log():
            try:
                if encounter_log:
                    return jsonify(encounter_log)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/shiny_log", methods=["GET"])
        def http_get_shiny_log():
            try:
                if shiny_log:
                    return jsonify(shiny_log["shiny_log"])
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/encounter_rate", methods=["GET"])
        def http_get_encounter_rate():
            try:
                return jsonify({"encounter_rate": get_encounter_rate()})
            except:
                console.print_exception(show_locals=True)
                return jsonify({"encounter_rate": 0})

        @server.route("/stats", methods=["GET"])
        def http_get_stats():
            try:
                if stats:
                    return jsonify(stats)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/emulator", methods=["GET"])
        def http_get_emulator():
            if context.emulator is None:
                return jsonify(None)
            else:
                return jsonify({
                    "emulation_speed": context.emulation_speed,
                    "video_enabled": context.video,
                    "audio_enabled": context.audio,
                    "bot_mode": context.bot_mode,
                    "current_message": context.message,
                    "frame_count": context.emulator.get_frame_count(),
                    "current_fps": context.emulator.get_current_fps(),
                    "profile": {
                        "name": context.profile.path.name
                    },
                    "game": {
                        "title": context.rom.game_title,
                        "name": context.rom.game_name,
                        "language": str(context.rom.language),
                        "revision": context.rom.revision
                    }
                })

        @server.route("/fps", methods=["GET"])
        def http_get_fps():
            if context.emulator is None:
                return jsonify(None)
            else:
                return jsonify(list(reversed(context.emulator._performance_tracker.fps_history)))

        server.run(
            debug=False,
            threaded=True,
            host=config["obs"]["http_server"]["ip"],
            port=config["obs"]["http_server"]["port"],
        )
    except:
        console.print_exception(show_locals=True)
