from flask_cors import CORS
from flask import Flask, jsonify, request
import asyncio
import websockets 
import json

from modules.config import config
from modules.context import context
from modules.items import get_items
from modules.pokemon import get_party
from modules.stats import total_stats
from modules.game import _event_flags
from modules.memory import get_event_flag, get_game_state
from modules.trainer import trainer  

class WebsocketHandler:
    """ This class hosts clients and updates. The clients are
    websockets that are connected. Updates are a list of
    type and data that are sent to each client (checked every second)"""
    
    def __init__(self):
        self.updates: list = []
        self.clients = set()
        
    def add_update(self, data, type) -> None:
        self.updates.append({"data" : data, "type" : type})
    
    def get_updates(self) -> list:
        updates_list = []
        while self.updates:
            updates_list.append(self.updates.pop())    
        return updates_list
    
    def add_client(self, websocket) -> None:
        self.clients.add(websocket)
    
    def remove_client(self, websocket) -> None:
        self.clients.remove(websocket)

    def get_clients(self) -> set():
        return self.clients

def websocket_server() -> None:
    """
    Run websockets to make the bot data available through a client
    """    
     
    async def handler(websocket):
        await asyncio.gather(
            consumer_handler(websocket),
            producer_handler(),
        )
    
    async def producer_handler():
        while True:
            await asyncio.sleep(1)
            messages = websocket_handler.get_updates()
            while messages:
                message = messages.pop()
                message = prep_data(message["data"], message["type"])
                for client in websocket_handler.get_clients():
                    await asyncio.create_task(send(client, message))

    async def consumer_handler(websocket):
        websocket_handler.add_client(websocket)
        try:
            # Begin loop to prevent websocket termination after just 1 message
            while True:
                message = await websocket.recv()
                message = message.lower()
                match message:
                    case "trainer" | "tr":
                        await websocket.send(ws_get_trainer())
                    
                    case "encounter log" | "el" | "enc log":
                        await websocket.send(ws_get_encounter_log())

                    case "items" | "it" | "bag" | "bg":
                        await websocket.send(ws_get_items())
                    
                    case "emulator" | "em" | "emu" :
                        await websocket.send(ws_get_emulator())
                        
                    case "party" | "pa" :
                        await websocket.send(ws_get_party())
                    
                    case "shiny" | "sh" | "shy":
                        await websocket.send(ws_get_shiny_log())
                        
                    case "stats" | "st" :
                        await websocket.send(ws_get_stats())
                    
                    case "encounter rate" | "er" | "enc rate":
                        await websocket.send(ws_get_encounter_rate())
                        
                    case "fps" :
                        await websocket.send(ws_get_fps())
                        
                    case "flags" | "event flags" | "ef" | "ev fl"  | "fl":
                        await websocket.send(ws_get_event_flags())
                        
                    # Unknown message
                    case _:
                        await websocket.send(prep_data(f"unknown message: {message}","unknown")) 
        except Exception as e:
            pass
        finally:
            websocket_handler.remove_client(websocket)
    
    async def send(websocket, message):
        try:
            await websocket.send(message)
        except websockets.ConnectionClosed:
            pass
    
    def prep_data(data, type: str):
        return json.dumps({"type" : type, "data" : data})
            
    
    def ws_get_trainer():
        data = trainer.to_dict()
        data["game_state"] = get_game_state().name
        return prep_data(data, "trainer")

    def ws_get_encounter_log():
        return prep_data(total_stats.get_encounter_log(), "encounter_log")
   
    def ws_get_items():
        return prep_data(get_items(),"items")

    def ws_get_party():
        return prep_data([p.to_dict() for p in get_party()], "party")

    def ws_get_shiny_log():
        return prep_data(total_stats.get_shiny_log(), "shiny_log")

    def ws_get_encounter_rate():
        return prep_data({"encounter_rate": total_stats.get_encounter_rate()}, "encounter_rate")

    def ws_get_stats():
        return prep_data(total_stats.get_total_stats(), "stats")

    def ws_get_event_flags():
        flag = request.args.get("flag")

        if flag and flag in _event_flags:
            return prep_data({flag: get_event_flag(flag)}, "flags")
        else:
            result = {}

            for flag in _event_flags:
                result[flag] = get_event_flag(flag)

            return prep_data(result, "flags")

    def ws_get_emulator():
        if context.emulator is None:
            return prep_data(None, "emulator")
        else:
            return prep_data(
                context.to_dict(), "emulator"
            )

    def ws_get_fps():
        if context.emulator is None:
            return prep_data(None, "fps")
        else:
            return prep_data(list(reversed(context.emulator._performance_tracker.fps_history)), "fps")

    async def main():
        host=config["obs"]["websocket_server"]["ip"]
        port=config["obs"]["websocket_server"]["port"]
        async with websockets.serve(handler, host, port):
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

websocket_handler = WebsocketHandler()