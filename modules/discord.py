import asyncio
import time
from asyncio import Queue, set_event_loop, new_event_loop, AbstractEventLoop
from dataclasses import dataclass
from pathlib import Path
from threading import Thread

from discord_webhook import DiscordEmbed, DiscordWebhook
from pypresence import Presence

from modules.console import console
from modules.context import context
from modules.state_cache import state_cache
from modules.version import pokebot_version

_event_loop: AbstractEventLoop | None = None
_message_queue: Queue["DiscordMessage"] = Queue()


@dataclass
class DiscordMessageEmbed:
    title: str | None = None
    description: str | None = None
    fields: dict[str, str] | None = None
    thumbnail: Path | None = None
    image: Path | None = None
    footer: str | None = None
    colour: str = "FFFFFF"


@dataclass
class DiscordMessage:
    webhook_url: str = None
    content: str = None
    image: Path = None
    embed: DiscordMessageEmbed | None = None
    delay: int | None = None


def discord_send(message: DiscordMessage) -> None:
    if not message.webhook_url and not context.config.discord.global_webhook_url:
        return
    elif not message.webhook_url:
        message.webhook_url = context.config.discord.global_webhook_url

    if message.delay is None:
        message.delay = context.config.discord.delay

    asyncio.run_coroutine_threadsafe(_message_queue.put(message), _event_loop)


async def _process_message(message: DiscordMessage) -> None:
    webhook = DiscordWebhook(url=message.webhook_url, content=message.content)

    # If one of the image files do not yet exist (which can happen as things like the
    # encounter GIF or the TCG cards are generated in a separate thread) delay
    # processing the message for a bit to allow those threads to catch up.
    # This will wait up to 5 seconds. If the image does not exist after that, it will
    # proceed without it.
    allowed_wait_time_in_seconds = 5

    async def wait_for_image_file_to_exist(image_file: Path) -> bool:
        nonlocal allowed_wait_time_in_seconds
        while not image_file.exists() or image_file.stat().st_size == 0:
            await asyncio.sleep(0.5)
            allowed_wait_time_in_seconds -= 0.5

        if not image_file.exists():
            console.print(
                f"[bold red]Discord Warning:[/] [red]The image file {str(image_file)} does not exist. Sending the message without that image.[/]"
            )
            return False
        else:
            return True

    if message.image is not None:
        if await wait_for_image_file_to_exist(message.image):
            with message.image.open("rb") as file:
                webhook.add_file(file=file.read(), filename=message.image.name)

    if message.embed is not None:
        embed = DiscordEmbed(title=message.embed.title, color=message.embed.colour)

        if message.embed.description:
            embed.description = message.embed.description

        if message.embed.fields is not None:
            for key, value in message.embed.fields.items():
                embed.add_embed_field(name=key, value=value, inline=False)

        if message.embed.thumbnail is not None:
            filename = "thumb.gif" if message.embed.thumbnail.name.endswith(".gif") else "thumb.png"
            if await wait_for_image_file_to_exist(message.embed.thumbnail):
                with message.embed.thumbnail.open("rb") as file:
                    webhook.add_file(file=file.read(), filename=filename)
                embed.set_thumbnail(url=f"attachment://{filename}")

        if message.embed.image is not None:
            filename = "embed.gif" if message.embed.image.name.endswith(".gif") else "embed.png"
            if await wait_for_image_file_to_exist(message.embed.image):
                with message.embed.image.open("rb") as file:
                    webhook.add_file(file=file.read(), filename=filename)
                embed.set_image(url=f"attachment://{filename}")

        if message.embed.footer:
            embed.set_footer(text=message.embed.footer)
        else:
            embed.set_footer(
                text=f"ID: {context.config.discord.bot_id} | {context.rom.game_name}\nPokéBot Gen3 {pokebot_version}"
            )

        embed.set_timestamp()
        webhook.add_embed(embed)

    if message.delay is not None and message.delay > 0:
        await asyncio.sleep(message.delay)

    webhook.execute()


def discord_rich_presence_loop() -> None:
    rpc = Presence("1125400717054713866")
    rpc.connect()
    start = time.time()

    if context.rom.is_ruby:
        large_image = "groudon"
    elif context.rom.is_sapphire:
        large_image = "kyogre"
    elif context.rom.is_emerald:
        large_image = "rayquaza"
    elif context.rom.is_fr:
        large_image = "charizard"
    elif context.rom.is_lg:
        large_image = "venusaur"
    else:
        large_image = None

    while True:
        location = "N/A"
        try:
            player_avatar = state_cache.player_avatar.value
            if player_avatar is not None:
                location = player_avatar.map_location.map_name.title()
        except:
            pass

        details = []

        try:
            global_stats = context.stats.get_global_stats()
            total_encounters = global_stats.totals.total_encounters
            shiny_encounters = global_stats.totals.shiny_encounters
            details.append(f"{total_encounters:,} ({shiny_encounters:,}✨)")
        except:
            pass

        try:
            encounter_rate = context.stats.encounter_rate
            details.append(f"{encounter_rate:,}/h")
        except:
            pass

        try:
            current_fps = context.emulator.get_current_fps()
            if current_fps > 0:
                details.append(f"{current_fps:,}fps ({current_fps / 59.727500569606:0.1f}×)")
        except:
            pass

        rpc.update(
            state=f"{location} | {context.rom.short_game_name}",
            details=" | ".join(details),
            large_image=large_image,
            start=int(start),
            buttons=[{"label": "⏬ Download PokéBot Gen3", "url": "https://github.com/40Cakes/pokebot-gen3"}],
        )

        time.sleep(15)


async def _handle_message_queue() -> None:
    while True:
        message = await _message_queue.get()
        await _process_message(message)


def discord_message_thread() -> None:
    global _event_loop

    _event_loop = new_event_loop()
    set_event_loop(_event_loop)

    _event_loop.create_task(_handle_message_queue())
    _event_loop.run_forever()
