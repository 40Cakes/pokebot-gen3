import os
import glob
import time
import random
from typing import NoReturn
from threading import Thread
from modules.Config import config
from modules.Console import console
from modules.Discord import DiscordMessage
from modules.Gui import GetROM


def CustomHooks(hook) -> NoReturn:
    """
    This function is called every time an encounter is logged, but before phase stats are reset (if shiny)
    this file is useful for custom webhooks or logging to external databases if you understand Python

    Note: this function runs in a thread and will not hold up the bot if you need to run any slow hooks
    """
    try:
        # Deep copy of Pokémon and stats dictionaries when the thread was called to avoid main thread overwriting vars
        pokemon = hook[0]
        stats = hook[1]
        block_list = hook[2]

        ### Your custom code goes here ###

        # Discord messages
        from modules.Stats import GetEncounterRate

        def IVField() -> str:
            # Formatted IV table
            if config["discord"]["iv_format"] == "formatted":
                iv_field = (
                    "```"
                    "╔═══╤═══╤═══╤═══╤═══╤═══╗\n"
                    "║HP │ATK│DEF│SPA│SPD│SPE║\n"
                    "╠═══╪═══╪═══╪═══╪═══╪═══╣\n"
                    f"║{pokemon['IVs']['hp']:^3}│"
                    f"{pokemon['IVs']['attack']:^3}│"
                    f"{pokemon['IVs']['defense']:^3}│"
                    f"{pokemon['IVs']['spAttack']:^3}│"
                    f"{pokemon['IVs']['spDefense']:^3}│"
                    f"{pokemon['IVs']['speed']:^3}║\n"
                    "╚═══╧═══╧═══╧═══╧═══╧═══╝"
                    "```"
                )
            else:
                # Basic IV table
                iv_field = (
                    f"HP: {pokemon['IVs']['hp']} | "
                    f"ATK: {pokemon['IVs']['attack']} | "
                    f"DEF: {pokemon['IVs']['defense']} | "
                    f"SPATK: {pokemon['IVs']['spAttack']} | "
                    f"SPDEF: {pokemon['IVs']['spDefense']} | "
                    f"SPE: {pokemon['IVs']['speed']}"
                )
            return iv_field

        def PhaseSummary() -> dict:
            return {
                f"{pokemon['name']} Phase Encounters": f"{stats['pokemon'][pokemon['name']].get('phase_encounters', 0):,}",
                "Phase Encounters": f"{stats['totals'].get('phase_encounters', 0):,} ({GetEncounterRate():,}/h)",
                "Phase IV Sum Records": (
                    f":arrow_up: `{stats['totals'].get('phase_highest_iv_sum', 0):,}` IV {stats['totals'].get('phase_highest_iv_sum_pokemon', 'N/A')}\n"
                    f":arrow_down: `{stats['totals'].get('phase_lowest_iv_sum', 0):,}` IV {stats['totals'].get('phase_lowest_iv_sum_pokemon', 'N/A')}"
                ),
                "Phase SV Records": (
                    f":arrow_up: `{stats['totals'].get('phase_highest_sv', 0):,}` SV {stats['totals'].get('phase_highest_sv_pokemon', 'N/A')}\n"
                    f":arrow_down: `{stats['totals'].get('phase_lowest_sv', 0):,}` SV ✨ {stats['totals'].get('phase_lowest_sv_pokemon', 'N/A')} ✨"
                ),
                "Phase Same Pokémon Streak": (
                    f"{stats['totals'].get('phase_streak', 0):,} {stats['totals'].get('phase_streak_pokemon', 'N/A')} were encountered in a row!"
                ),
                "Total Encounters": (
                    f"{stats['totals'].get('encounters', 0):,} ({stats['totals'].get('shiny_encounters', 0):,}✨)"
                ),
            }

        try:
            # Discord shiny Pokémon encountered
            if config["discord"]["shiny_pokemon_encounter"]["enable"] and pokemon["shiny"]:
                # Discord pings
                discord_ping = ""
                match config["discord"]["shiny_pokemon_encounter"]["ping_mode"]:
                    case "role":
                        discord_ping = f"📢 <@&{config['discord']['shiny_pokemon_encounter']['ping_id']}>"
                    case "user":
                        discord_ping = f"📢 <@{config['discord']['shiny_pokemon_encounter']['ping_id']}>"

                block = "\n❌Skipping catching shiny (on catch block list)!" if pokemon["name"] in block_list else ""

                DiscordMessage(
                    webhook_url=config["discord"]["shiny_pokemon_encounter"].get("webhook_url", None),
                    content=f"Encountered a shiny ✨ {pokemon['name']} ✨! {block}\n{discord_ping}",
                    embed=True,
                    embed_title="Shiny encountered!",
                    embed_description=(
                        f"{pokemon['nature']} {pokemon['name']} (Lv. {pokemon['level']:,}) at {pokemon['metLocation']}!"
                    ),
                    embed_fields={
                        "Shiny Value": f"{pokemon['shinyValue']:,}",
                        "IVs": IVField(),
                        f"{pokemon['name']} Encounters": f"{stats['pokemon'][pokemon['name']].get('encounters', 0):,} ({stats['pokemon'][pokemon['name']].get('shiny_encounters', 0):,}✨)",
                        f"{pokemon['name']} Phase Encounters": f"{stats['pokemon'][pokemon['name']].get('phase_encounters', 0):,}",
                    }
                    | PhaseSummary(),
                    embed_thumbnail=f"./sprites/pokemon/shiny/{pokemon['name']}.png",
                    embed_footer=f"PokéBot ID: {config['discord']['bot_id']} | {GetROM().game_name}",
                    embed_color="ffd242",
                )
        except:
            console.print_exception(show_locals=True)

        try:
            # Discord Pokémon encounter milestones
            if (
                config["discord"]["pokemon_encounter_milestones"]["enable"]
                and stats["pokemon"][pokemon["name"]].get("encounters", -1)
                % config["discord"]["pokemon_encounter_milestones"].get("interval", 0)
                == 0
            ):
                # Discord pings
                discord_ping = ""
                match config["discord"]["pokemon_encounter_milestones"]["ping_mode"]:
                    case "role":
                        discord_ping = f"📢 <@&{config['discord']['pokemon_encounter_milestones']['ping_id']}>"
                    case "user":
                        discord_ping = f"📢 <@{config['discord']['pokemon_encounter_milestones']['ping_id']}>"
                DiscordMessage(
                    webhook_url=config["discord"]["pokemon_encounter_milestones"].get("webhook_url", None),
                    content=f"🎉 New milestone achieved!\n{discord_ping}",
                    embed=True,
                    embed_description=f"{stats['pokemon'][pokemon['name']].get('encounters', 0):,} {pokemon['name']} encounters!",
                    embed_thumbnail=f"./sprites/pokemon/normal/{pokemon['name']}.png",
                    embed_footer=f"PokéBot ID: {config['discord']['bot_id']} | {GetROM().game_name}",
                    embed_color="50C878",
                )
        except:
            console.print_exception(show_locals=True)

        try:
            # Discord shiny Pokémon encounter milestones
            if (
                config["discord"]["shiny_pokemon_encounter_milestones"]["enable"]
                and pokemon["shiny"]
                and stats["pokemon"][pokemon["name"]].get("shiny_encounters", -1)
                % config["discord"]["shiny_pokemon_encounter_milestones"].get("interval", 0)
                == 0
            ):
                # Discord pings
                discord_ping = ""
                match config["discord"]["shiny_pokemon_encounter_milestones"]["ping_mode"]:
                    case "role":
                        discord_ping = f"📢 <@&{config['discord']['shiny_pokemon_encounter_milestones']['ping_id']}>"
                    case "user":
                        discord_ping = f"📢 <@{config['discord']['shiny_pokemon_encounter_milestones']['ping_id']}>"
                DiscordMessage(
                    webhook_url=config["discord"]["shiny_pokemon_encounter_milestones"].get("webhook_url", None),
                    content=f"🎉 New milestone achieved!\n{discord_ping}",
                    embed=True,
                    embed_description=f"{stats['pokemon'][pokemon['name']].get('shiny_encounters', 0):,} shiny ✨ {pokemon['name']} ✨ encounters!",
                    embed_thumbnail=f"./sprites/pokemon/shiny/{pokemon['name']}.png",
                    embed_footer=f"PokéBot ID: {config['discord']['bot_id']} | {GetROM().game_name}",
                    embed_color="ffd242",
                )
        except:
            console.print_exception(show_locals=True)

        try:
            # Discord total encounter milestones
            if (
                config["discord"]["total_encounter_milestones"]["enable"]
                and stats["totals"].get("encounters", -1)
                % config["discord"]["total_encounter_milestones"].get("interval", 0)
                == 0
            ):
                # Discord pings
                discord_ping = ""
                match config["discord"]["total_encounter_milestones"]["ping_mode"]:
                    case "role":
                        discord_ping = f"📢 <@&{config['discord']['total_encounter_milestones']['ping_id']}>"
                    case "user":
                        discord_ping = f"📢 <@{config['discord']['total_encounter_milestones']['ping_id']}>"

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

                DiscordMessage(
                    webhook_url=config["discord"]["total_encounter_milestones"].get("webhook_url", None),
                    content=f"🎉 New milestone achieved!\n{discord_ping}",
                    embed=True,
                    embed_description=f"{stats['totals'].get('encounters', 0):,} total encounters!",
                    embed_thumbnail=f"./sprites/items/{embed_thumbnail}.png",
                    embed_footer=f"PokéBot ID: {config['discord']['bot_id']} | {GetROM().game_name}",
                    embed_color="50C878",
                )
        except:
            console.print_exception(show_locals=True)

        try:
            # Discord phase encounter notifications
            if (
                config["discord"]["phase_summary"]["enable"]
                and not pokemon["shiny"]
                and (
                    stats["totals"].get("phase_encounters", -1)
                    == config["discord"]["phase_summary"].get("first_interval", 0)
                    or (
                        stats["totals"].get("phase_encounters", -1)
                        > config["discord"]["phase_summary"].get("first_interval", 0)
                        and stats["totals"].get("phase_encounters", -1)
                        % config["discord"]["phase_summary"].get("consequent_interval", 0)
                        == 0
                    )
                )
            ):
                # Discord pings
                discord_ping = ""
                match config["discord"]["phase_summary"]["ping_mode"]:
                    case "role":
                        discord_ping = f"📢 <@&{config['discord']['phase_summary']['ping_id']}>"
                    case "user":
                        discord_ping = f"📢 <@{config['discord']['phase_summary']['ping_id']}>"
                DiscordMessage(
                    webhook_url=config["discord"]["phase_summary"].get("webhook_url", None),
                    content=f"💀 The current phase has reached {stats['totals'].get('phase_encounters', 0):,} encounters!\n{discord_ping}",
                    embed=True,
                    embed_fields=PhaseSummary(),
                    embed_footer=f"PokéBot ID: {config['discord']['bot_id']} | {GetROM().game_name}",
                    embed_color="D70040",
                )
        except:
            console.print_exception(show_locals=True)

        try:
            # Discord anti-shiny Pokémon encountered
            if config["discord"]["anti_shiny_pokemon_encounter"]["enable"] and (
                65528 <= pokemon["shinyValue"] <= 65535
            ):
                # Discord pings
                discord_ping = ""
                match config["discord"]["anti_shiny_pokemon_encounter"]["ping_mode"]:
                    case "role":
                        discord_ping = f"📢 <@&{config['discord']['anti_shiny_pokemon_encounter']['ping_id']}>"
                    case "user":
                        discord_ping = f"📢 <@{config['discord']['anti_shiny_pokemon_encounter']['ping_id']}>"
                DiscordMessage(
                    webhook_url=config["discord"]["anti_shiny_pokemon_encounter"].get("webhook_url", None),
                    content=f"Encountered an anti-shiny 💀 {pokemon['name']} 💀!\n{discord_ping}",
                    embed=True,
                    embed_title="Anti-Shiny encountered!",
                    embed_description=f"{pokemon['nature']} {pokemon['name']} (Lv. {pokemon['level']:,}) at {pokemon['metLocation']}!",
                    embed_fields={
                        "Shiny Value": f"{pokemon['shinyValue']:,}",
                        "IVs": IVField(),
                        f"{pokemon['name']} Encounters": f"{stats['pokemon'][pokemon['name']].get('encounters', 0):,} ({stats['pokemon'][pokemon['name']].get('shiny_encounters', 0):,}✨)",
                        f"{pokemon['name']} Phase Encounters": f"{stats['pokemon'][pokemon['name']].get('phase_encounters', 0):,}",
                    }
                    | PhaseSummary(),
                    embed_thumbnail=f"./sprites/pokemon/anti-shiny/{pokemon['name']}.png",
                    embed_footer=f"PokéBot ID: {config['discord']['bot_id']} | {GetROM().game_name}",
                    embed_color="000000",
                )
        except:
            console.print_exception(show_locals=True)

    except:
        console.print_exception(show_locals=True)

    try:
        # Post the most recent OBS stream screenshot to Discord
        # (screenshot is taken in Stats.py before phase resets)
        if config["obs"]["discord_webhook_url"] and pokemon["shiny"]:

            def OBSDiscordScreenshot():
                time.sleep(3)  # Give the screenshot some time to save to disk
                images = glob.glob(f"{config['obs']['replay_dir']}*.png")
                image = max(images, key=os.path.getctime)
                DiscordMessage(webhook_url=config["obs"].get("discord_webhook_url", None), image=image)

            # Run in a thread to not hold up other hooks
            Thread(target=OBSDiscordScreenshot).start()
    except:
        console.print_exception(show_locals=True)

    try:
        # Save OBS replay buffer n frames after encountering a shiny
        if config["obs"]["replay_buffer"] and pokemon["shiny"]:

            def OBSReplayBuffer():
                from modules.OBS import OBSHotKey

                time.sleep(config["obs"].get("replay_buffer_delay", 0))
                OBSHotKey("OBS_KEY_F12", pressCtrl=True)

            # Run in a thread to not hold up other hooks
            Thread(target=OBSReplayBuffer).start()
    except:
        console.print_exception(show_locals=True)
