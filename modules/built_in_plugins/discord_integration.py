import random
from threading import Thread
from typing import TYPE_CHECKING, Generator

from modules.context import context
from modules.discord import (
    discord_message_thread,
    DiscordMessage,
    DiscordMessageEmbed,
    discord_send,
    discord_rich_presence_loop,
)
from modules.plugin_interface import BotPlugin
from modules.runtime import get_sprites_path
from modules.sprites import get_shiny_sprite, get_regular_sprite, get_anti_shiny_sprite

if TYPE_CHECKING:
    from modules.config.schemas_v1 import DiscordWebhook
    from modules.encounter import ActiveWildEncounter
    from modules.pokemon import Pokemon
    from modules.profiles import Profile


def iv_table(pokemon: "Pokemon") -> str:
    if context.config.discord.iv_format == "formatted":
        return (
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
        return (
            f"HP: {pokemon.ivs.hp} | "
            f"ATK: {pokemon.ivs.attack} | "
            f"DEF: {pokemon.ivs.defence} | "
            f"SPATK: {pokemon.ivs.special_attack} | "
            f"SPDEF: {pokemon.ivs.special_defence} | "
            f"SPE: {pokemon.ivs.speed}"
        )


def phase_summary_fields(pokemon: "Pokemon", phase: "ShinyPhase | None") -> dict[str, str]:
    if phase is None:
        return {}

    if pokemon.is_shiny:
        lowest_sv = f"`{pokemon.shiny_value:,}` SV (✨{pokemon.species.name}✨)"
    elif phase.lowest_sv is not None:
        lowest_sv = f"`{phase.lowest_sv:,}` SV ({phase.lowest_sv_species.name})"
    else:
        lowest_sv = None

    result = {"Phase Encounters": f"{phase.encounters:,} ({context.stats.encounter_rate:,}/h)"}
    if phase.highest_iv_sum is not None and phase.lowest_iv_sum is not None:
        result["Phase IV Sum Records"] = (
            f":arrow_up: `{phase.highest_iv_sum:,}` IV ({phase.highest_iv_sum_species.name})\n"
            f":arrow_down: `{phase.lowest_iv_sum:,}` IV ({phase.lowest_iv_sum_species.name})"
        )
    if phase.highest_sv is not None and lowest_sv is not None:
        result["Phase SV Records"] = (
            f":arrow_up: `{phase.highest_sv:,}` SV ({phase.highest_sv_species.name})\n" f":arrow_down: {lowest_sv}"
        )

    if phase.longest_streak is not None and phase.longest_streak_species is not None:
        result["Phase Same Pokémon Streak"] = (
            f"{phase.longest_streak:,} {phase.longest_streak_species.name} were encountered in a row!"
        )

    if phase.snapshot_total_encounters is not None and phase.snapshot_total_shiny_encounters is not None:
        result["Total Encounters"] = (
            f"{phase.snapshot_total_encounters:,} ({phase.snapshot_total_shiny_encounters:,}✨)"
        )

    return result


def send_discord_message(webhook_config: "DiscordWebhook", content: str, **kwargs) -> None:
    if webhook_config.ping_mode == "role":
        ping = f"\n📢 <@&{webhook_config.ping_id}>"
    elif webhook_config.ping_mode == "user":
        ping = f"\n📢 <@{webhook_config.ping_id}>"
    else:
        ping = ""

    if content == "":
        ping = ping.strip()

    discord_send(DiscordMessage(webhook_url=webhook_config.webhook_url, content=f"{content}{ping}", **kwargs))


class DiscordPlugin(BotPlugin):
    def __init__(self):
        self._thread: Thread

    def on_profile_loaded(self, profile: "Profile") -> None:
        self._thread = Thread(target=discord_message_thread).start()

        if context.config.discord.rich_presence:
            Thread(target=discord_rich_presence_loop, daemon=True).start()

    def on_wild_encounter_visible(self, wild_encounter: "ActiveWildEncounter") -> Generator | None:
        global_stats = context.stats.get_global_stats()
        opponent = wild_encounter.pokemon
        species_stats = global_stats.species(opponent.species)
        if opponent.is_shiny:
            shiny_phase = context.stats.get_shiny_phase_by_shiny(opponent)
        else:
            shiny_phase = context.stats.current_shiny_phase

        # Discord shiny Pokémon encountered
        if context.config.discord.shiny_pokemon_encounter.enable and opponent.is_shiny:
            block = (
                "\n❌Skipping catching shiny (on catch block list)!"
                if opponent.species_name_for_stats in context.config.catch_block
                or opponent.species.name in context.config.catch_block
                else ""
            )

            send_discord_message(
                webhook_config=context.config.discord.shiny_pokemon_encounter,
                content=f"Encountered a shiny ✨ {opponent.species_name_for_stats} ✨! {block}",
                embed=DiscordMessageEmbed(
                    title="Shiny encountered!",
                    description=f"{opponent.nature.name} {opponent.species_name_for_stats} (Lv. {opponent.level:,}) at {opponent.location_met}!",
                    fields={
                        "Shiny Value": f"{opponent.shiny_value:,}",
                        f"IVs ({opponent.ivs.sum()})": iv_table(opponent),
                        "Held item": opponent.held_item.name if opponent.held_item else "None",
                        f"{opponent.species_name_for_stats} Encounters": f"{species_stats.total_encounters:,} ({species_stats.shiny_encounters:,}✨)",
                        f"{opponent.species_name_for_stats} Phase Encounters": f"{species_stats.phase_encounters:,}",
                    }
                    | phase_summary_fields(opponent, shiny_phase),
                    thumbnail=get_shiny_sprite(opponent),
                    colour="ffd242",
                    image=wild_encounter.gif_path,
                ),
            )

        # Discord Pokémon encounter milestones
        if (
            context.config.discord.pokemon_encounter_milestones.enable
            and species_stats.total_encounters % context.config.discord.pokemon_encounter_milestones.interval == 0
        ):
            send_discord_message(
                webhook_config=context.config.discord.pokemon_encounter_milestones,
                content="🎉 New milestone achieved!",
                embed=DiscordMessageEmbed(
                    description=f"{species_stats.total_encounters:,} {opponent.species_name_for_stats} encounters!",
                    thumbnail=get_regular_sprite(opponent),
                    colour="50C878",
                ),
            )

        # Discord shiny Pokémon encounter milestones
        if (
            context.config.discord.shiny_pokemon_encounter_milestones.enable
            and opponent.is_shiny
            and species_stats.shiny_encounters % context.config.discord.shiny_pokemon_encounter_milestones.interval == 0
        ):
            send_discord_message(
                webhook_config=context.config.discord.shiny_pokemon_encounter_milestones,
                content="🎉 New milestone achieved!",
                embed=DiscordMessageEmbed(
                    description=f"{species_stats.shiny_encounters:,} shiny ✨ {opponent.species_name_for_stats} ✨ encounters!",
                    thumbnail=get_shiny_sprite(opponent),
                    colour="ffd242",
                ),
            )

        # Discord total encounter milestones
        if (
            context.config.discord.total_encounter_milestones.enable
            and global_stats.totals.total_encounters % context.config.discord.total_encounter_milestones.interval == 0
        ):
            embed_thumbnail = random.choice(
                [
                    "Dive Ball.png",
                    "Great Ball.png",
                    "Light Ball.png",
                    "Luxury Ball.png",
                    "Master Ball.png",
                    "Nest Ball.png",
                    "Net Ball.png",
                    "Poké Ball.png",
                    "Premier Ball.png",
                    "Repeat Ball.png",
                    "Safari Ball.png",
                    "Smoke Ball.png",
                    "Timer Ball.png",
                    "Ultra Ball.png",
                ]
            )

            send_discord_message(
                webhook_config=context.config.discord.total_encounter_milestones,
                content="🎉 New milestone achieved!",
                embed=DiscordMessageEmbed(
                    description=f"{global_stats.totals.total_encounters:,} total encounters!",
                    thumbnail=get_sprites_path() / "items" / embed_thumbnail,
                    colour="50c878",
                ),
            )

        # Discord phase encounter notifications
        phase_encounters = global_stats.totals.phase_encounters
        if (
            context.config.discord.phase_summary.enable
            and not opponent.is_shiny
            and phase_encounters == context.config.discord.phase_summary.first_interval
            or (
                phase_encounters > context.config.discord.phase_summary.first_interval
                and phase_encounters % context.config.discord.phase_summary.consequent_interval == 0
            )
        ):
            send_discord_message(
                webhook_config=context.config.discord.phase_summary,
                content=f"💀 The current phase has reached {phase_encounters:,} encounters!",
                embed=DiscordMessageEmbed(fields=phase_summary_fields(opponent, shiny_phase), colour="d70040"),
            )

        # Discord anti-shiny Pokémon encountered
        if context.config.discord.anti_shiny_pokemon_encounter.enable and opponent.is_anti_shiny:
            send_discord_message(
                webhook_config=context.config.discord.anti_shiny_pokemon_encounter,
                content=f"Encountered an anti-shiny 💀 {opponent.species_name_for_stats} 💀!",
                embed=DiscordMessageEmbed(
                    title="Anti-Shiny encountered!",
                    description=f"{opponent.nature.name} {opponent.species_name_for_stats} (Lv. {opponent.level:,}) at {opponent.location_met}!",
                    fields={
                        "Shiny Value": f"{opponent.shiny_value:,}",
                        f"IVs ({opponent.ivs.sum()})": iv_table(opponent),
                        "Held item": opponent.held_item.name if opponent.held_item else "None",
                        f"{opponent.species_name_for_stats} Encounters": f"{species_stats.total_encounters:,} ({species_stats.shiny_encounters:,}✨)",
                        f"{opponent.species_name_for_stats} Phase Encounters": f"{species_stats.phase_encounters:,}",
                    }
                    | phase_summary_fields(opponent, shiny_phase),
                    thumbnail=get_anti_shiny_sprite(opponent),
                    colour="000000",
                ),
            )

        # Discord Pokémon matching custom filter encountered
        if context.config.discord.custom_filter_pokemon_encounter.enable and isinstance(
            wild_encounter.catch_filters_result, str
        ):
            send_discord_message(
                webhook_config=context.config.discord.custom_filter_pokemon_encounter,
                content=f"Encountered a {opponent.species_name_for_stats} matching custom filter: `{wild_encounter.catch_filters_result}`!",
                description=f"{opponent.nature.name} {opponent.species_name_for_stats} (Lv. {opponent.level:,}) at {opponent.location_met}!",
                fields={
                    "Shiny Value": f"{opponent.shiny_value:,}",
                    f"IVs ({opponent.ivs.sum()})": iv_table(opponent),
                    "Held item": opponent.held_item.name if opponent.held_item else "None",
                    f"{opponent.species_name_for_stats} Encounters": f"{species_stats.total_encounters:,} ({species_stats.shiny_encounters:,}✨)",
                    f"{opponent.species_name_for_stats} Phase Encounters": f"{species_stats.phase_encounters:,}",
                }
                | phase_summary_fields(opponent, shiny_phase),
                thumbnail=get_regular_sprite(opponent),
                colour="6a89cc",
                image=wild_encounter.gif_path,
            )

        # Discord TCG cards
        if (
            context.config.discord.tcg_cards.enable
            and context.config.logging.tcg_cards
            and wild_encounter.tcg_card_path is not None
        ):
            send_discord_message(
                webhook_config=context.config.discord.tcg_cards,
                content="",
                image=wild_encounter.tcg_card_path,
            )

        return None
