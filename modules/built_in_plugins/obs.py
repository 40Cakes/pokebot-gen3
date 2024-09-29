# OBS plugin
# This plugin allows the bot to send commands to OBS via WebSockets
# See [here](https://github.com/obsproject/obs-websocket) for more information on OBS WebSockets
# The bot does **not** emulate keystrokes, it simply sends a `TriggerHotkeyByKeySequence` (Ctrl + F11) WebSocket command
# OBS hotkeys: https://github.com/obsproject/obs-studio/blob/master/libobs/obs-hotkeys.h
import base64
import time
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import TYPE_CHECKING, Generator

import obsws_python as obs
from black import datetime

from modules.console import console
from modules.context import context
from modules.discord import discord_send, DiscordMessage
from modules.plugin_interface import BotPlugin

if TYPE_CHECKING:
    from modules.encounter import ActiveWildEncounter
    from modules.profiles import Profile


def _obs_screenshot(client: obs.ReqClient, width: int, height: int) -> Path:
    current_scene_name = client.get_current_program_scene().current_program_scene_name
    screenshots_dir = context.profile.path / "screenshots" / "obs"
    if not screenshots_dir.exists():
        screenshots_dir.mkdir(parents=True)

    file_name = datetime.now().isoformat() + ".png"
    file_path = screenshots_dir / file_name

    with file_path.open("wb") as file:
        file.write(
            base64.b64decode(
                client.get_source_screenshot(
                    name=current_scene_name,
                    img_format="png",
                    width=width,
                    height=height,
                    quality=-1,
                ).image_data[22:]
            )
        )

    return file_path


def _obs_thread(task_queue: Queue[str]):
    with obs.ReqClient(
        host=context.config.obs.obs_websocket.host,
        port=context.config.obs.obs_websocket.port,
        password=context.config.obs.obs_websocket.password,
        timeout=5,
    ) as client:
        video_settings = client.get_video_settings()
        video_width = video_settings.base_width
        video_height = video_settings.base_height

        version = client.get_version()
        if "png" not in version.supported_image_formats:
            raise RuntimeError("OBS does not support PNG, so taking screenshots is not going to work.")

        while True:
            task = task_queue.get()

            if task == "save_screenshot":
                if context.config.obs.shiny_delay > 0:
                    time.sleep(context.config.obs.shiny_delay)
                _obs_screenshot(client, video_width, video_height)

            elif task == "save_screenshot_and_send_to_discord":
                if context.config.obs.shiny_delay > 0:
                    time.sleep(context.config.obs.shiny_delay)
                image_file = _obs_screenshot(client, video_width, video_height)
                if context.config.obs.discord_webhook_url:
                    if context.config.obs.discord_delay > 0:
                        time.sleep(context.config.obs.discord_delay)
                    discord_send(
                        DiscordMessage(
                            webhook_url=context.config.obs.discord_webhook_url,
                            image=image_file,
                        )
                    )

            elif task == "save_replay_buffer":
                if context.config.obs.replay_buffer_delay > 0:
                    time.sleep(context.config.obs.replay_buffer_delay)
                client.save_replay_buffer()

            else:
                console.print("[bold red]OBS Plugin:[/] [red]Unknown task: " + task + "[/]")


class OBSPlugin(BotPlugin):
    def __init__(self):
        self._task_queue: Queue[str] = Queue()

    def on_profile_loaded(self, profile: "Profile") -> None:
        Thread(target=_obs_thread, args=(self._task_queue,)).start()

    def on_wild_encounter_visible(self, wild_encounter: "ActiveWildEncounter") -> Generator | None:
        if not wild_encounter.value.is_of_interest:
            return

        # Save a screenshot of the OBS output after encountering a Pokémon of interest.
        if context.config.obs.screenshot:
            if wild_encounter.pokemon.is_shiny:
                self._task_queue.put("save_screenshot_and_send_to_discord")
            else:
                self._task_queue.put("save_screenshot")

        # Save OBS replay buffer n seconds after encountering a shiny.
        if context.config.obs.replay_buffer and wild_encounter.pokemon.is_shiny:
            self._task_queue.put("save_replay_buffer")
