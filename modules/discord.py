import time
from pathlib import Path
from pypresence import Presence
from discord_webhook import DiscordWebhook, DiscordEmbed
from modules.config import config
from modules.context import context


def discord_message(
    webhook_url: str = None,
    content: str = None,
    image: str = None,
    embed: bool = False,
    embed_title: str = None,
    embed_description: str = None,
    embed_fields: object = None,
    embed_thumbnail: str | Path = None,
    embed_image: str | Path = None,
    embed_footer: str = None,
    embed_color: str = "FFFFFF",
) -> None:
    if not webhook_url:
        webhook_url = config["discord"]["global_webhook_url"]
    webhook, embed_obj = DiscordWebhook(url=webhook_url, content=content), None

    if image:
        with open(image, "rb") as f:
            webhook.add_file(file=f.read(), filename="image.png")

    if embed:
        embed_obj = DiscordEmbed(title=embed_title, color=embed_color)

        if embed_description:
            embed_obj.description = embed_description

        if embed_fields:
            for key, value in embed_fields.items():
                embed_obj.add_embed_field(name=key, value=value, inline=False)

        if embed_thumbnail:
            with open(embed_thumbnail, "rb") as f:
                webhook.add_file(file=f.read(), filename="thumb.png")
            embed_obj.set_thumbnail(url="attachment://thumb.png")

        if embed_image:
            with open(embed_image, "rb") as f:
                webhook.add_file(file=f.read(), filename="embed.png")
            embed_obj.set_image(url="attachment://embed.png")

        if embed_footer:
            embed_obj.set_footer(text=embed_footer)

        embed_obj.set_timestamp()
        webhook.add_embed(embed_obj)

    time.sleep(config["obs"]["discord_delay"])
    webhook.execute()


def discord_rich_presence() -> None:
    from modules.stats import total_stats
    from asyncio import new_event_loop as new_loop, set_event_loop as set_loop

    set_loop(new_loop())
    RPC = Presence("1125400717054713866")
    RPC.connect()
    start = time.time()

    match context.rom.game_title:
        case "POKEMON RUBY":
            large_image = "groudon"
        case "POKEMON SAPP":
            large_image = "kyogre"
        case "POKEMON EMER":
            large_image = "rayquaza"
        case "POKEMON FIRE":
            large_image = "charizard"
        case "POKEMON LEAF":
            large_image = "venusaur"

    while True:
        encounter_log = total_stats.get_encounter_log()
        totals = total_stats.get_total_stats()
        location = encounter_log[-1]["pokemon"]["metLocation"] if len(encounter_log) > 0 else "N/A"

        RPC.update(
            state=f"{location} | {context.rom.game_name}",
            details=(
                f'{totals["totals"].get("encounters", 0):,} ({totals["totals"].get("shiny_encounters", 0):,}✨) |'
                f" {total_stats.get_encounter_rate():,}/h"
            ),
            large_image=large_image,
            start=start,
            buttons=[{"label": "⏬ Download PokéBot", "url": "https://github.com/40Cakes/pokebot-gen3"}],
        )

        time.sleep(15)
