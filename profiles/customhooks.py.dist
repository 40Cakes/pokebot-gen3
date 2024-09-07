import glob
import os
import random
import time
from pathlib import Path
from threading import Thread

from modules.console import console
from modules.context import context
from modules.discord import discord_message
from modules.files import make_string_safe_for_file_name
from modules.pokemon import Pokemon
from modules.runtime import get_sprites_path


def custom_hooks(hook) -> None:
    """
    This function is called every time an encounter is logged, but before phase stats are reset (if shiny)
    this file is useful for custom webhooks or logging to external databases if you understand Python

    Note: this function runs in a thread and will not hold up the bot if you need to run any slow hooks
    """
    # Deep copy of Pokémon and stats dictionaries when the thread was called to avoid main thread overwriting vars
    pokemon: Pokemon = hook[0]
    stats = hook[1]
    block_list = hook[2]
    custom_filter_result = hook[3]
    gif_path = hook[4]
    tcg_path = hook[5]

    try:
        ### Your custom code goes here ###

        # Discord messages
        def iv_field() -> str:
            # Formatted IV table
            if context.config.discord.iv_format == "formatted":
                iv_field = (
                    "```"
                    "╔═══╤═══╤═══╤═══╤═══╤═══╗\n"
                    "║HP │ATK│DEF│SPA│SPD│SPE║\n"
                    "╠═══╪═══╪═══╪═══╪═══╪═══╣\n"
                    f"║{pokemon.ivs.hp:^3}│"
                    f"{pokemon.ivs.attack:^3}│"
                    f"{pokemon.ivs.defence:^3}│"
                    f"{pokemon.ivs.special_attack:^3}│"
                    f"{pokemon.ivs.special_defence:^3}│"
                    f"{pokemon.ivs.speed:^3}║\n"
                    "╚═══╧═══╧═══╧═══╧═══╧═══╝"
                    "```"
                )
            else:
                # Basic IV table
                iv_field = (
                    f"HP: {pokemon.ivs.hp} | "
                    f"ATK: {pokemon.ivs.attack} | "
                    f"DEF: {pokemon.ivs.defence} | "
                    f"SPATK: {pokemon.ivs.special_attack} | "
                    f"SPDEF: {pokemon.ivs.special_defence} | "
                    f"SPE: {pokemon.ivs.speed}"
                )
            return iv_field

        def phase_summary() -> dict:
            from modules.stats import total_stats  # TODO prevent instantiating TotalStats class before profile selected

            sparkle = "✨" if stats["totals"].get("phase_lowest_sv", -1) < 8 else ""
            return {
                "Phase Encounters": f"{stats['totals'].get('phase_encounters', -1):,} ({total_stats.get_encounter_rate():,}/h)",
                "Phase IV Sum Records": (
                    f":arrow_up: `{stats['totals'].get('phase_highest_iv_sum', -1):,}` IV {stats['totals'].get('phase_highest_iv_sum_pokemon', 'N/A')}\n"
                    f":arrow_down: `{stats['totals'].get('phase_lowest_iv_sum', -1):,}` IV {stats['totals'].get('phase_lowest_iv_sum_pokemon', 'N/A')}"
                ),
                "Phase SV Records": (
                    f":arrow_up: `{stats['totals'].get('phase_highest_sv', -1):,}` SV {stats['totals'].get('phase_highest_sv_pokemon', 'N/A')}\n"
                    f":arrow_down: `{stats['totals'].get('phase_lowest_sv', -1):,}` SV {sparkle}{stats['totals'].get('phase_lowest_sv_pokemon', 'N/A')}{sparkle}"
                ),
                "Phase Same Pokémon Streak": (
                    f"{stats['totals'].get('phase_streak', -1):,} {stats['totals'].get('phase_streak_pokemon', 'N/A')} were encountered in a row!"
                ),
                "Total Encounters": (
                    f"{stats['totals'].get('encounters', -1):,} ({stats['totals'].get('shiny_encounters', -1):,}✨)"
                ),
            }

        try:
            # Discord shiny Pokémon encountered
            if context.config.discord.shiny_pokemon_encounter.enable and pokemon.is_shiny:
                # Discord pings
                discord_ping = ""
                match context.config.discord.shiny_pokemon_encounter.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.shiny_pokemon_encounter.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.shiny_pokemon_encounter.ping_id}>"

                block = (
                    "\n❌Skipping catching shiny (on catch block list)!"
                    if pokemon.species_name_for_stats in block_list or pokemon.species.name in block_list
                    else ""
                )

                discord_message(
                    webhook_url=context.config.discord.shiny_pokemon_encounter.webhook_url,
                    content=f"Encountered a shiny ✨ {pokemon.species_name_for_stats} ✨! {block}\n{discord_ping}",
                    embed=True,
                    embed_title="Shiny encountered!",
                    embed_description=(
                        f"{pokemon.nature.name} {pokemon.species_name_for_stats} (Lv. {pokemon.level:,}) at {pokemon.location_met}!"
                    ),
                    embed_fields={
                        "Shiny Value": f"{pokemon.shiny_value:,}",
                        f"IVs ({pokemon.ivs.sum()})": iv_field(),
                        "Held item": pokemon.held_item.name if pokemon.held_item else "None",
                        f"{pokemon.species_name_for_stats} Encounters": f"{stats['pokemon'][pokemon.species_name_for_stats].get('encounters', 0):,} ({stats['pokemon'][pokemon.species_name_for_stats].get('shiny_encounters', 0):,}✨)",
                        f"{pokemon.species_name_for_stats} Phase Encounters": f"{stats['pokemon'][pokemon.species_name_for_stats].get('phase_encounters', 0):,}",
                    }
                    | phase_summary(),
                    embed_thumbnail=get_sprites_path()
                    / "pokemon"
                    / "shiny"
                    / f"{make_string_safe_for_file_name(pokemon.species_name_for_stats)}.png",
                    embed_color="ffd242",
                    embed_image=gif_path,
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord Pokémon encounter milestones
            if (
                context.config.discord.pokemon_encounter_milestones.enable
                and stats["pokemon"][pokemon.species_name_for_stats].get("encounters", -1)
                % context.config.discord.pokemon_encounter_milestones.interval
                == 0
            ):
                # Discord pings
                discord_ping = ""
                match context.config.discord.pokemon_encounter_milestones.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.pokemon_encounter_milestones.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.pokemon_encounter_milestones.ping_id}>"
                discord_message(
                    webhook_url=context.config.discord.pokemon_encounter_milestones.webhook_url,
                    content=f"🎉 New milestone achieved!\n{discord_ping}",
                    embed=True,
                    embed_description=f"{stats['pokemon'][pokemon.species_name_for_stats].get('encounters', 0):,} {pokemon.species_name_for_stats} encounters!",
                    embed_thumbnail=get_sprites_path()
                    / "pokemon"
                    / "normal"
                    / f"{make_string_safe_for_file_name(pokemon.species_name_for_stats)}.png",
                    embed_color="50C878",
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord shiny Pokémon encounter milestones
            if (
                context.config.discord.shiny_pokemon_encounter_milestones.enable
                and pokemon.is_shiny
                and stats["pokemon"][pokemon.species_name_for_stats].get("shiny_encounters", -1)
                % context.config.discord.shiny_pokemon_encounter_milestones.interval
                == 0
            ):
                # Discord pings
                discord_ping = ""
                match context.config.discord.shiny_pokemon_encounter_milestones.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.shiny_pokemon_encounter_milestones.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.shiny_pokemon_encounter_milestones.ping_id}>"
                discord_message(
                    webhook_url=context.config.discord.shiny_pokemon_encounter_milestones.webhook_url,
                    content=f"🎉 New milestone achieved!\n{discord_ping}",
                    embed=True,
                    embed_description=f"{stats['pokemon'][pokemon.species_name_for_stats].get('shiny_encounters', 0):,} shiny ✨ {pokemon.species_name_for_stats} ✨ encounters!",
                    embed_thumbnail=get_sprites_path()
                    / "pokemon"
                    / "shiny"
                    / f"{make_string_safe_for_file_name(pokemon.species_name_for_stats)}.png",
                    embed_color="ffd242",
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord total encounter milestones
            if (
                context.config.discord.total_encounter_milestones.enable
                and stats["totals"].get("encounters", -1) % context.config.discord.total_encounter_milestones.interval
                == 0
            ):
                # Discord pings
                discord_ping = ""
                match context.config.discord.total_encounter_milestones.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.total_encounter_milestones.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.total_encounter_milestones.ping_id}>"

                embed_thumbnail = random.choice(
                    [
                        "Dive Ball",
                        "Great Ball",
                        "Light Ball",
                        "Luxury Ball",
                        "Master Ball",
                        "Nest Ball",
                        "Net Ball",
                        "Poké Ball",
                        "Premier Ball",
                        "Repeat Ball",
                        "Safari Ball",
                        "Smoke Ball",
                        "Timer Ball",
                        "Ultra Ball",
                    ]
                )

                discord_message(
                    webhook_url=context.config.discord.total_encounter_milestones.webhook_url,
                    content=f"🎉 New milestone achieved!\n{discord_ping}",
                    embed=True,
                    embed_description=f"{stats['totals'].get('encounters', 0):,} total encounters!",
                    embed_thumbnail=get_sprites_path() / "items" / f"{embed_thumbnail}.png",
                    embed_color="50C878",
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord phase encounter notifications
            if (
                context.config.discord.phase_summary.enable
                and not pokemon.is_shiny
                and (
                    stats["totals"].get("phase_encounters", -1) == context.config.discord.phase_summary.first_interval
                    or (
                        stats["totals"].get("phase_encounters", -1)
                        > context.config.discord.phase_summary.first_interval
                        and stats["totals"].get("phase_encounters", -1)
                        % context.config.discord.phase_summary.consequent_interval
                        == 0
                    )
                )
            ):
                # Discord pings
                discord_ping = ""
                match context.config.discord.phase_summary.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.phase_summary.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.phase_summary.ping_id}>"
                discord_message(
                    webhook_url=context.config.discord.phase_summary.webhook_url,
                    content=f"💀 The current phase has reached {stats['totals'].get('phase_encounters', 0):,} encounters!\n{discord_ping}",
                    embed=True,
                    embed_fields=phase_summary(),
                    embed_color="D70040",
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord anti-shiny Pokémon encountered
            if context.config.discord.anti_shiny_pokemon_encounter.enable and pokemon.is_anti_shiny:
                # Discord pings
                discord_ping = ""
                match context.config.discord.anti_shiny_pokemon_encounter.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.anti_shiny_pokemon_encounter.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.anti_shiny_pokemon_encounter.ping_id}>"
                discord_message(
                    webhook_url=context.config.discord.anti_shiny_pokemon_encounter.webhook_url,
                    content=f"Encountered an anti-shiny 💀 {pokemon.species_name_for_stats} 💀!\n{discord_ping}",
                    embed=True,
                    embed_title="Anti-Shiny encountered!",
                    embed_description=f"{pokemon.nature.name} {pokemon.species_name_for_stats} (Lv. {pokemon.level:,}) at {pokemon.location_met}!",
                    embed_fields={
                        "Shiny Value": f"{pokemon.shiny_value:,}",
                        f"IVs ({pokemon.ivs.sum()})": iv_field(),
                        "Held item": pokemon.held_item.name if pokemon.held_item else "None",
                        f"{pokemon.species_name_for_stats} Encounters": f"{stats['pokemon'][pokemon.species_name_for_stats].get('encounters', 0):,} ({stats['pokemon'][pokemon.species_name_for_stats].get('shiny_encounters', 0):,}✨)",
                        f"{pokemon.species_name_for_stats} Phase Encounters": f"{stats['pokemon'][pokemon.species_name_for_stats].get('phase_encounters', 0):,}",
                    }
                    | phase_summary(),
                    embed_thumbnail=get_sprites_path()
                    / "pokemon"
                    / "anti-shiny"
                    / f"{make_string_safe_for_file_name(pokemon.species_name_for_stats)}.png",
                    embed_color="000000",
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord Pokémon matching custom filter encountered
            if context.config.discord.custom_filter_pokemon_encounter.enable and isinstance(custom_filter_result, str):
                # Discord pings
                discord_ping = ""
                match context.config.discord.custom_filter_pokemon_encounter.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.custom_filter_pokemon_encounter.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.custom_filter_pokemon_encounter.ping_id}>"

                discord_message(
                    webhook_url=context.config.discord.custom_filter_pokemon_encounter.webhook_url,
                    content=f"Encountered a {pokemon.species_name_for_stats} matching custom filter: `{custom_filter_result}`!\n{discord_ping}",
                    embed=True,
                    embed_title="Encountered Pokémon matching custom catch filter!",
                    embed_description=f"{pokemon.nature.name} {pokemon.species_name_for_stats} (Lv. {pokemon.level:,}) at {pokemon.location_met}!\nMatching custom filter **{custom_filter_result}**",
                    embed_fields={
                        "Shiny Value": f"{pokemon.shiny_value:,}",
                        f"IVs ({pokemon.ivs.sum()})": iv_field(),
                        "Held item": pokemon.held_item.name if pokemon.held_item else "None",
                        f"{pokemon.species_name_for_stats} Encounters": f"{stats['pokemon'][pokemon.species_name_for_stats].get('encounters', 0):,} ({stats['pokemon'][pokemon.species_name_for_stats].get('shiny_encounters', 0):,}✨)",
                        f"{pokemon.species_name_for_stats} Phase Encounters": f"{stats['pokemon'][pokemon.species_name_for_stats].get('phase_encounters', 0):,}",
                    }
                    | phase_summary(),
                    embed_thumbnail=get_sprites_path()
                    / "pokemon"
                    / "normal"
                    / f"{make_string_safe_for_file_name(pokemon.species_name_for_stats)}.png",
                    embed_color="6a89cc",
                    embed_image=gif_path,
                )
        except Exception:
            console.print_exception(show_locals=True)

        try:
            # Discord TCG cards
            if context.config.discord.tcg_cards.enable and tcg_path:
                # Discord pings
                discord_ping = ""
                match context.config.discord.tcg_cards.ping_mode:
                    case "role":
                        discord_ping = f"📢 <@&{context.config.discord.tcg_cards.ping_id}>"
                    case "user":
                        discord_ping = f"📢 <@{context.config.discord.tcg_cards.ping_id}>"

                discord_message(
                    webhook_url=context.config.discord.tcg_cards.webhook_url,
                    content=discord_ping,
                    image=tcg_path,
                )
        except Exception:
            console.print_exception(show_locals=True)

    except Exception:
        console.print_exception(show_locals=True)

    try:
        # Post the most recent OBS stream screenshot to Discord
        # (screenshot is taken in stats.py before phase resets)
        if context.config.obs.discord_webhook_url and pokemon.is_shiny:

            def OBSDiscordScreenshot():
                time.sleep(3)  # Give the screenshot some time to save to disk
                images = glob.glob(f"{context.config.obs.replay_dir}*.png")
                image = max(images, key=os.path.getctime)
                discord_message(webhook_url=context.config.obs.discord_webhook_url, image=Path(image))

            # Run in a thread to not hold up other hooks
            Thread(target=OBSDiscordScreenshot).start()
    except Exception:
        console.print_exception(show_locals=True)

    try:
        # Save OBS replay buffer n frames after encountering a shiny
        if context.config.obs.replay_buffer and pokemon.is_shiny:

            def OBSReplayBuffer():
                from modules.obs import obs_hot_key

                time.sleep(context.config.obs.replay_buffer_delay)
                obs_hot_key("OBS_KEY_F12", pressCtrl=True)

            # Run in a thread to not hold up other hooks
            Thread(target=OBSReplayBuffer).start()
    except Exception:
        console.print_exception(show_locals=True)
