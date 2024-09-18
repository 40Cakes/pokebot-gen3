# OBS plugin
# This plugin allows the bot to send commands to OBS via WebSockets
# See [here](https://github.com/obsproject/obs-websocket) for more information on OBS WebSockets
# The bot does **not** emulate keystrokes, it simply sends a `TriggerHotkeyByKeySequence` (Ctrl + F11) WebSocket command
# OBS hotkeys: https://github.com/obsproject/obs-studio/blob/master/libobs/obs-hotkeys.h

import time
from pathlib import Path
from threading import Thread
from typing import TYPE_CHECKING
import obsws_python as obs

from modules.battle import BattleOutcome, BattleState, get_battle_state
from modules.console import console
from modules.context import context
from modules.discord import discord_message
from modules.encounter import judge_encounter
from modules.modes.util import save_the_game, wait_for_n_frames
from modules.plugin_interface import BotPlugin

if TYPE_CHECKING:
    from modules.pokemon import Pokemon

# OBS integration config
# OBS > Tools > Websocket Server Settings > Enable WebSocket Server
obs_websocket_ip = "127.0.0.1"
obs_websocket_port = 4455
obs_websocket_password = "password"
obs_discord_webhook_url = ""
obs_discord_delay = 0  # Wait n seconds before posting to Discord (prevents spoilers for livestream viewers)
# Relative dir to this file, must be set to the same directory in OBS (Settings > Output > Recording > Recording Path)
obs_replay_dir = Path(__file__).parent / "obs" / "replays"

# OBS screenshot config
obs_screenshot = False
obs_screenshot_hotkey = "OBS_KEY_F11"  # OBS > Settings > Hotkeys > "Screenshot Output" > CTRL+F11

# OBS replay buffer config
# OBS > Settings > Output > Replay Buffer > Enable (must be enabled for hotkey option to be visible)
obs_replay_buffer = False
obs_replay_buffer_hotkey = "OBS_KEY_F12"  # OBS > Settings > Hotkeys > "Save Replay" > CTRL+F12
obs_replay_buffer_delay = 0  # Wait n seconds before saving OBS replay buffer


def wait(seconds: float):
    for _ in range(round(seconds * 60)):
        yield


def obs_hot_key(
    obs_key: str, pressCtrl: bool = False, pressShift: bool = False, pressAlt: bool = False, pressCmd: bool = False
):
    try:
        with obs.ReqClient(
            host=obs_websocket_ip,
            port=obs_websocket_port,
            password=obs_websocket_password,
            timeout=5,
        ) as client:
            client.trigger_hot_key_by_key_sequence(
                obs_key, pressCtrl=pressCtrl, pressShift=pressShift, pressAlt=pressAlt, pressCmd=pressCmd
            )

    except Exception:
        console.print_exception(show_locals=True)


class OBSPlugin(BotPlugin):
    def on_battle_started(self, opponent: "Pokemon") -> None:
        try:
            if not judge_encounter(opponent).is_of_interest:
                return

            if obs_screenshot:
                while get_battle_state() != BattleState.ACTION_SELECTION:
                    context.emulator.press_button("B")  # Throw out Pokémon for Discord screenshot
                    yield
                # Wait a few seconds to give overlays some time to get up to date
                yield from wait_for_n_frames(300 * context.emulation_speed)
                obs_hot_key(obs_screenshot_hotkey, pressCtrl=True)

                # Post the most recent OBS stream screenshot to Discord
                if obs_discord_webhook_url and opponent.is_shiny:
                    def send_obs_discord_screenshot():
                        time.sleep(3)  # Give OBS some time to save screenshot to disk
                        # Find the most recent screenshot in replays folder
                        images = obs_replay_dir.glob("*.png")
                        image = max(list(images), key=lambda item: item.stat().st_ctime)
                        time.sleep(obs_discord_delay)
                        discord_message(webhook_url=obs_discord_webhook_url, image=Path(image))

                    Thread(target=send_obs_discord_screenshot).start()

                # Save OBS replay buffer n seconds after encountering a shiny
                if obs_replay_buffer and opponent.is_shiny:
                    def save_obs_replay_buffer():
                        time.sleep(obs_replay_buffer_delay)
                        obs_hot_key(obs_replay_buffer_hotkey, pressCtrl=True)

                    Thread(target=save_obs_replay_buffer).start()

        except Exception:
            console.print_exception(show_locals=True)

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if outcome is BattleOutcome.Caught:
            yield from save_the_game()
