import obsws_python as obs

from modules.config import config


def obs_hot_key(
    obs_key: str, pressCtrl: bool = False, pressShift: bool = False, pressAlt: bool = False, pressCmd: bool = False
):
    try:
        with obs.ReqClient(
            host=config["obs"]["obs_websocket"]["host"],
            port=config["obs"]["obs_websocket"]["port"],
            password=config["obs"]["obs_websocket"]["password"],
            timeout=5,
        ) as client:
            client.trigger_hot_key_by_key_sequence(
                obs_key, pressCtrl=pressCtrl, pressShift=pressShift, pressAlt=pressAlt, pressCmd=pressCmd
            )
    except:
        pass
