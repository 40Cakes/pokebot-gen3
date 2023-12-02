import obsws_python as obs

from modules.context import context


def obs_hot_key(
    obs_key: str, pressCtrl: bool = False, pressShift: bool = False, pressAlt: bool = False, pressCmd: bool = False
):
    with obs.ReqClient(
        host=context.config.obs.obs_websocket.host,
        port=context.config.obs.obs_websocket.port,
        password=context.config.obs.obs_websocket.password,
        timeout=5,
    ) as client:
        client.trigger_hot_key_by_key_sequence(
            obs_key, pressCtrl=pressCtrl, pressShift=pressShift, pressAlt=pressAlt, pressCmd=pressCmd
        )
