from flask_cors import CORS
from flask import Flask, jsonify, request
import asyncio
from websockets.server import serve
import json

from modules.config import config
from modules.context import context
from modules.items import get_items
from modules.pokemon import get_party
from modules.stats import total_stats
from modules.game import _event_flags
from modules.memory import get_event_flag, get_game_state
from modules.trainer import trainer


# Return back to the client whatever is sent to the server      

def websocket_server() -> None:
    """
    Run websockets to make the bot data available through a client
    """

    options = ["player"]
       
    # Message received        
    async def handler(websocket, path):
        message = await websocket.recv()
            
        message = message.lower()
        match message:
            case "trainer" | "tr":
                await websocket.send(ws_get_trainer())
            
            case "encounter log" | "el" | "enc log":
                await websocket.send(wg_get_encounter_log())

            case "items" | "it" | "bag" | "bg":
                await websocket.send(wg_get_items())
            
            case "emulator" | "em" | "emu" :
                await websocket.send(wg_get_emulator())
                
            case "party" | "pa" :
                await websocket.send(wg_get_party())
            
            case "shiny" | "sh" | "shy":
                await websocket.send(wg_get_shiny_log())
                
            case "stats" | "st" :
                await websocket.send(wg_get_stats())
            
            case "encounter rate" | "er" | "enc rate":
                await websocket.send(wg_get_encounter_rate())
                
            case "fps" :
                await websocket.send(wg_get_fps())
                
            case "flags" | "event flags" | "ef" | "ev fl"  | "fl":
                await websocket.send(wg_get_event_flags())
            # Unknown message
            case _:
                await websocket.send(prep_data(f"unknown message: {message}","unknown"))
    
    def prep_data(obj, type):
        data = dict()
        data["data"] = obj
        data["type"] = type
        return json.dumps(data)
    
    def ws_get_trainer():
        data = trainer.to_dict()
        data["game_state"] = get_game_state().name
        return prep_data(data, "trainer")

    def wg_get_encounter_log():
        return prep_data(total_stats.get_encounter_log(), "encounter_log")
   
    def wg_get_items():
        return prep_data(get_items(),"items")

    def wg_get_party():
        return prep_data([p.to_dict() for p in get_party()], "party")

    def wg_get_shiny_log():
        return prep_data(total_stats.get_shiny_log(), "shiny_log")

    def wg_get_encounter_rate():
        return prep_data({"encounter_rate": total_stats.get_encounter_rate()}, "encounter_rate")

    def wg_get_stats():
        return prep_data(total_stats.get_total_stats(), "stats")

    def wg_get_event_flags():
        flag = request.args.get("flag")

        if flag and flag in _event_flags:
            return prep_data({flag: get_event_flag(flag)}, "flags")
        else:
            result = {}

            for flag in _event_flags:
                result[flag] = get_event_flag(flag)

            return prep_data(result, "flags")

    def wg_get_emulator():
        if context.emulator is None:
            return prep_data(None, "emulator")
        else:
            return prep_data(
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
                }, "emulator"
            )

    def wg_get_fps():
        if context.emulator is None:
            return prep_data(None, "fps")
        else:
            return prep_data(list(reversed(context.emulator._performance_tracker.fps_history)), "fps")

    async def main():
        host=config["obs"]["websocket"]["ip"]
        port=config["obs"]["websocket"]["port"]
        async with serve(handler, host, port):
            await asyncio.Future()  # run forever

    # Start the websocket
    asyncio.run(main())


def http_server() -> None:
    """
    Run Flask server to make bot data available via HTTP requests.
    """
    server = Flask(__name__)
    CORS(server)

    @server.route("/trainer", methods=["GET"])
    def http_get_trainer():
        data = trainer.to_dict()
        data["game_state"] = get_game_state().name
        return jsonify(data)

    @server.route("/items", methods=["GET"])
    def http_get_bag():
        return jsonify(get_items())

    @server.route("/party", methods=["GET"])
    def http_get_party():
        return jsonify([p.to_dict() for p in get_party()])

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
