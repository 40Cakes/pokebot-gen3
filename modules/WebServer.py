from flask import Flask, abort, jsonify
from flask_cors import CORS

from modules.Config import config_obs
from modules.Console import console
from modules.Memory import GetTrainer, GetParty, GetItems
from modules.Stats import GetEncounterLog, GetStats, GetEncounterRate, GetShinyLog


def WebServer():
    """
    Run Flask server to make bot data available via HTTP GET
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

        @server.route('/encounter', methods=['GET'])
        def Encounter():
            try:
                encounter_logs = GetEncounterLog()['encounter_log']
                if len(encounter_logs) > 0 and encounter_logs[-1]['pokemon']:
                    encounter = encounter_logs.pop()['pokemon']
                    stats = GetStats()
                    if stats:
                        try:
                            encounter['stats'] = stats['pokemon'][encounter['name']]
                            return jsonify(encounter)
                        except:
                            abort(503)
                    return jsonify(encounter)
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
                stats = GetStats()
                if stats:
                    return jsonify(stats)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route('/encounter_log', methods=['GET'])
        def EncounterLog():
            try:
                recent_encounter_log = GetEncounterLog()['encounter_log'][-25:]
                if recent_encounter_log:
                    encounter_log = {'encounter_log': recent_encounter_log}
                    return jsonify(encounter_log)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        @server.route('/shiny_log', methods=['GET'])
        def ShinyLog():
            try:
                shiny_log = GetShinyLog()
                if shiny_log:
                    return jsonify(shiny_log)
                abort(503)
            except:
                console.print_exception(show_locals=True)
                abort(503)

        server.run(debug=False, threaded=True, host=config_obs['server']['ip'], port=config_obs['server']['port'])
    except:
        console.print_exception(show_locals=True)
