import time
from pathlib import Path

from discord_webhook import DiscordEmbed, DiscordWebhook
from pypresence import Presence

from modules.context import context
from modules.version import pokebot_version


def discord_message(
    webhook_url: str = None,
    content: str = None,
    image: Path = None,
    embed: bool = False,
    embed_title: str = None,
    embed_description: str = None,
    embed_fields: dict = None,
    embed_thumbnail: str | Path = None,
    embed_image: Path = None,
    embed_footer: str = None,
    embed_color: str = "FFFFFF",
) -> None:
    if not (webhook_url := webhook_url or context.config.discord.global_webhook_url):
        return
    webhook, embed_obj = DiscordWebhook(url=webhook_url, content=content), None

    if image:
        with open(image, "rb") as f:
            webhook.add_file(file=f.read(), filename=image.name)

    if embed:
        embed_obj = DiscordEmbed(title=embed_title, color=embed_color)

        if embed_description:
            embed_obj.description = embed_description

        if embed_fields:
            for key, value in embed_fields.items():
                embed_obj.add_embed_field(name=key, value=value, inline=False)

        if embed_thumbnail:
            filename = "thumb.gif" if str(embed_thumbnail).endswith(".gif") else "thumb.png"
            with open(embed_thumbnail, "rb") as f:
                webhook.add_file(file=f.read(), filename=filename)
            embed_obj.set_thumbnail(url=f"attachment://{filename}")

        if embed_image:
            filename = "embed.gif" if embed_image.name.endswith(".gif") else "embed.png"
            with open(embed_image, "rb") as f:
                webhook.add_file(file=f.read(), filename=filename)
            embed_obj.set_image(url=f"attachment://{filename}")

        if embed_footer:
            embed_obj.set_footer(text=embed_footer)
        else:
            embed_obj.set_footer(
                text=f"ID: {context.config.discord.bot_id} | {context.rom.game_name}\nPokéBot Gen3 {pokebot_version}"
            )

        embed_obj.set_timestamp()
        webhook.add_embed(embed_obj)

    time.sleep(context.config.obs.discord_delay)
    webhook.execute()


def discord_rich_presence() -> None:
    from modules.stats import total_stats
    from asyncio import new_event_loop as new_loop, set_event_loop as set_loop

    set_loop(new_loop())
    rpc = Presence("1125400717054713866")
    rpc.connect()
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
        case _:
            large_image = None

    while True:
        encounter_log = total_stats.get_encounter_log()
        totals = total_stats.get_total_stats()
        location = encounter_log[-1]["pokemon"]["metLocation"] if len(encounter_log) > 0 else "N/A"
        current_fps = context.emulator.get_current_fps()

        rpc.update(
            state=f"{location} | {context.rom.game_name}",
            details=(
                f"{totals.get('totals', {}).get('encounters', 0):,} ({totals.get('totals', {}).get('shiny_encounters', 0):,}✨) | "
                f"{total_stats.get_encounter_rate():,}/h | "
                f"{current_fps:,}fps ({current_fps / 59.727500569606:0.2f}x)"
            ),
            large_image=large_image,
            start=int(start),
            buttons=[{"label": "⏬ Download PokéBot Gen3", "url": "https://github.com/40Cakes/pokebot-gen3"}],
        )

        time.sleep(15)
