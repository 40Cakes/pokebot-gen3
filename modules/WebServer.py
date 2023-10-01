from typing import NoReturn
from flask_cors import CORS
from flask import Flask, abort, jsonify

from modules.Config import config_obs
from modules.Console import console
from modules.Items import GetItems
from modules.Pokemon import GetParty
from modules.Stats import GetEncounterRate, encounter_log, stats, shiny_log
from modules.Trainer import GetTrainer


def WebServer() -> NoReturn:
    """
    Run Flask server to make bot data available via HTTP requests.
    """
    try:
        server = Flask(__name__)
        CORS(server)

        @server.route('/trainer', methods=['GET'])
        def Trainer():
            try:
                trainer = GetTrainer()
                if trainer:
                    return jsonify(trainer)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route('/items', methods=['GET'])
        def Bag():
            try:
                items = GetItems()
                if items:
                    return jsonify(items)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route('/party', methods=['GET'])
        def Party():
            try:
                party = GetParty()
                if party:
                    return jsonify(party)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)
        @server.route('/encounter_log', methods=['GET'])  # TODO add parameter to get encounter by list index
        def EncounterLog():
            try:
                if encounter_log:
                    return jsonify(encounter_log['encounter_log'])
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route('/shiny_log', methods=['GET'])
        def ShinyLog():
            try:
                if shiny_log:
                    return jsonify(shiny_log['shiny_log'])
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route('/encounter_rate', methods=['GET'])
        def EncounterRate():
            try:
                return jsonify({'encounter_rate': GetEncounterRate()})
            except:
                console.print_exception(show_locals=True)
                return jsonify({'encounter_rate': 0})

        @server.route('/stats', methods=['GET'])
        def Stats():
            try:
                if stats:
                    return jsonify(stats)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        server.run(debug=False, threaded=True, host=config_obs['http_server']['ip'], port=config_obs['http_server']['port'])
    except:
        console.print_exception(show_locals=True)
