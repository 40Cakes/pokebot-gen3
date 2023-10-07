import obsws_python as obs

from modules.Config import config
from modules.Console import console


def OBSHotKey(obs_key: str,
              pressCtrl: bool = False,
              pressShift: bool = False,
              pressAlt: bool = False,
              pressCmd: bool = False):

    try:
        with obs.ReqClient(host=config['obs']['obs_websocket']['host'],
                           port=config['obs']['obs_websocket']['port'],
                           password=config['obs']['obs_websocket']['password'],
                           timeout=5) as client:

            client.trigger_hot_key_by_key_sequence(obs_key,
                                                    pressCtrl=pressCtrl,
                                                    pressShift=pressShift,
                                                    pressAlt=pressAlt,
                                                    pressCmd=pressCmd)

    except:
        console.print_exception(show_locals=True)
