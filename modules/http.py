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
    """ This class hosts websockets, updates and subscriptions. The websockets are
    websockets that are connected. Updates are a list of
    type and data that are sent to each websocket (checked every second)"""
    
    def __init__(self) -> None:
        self.updates: list = []
        self.websockets = dict()
    
    def prep_data(self, type: str, data) -> str:
        """Takes type and data and transforms it first into
        a dict, then a stringifyed json for sending over the websocket"""

        return json.dumps({"type" : type, "data" : data})
    
    def add_update(self, type: str, data = None) -> str:
        """Subscribed websockets to be notified of an event by adding an entry for each
        websocket's dictionary entry"""
        
        # Update the data based on the type
        match type:
            case "encounter":
                self.add_update("stats") # Add stats update 
                self.add_update("encounter_log")    # Add encounter log update
                pass    
            case "stats":
                data = self.get_stats()
            case "encounter_log":
                data = self.get_encounter_log()
            case "emulator":
                data = self.get_emulator()
            case _ :
                data = None
    
        if data != None:
            # Add update to each subbed websocket
            for websocket in self.websockets:
                if type in self.websockets[websocket]["subscriptions"]:
                    self.websockets[websocket]["updates"].append(self.prep_data(type, data))
    
    def subscribe(self, data, websocket) -> str:
        """Message from websocket requests a subscription,
        so add it to the appropriate dict entry. Subs can be sent
        in list format, requiring only 1 message from websocket to subscribe
        to more than one service"""
        
        for sub in data:
            if sub not in self.websockets[websocket]["subscriptions"]:
                self.websockets[websocket]["subscriptions"].append(sub)
        return  f"subscribed to {data}"
 
    def publish(self, websocket) -> list:
        """Returns the full list of updates for a specific websocket and removes them"""
        
        updates_list = []
        while self.websockets[websocket]["updates"]:
            updates_list.append(self.websockets[websocket]["updates"].pop())   
    
        return updates_list
        
    def read_message(self, message, websocket) -> str:
        """Message received by the websocket, return appropriate data"""
        
        message = json.loads(message)
        type = message["type"]
        data = message["data"]
        match type:
            case "SUB":
                rtn = self.subscribe(data, websocket)
                return self.prep_data("notification", rtn)
            case "GET":
                return self.get_update(data)
            case _:
                return self.prep_data("Unknown", {"message" : f"Unknown type '{type}'"})
    
    def add_websocket(self, websocket) -> None:
        """Generates a dict entry for the websocket"""
        self.websockets[websocket] = {
            "subscriptions" : list(),
            "updates" : list()
        }
    
    def get_websockets(self) -> dict:
        """Returns the websockets dict"""
        return self.websockets
    
    def remove_websocket(self, websocket) -> None:
        """Remove a websocket and its subscriptions"""
        
        del self.websockets[websocket]
    
    def get_update(self, type) -> str:
        """Message from websocket wants data update, return as such"""
        data = None
        match type:
            case "encounter_log":
                data = self.get_encounter_log()
            case "encounter_rate":
                data = self.get_encounter_rate()
            case "emulator":
                data = self.get_emulator()
            case "party":
                data = self.get_party()
            case "fps":
                data = self.get_fps()
            case "event_flags": 
                data = self.get_event_flags()
            case "items":
                data = self.get_items()
            case "shiny_log":
                data = self.get_shiny_log()
            case "stats":
                data = self.get_stats()
            case "trainer":
                data = self.get_trainer()
            case _ :
                data = None
            
        if data == None:
            return self.prep_data("Unknown", {"message" : f"Unknown GET type '{type}'"})
        else:
            return self.prep_data(type, data)
        
            
    def get_trainer(self) -> dict:
        data = trainer.to_dict()
        data["game_state"] = get_game_state().name
        return data

    def get_encounter_log(self) -> dict:
        return total_stats.get_encounter_log() 
   
    def get_items(self) -> dict:
        return get_items()

    def get_party(self) -> dict:
        return [p.to_dict() for p in get_party()]

    def get_shiny_log(self) -> dict:
        return total_stats.get_shiny_log()

    def get_encounter_rate(self) -> dict:
        return {"encounter_rate": total_stats.get_encounter_rate()}

    def get_stats(self) -> dict:
        return total_stats.get_total_stats()

    def get_event_flags(self) -> dict:
        flag = request.args.get("flag")

        if flag and flag in _event_flags:
            return {flag: get_event_flag(flag)}
        else:
            result = {}

            for flag in _event_flags:
                result[flag] = get_event_flag(flag)

            return result

    def get_emulator(self) -> dict:
        if context.emulator is None:
            return None
        else:
            return  context.to_dict()

    def get_fps(self) -> list:
        if context.emulator is None:
            return None, "fps"
        else:
            return list(reversed(context.emulator._performance_tracker.fps_history))

def websocket_server() -> None:
    """
    Makes bot data available through a websocket
    """   
        
    async def handler(websocket):
        """Handles requests in and out of the websocket"""
        websocket_handler.add_websocket(websocket)
        await asyncio.gather(
            consumer_handler(websocket),
            producer_handler(websocket)
        )
    
                    
    async def producer_handler(websocket):                
        """Pushes out updates/events to websockets using the
        WebsocketHandler class. Checks the list every second"""
        
        while True:
            await asyncio.sleep(1)
            updates = websocket_handler.publish(websocket)
            while updates:
                message = updates.pop()
                if message != None:
                    await asyncio.create_task(send(websocket, message))
    
    async def consumer_handler(websocket):
        """Responds to websocket messages"""
        
        
        try:
            # Begin loop to prevent websocket termination after just 1 message
            while True:
                
                message = await websocket.recv()
                 # All different cases are handled by the WebsocketHandler class
                await websocket.send(websocket_handler.read_message(message, websocket))

        except Exception as e:
            pass
        finally:
            websocket_handler.remove_websocket(websocket)
    
    async def send(websocket, message):
        """Sends a message to the websocket"""
        try:
            await websocket.send(message)
        except websockets.ConnectionClosed:
            pass

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