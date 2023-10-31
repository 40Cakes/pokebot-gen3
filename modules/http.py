from flask_cors import CORS
from flask import Flask, abort, jsonify, request

from modules.config import config
from modules.console import console
from modules.items import get_items
from modules.pokemon import get_party
from modules.stats import total_stats
from modules.game import _event_flags
from modules.memory import get_event_flag


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
                data = trainer.to_dict()
                if data:
                    return jsonify(data)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/items", methods=["GET"])
        def http_get_bag():
            try:
                data = get_items()
                if data:
                    return jsonify(data)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/party", methods=["GET"])
        def http_get_party():
            try:
                data = get_party()
                if data:
                    return jsonify([p.to_dict() for p in data])
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/encounter_log", methods=["GET"])
        def http_get_encounter_log():
            try:
                data = total_stats.get_encounter_log()
                if data:
                    return jsonify(data)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/shiny_log", methods=["GET"])
        def http_get_shiny_log():
            try:
                data = total_stats.get_shiny_log()
                if data:
                    return jsonify(data["shiny_log"])
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/encounter_rate", methods=["GET"])
        def http_get_encounter_rate():
            try:
                return jsonify({"encounter_rate": total_stats.get_encounter_rate()})
            except:
                console.print_exception(show_locals=True)
                return jsonify({"encounter_rate": 0})

        @server.route("/stats", methods=["GET"])
        def http_get_stats():
            try:
                data = total_stats.get_total_stats()
                if data:
                    return jsonify(data)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/event_flags", methods=["GET"])
        def http_get_event_flags():
            try:
                flag = request.args.get("flag")

                if flag and flag in _event_flags:
                    return(jsonify({flag: get_event_flag(flag)}))
                else:
                    result = {}

                    for flag in _event_flags:
                        result[flag] = get_event_flag(flag)

                    return result
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route("/", methods=["GET"])
        def http_get_routes():
            routes = {}
            for route in server.url_map._rules:
                routes[route.rule] = {}
                routes[route.rule]["functionName"] = route.endpoint
                routes[route.rule]["methods"] = list(route.methods)

            routes.pop("/static/<path:filename>")

            return jsonify(routes)

        server.run(
            debug=False,
            threaded=True,
            host=config["obs"]["http_server"]["ip"],
            port=config["obs"]["http_server"]["port"],
        )
    except:
        console.print_exception(show_locals=True)
