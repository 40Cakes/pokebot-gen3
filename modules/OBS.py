import obsws_python as obs

from modules.Config import config_obs
from modules.Console import console


def OBSHotKey(obs_key: str,
              pressCtrl: bool = False,
              pressShift: bool = False,
              pressAlt: bool = False,
              pressCmd: bool = False):

    try:
        with obs.ReqClient(host=config_obs['obs_websocket']['host'],
                           port=config_obs['obs_websocket']['port'],
                           password=config_obs['obs_websocket']['password'],
                           timeout=5) as client:

            client.trigger_hot_key_by_key_sequence(obs_key,
                                                    pressCtrl=pressCtrl,
                                                    pressShift=pressShift,
                                                    pressAlt=pressAlt,
                                                    pressCmd=pressCmd)

    except:
        console.print_exception(show_locals=True)
