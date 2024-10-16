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
from modules.encounter import EncounterValue
from modules.plugin_interface import BotPlugin
from modules.runtime import get_sprites_path
from modules.sprites import get_shiny_sprite, get_regular_sprite, get_anti_shiny_sprite
from modules.stats import EncounterSummary

if TYPE_CHECKING:
    from modules.config.schemas_v1 import DiscordWebhook
    from modules.encounter import EncounterInfo
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


def pokemon_label(pokemon: "Pokemon") -> str:
    return f"{pokemon.nature.name} {pokemon.species_name_for_stats} (Lv. {pokemon.level:,}) at {pokemon.location_met}!"


def pokemon_fields(pokemon: "Pokemon", species_stats: "EncounterSummary", short: bool = False) -> dict[str, str]:
    result = {"Shiny Value": f"{pokemon.shiny_value:,}"}
    if not short:
        result[f"IVs ({pokemon.ivs.sum()})"] = iv_table(pokemon)
        result["Held item"] = pokemon.held_item.name if pokemon.held_item else "None"
    result[f"{pokemon.species_name_for_stats} Encounters"] = (
        f"{species_stats.total_encounters:,} ({species_stats.shiny_encounters:,}✨)"
    )
    result[f"{pokemon.species_name_for_stats} Phase Encounters"] = f"{species_stats.phase_encounters:,}"
    return result


def phase_summary_fields(pokemon: "Pokemon", phase: "ShinyPhase | None") -> dict[str, str]:
    if phase is None:
        return {}

    if pokemon.is_shiny:
        lowest_sv = f"`{pokemon.shiny_value:,}` SV (✨{pokemon.species_name_for_stats}✨)"
    elif phase.lowest_sv is not None:
        lowest_sv = f"`{phase.lowest_sv.value:,}` SV ({phase.lowest_sv.species_name})"
    else:
        lowest_sv = None

    result = {"Phase Encounters": f"{phase.encounters:,} ({context.stats.encounter_rate:,}/h)"}
    if phase.highest_iv_sum is not None and phase.lowest_iv_sum is not None:
        result["Phase IV Sum Records"] = (
            f":arrow_up: `{phase.highest_iv_sum.value:,}` IV ({phase.highest_iv_sum.species_name})\n"
            f":arrow_down: `{phase.lowest_iv_sum.value:,}` IV ({phase.lowest_iv_sum.species_name})"
        )
    if phase.highest_sv is not None and lowest_sv is not None:
        result["Phase SV Records"] = (
            f":arrow_up: `{phase.highest_sv.value:,}` SV ({phase.highest_sv.species_name})\n"
            f":arrow_down: {lowest_sv}"
        )

    if phase.longest_streak is not None:
        result["Phase Same Pokémon Streak"] = (
            f"{phase.longest_streak.value:,} {phase.longest_streak.species_name} were encountered in a row!"
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

    def on_logging_encounter(self, encounter: "EncounterInfo") -> Generator | None:
        global_stats = context.stats.get_global_stats()
        opponent = encounter.pokemon
        species_stats = global_stats.species(opponent)
        shiny_phase = context.stats.current_shiny_phase

        already_reported_pokemon = False

        # Discord shiny Pokémon encountered
        if (
            not already_reported_pokemon
            and context.config.discord.shiny_pokemon_encounter.enable
            and encounter.value is EncounterValue.Shiny
        ):
            already_reported_pokemon = True
            send_discord_message(
                webhook_config=context.config.discord.shiny_pokemon_encounter,
                content=f"{encounter.type.verb.title()} a shiny ✨ {opponent.species_name_for_stats} ✨!",
                embed=DiscordMessageEmbed(
                    title=f"Shiny {encounter.type.verb}!",
                    description=pokemon_label(opponent),
                    fields=pokemon_fields(opponent, species_stats) | phase_summary_fields(opponent, shiny_phase),
                    thumbnail=get_shiny_sprite(opponent),
                    colour="ffd242",
                    image=encounter.gif_path,
                ),
            )

        # Discord shiny on block list encountered
        if (
            not already_reported_pokemon
            and context.config.discord.blocked_shiny_encounter.enable
            and encounter.value is EncounterValue.ShinyOnBlockList
        ):
            already_reported_pokemon = True
            send_discord_message(
                webhook_config=context.config.discord.blocked_shiny_encounter,
                content=f"{encounter.type.verb.title()} a shiny ✨ {opponent.species_name_for_stats} ✨.\n❌ But this species is on the block list, so it will not be caught. ❌",
                embed=DiscordMessageEmbed(
                    title=f"(Blocked) Shiny {encounter.type.verb}",
                    description=pokemon_label(opponent),
                    fields=pokemon_fields(opponent, species_stats, short=True)
                    | phase_summary_fields(opponent, shiny_phase),
                    thumbnail=get_shiny_sprite(opponent),
                    colour="808080",
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
            and (
                phase_encounters == context.config.discord.phase_summary.first_interval
                or (
                    phase_encounters > context.config.discord.phase_summary.first_interval
                    and phase_encounters % context.config.discord.phase_summary.consequent_interval == 0
                )
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
                content=f"{encounter.type.verb.title()} an anti-shiny 💀 {opponent.species_name_for_stats} 💀!",
                embed=DiscordMessageEmbed(
                    title=f"Anti-Shiny {encounter.type.verb}!",
                    description=pokemon_label(opponent),
                    fields=pokemon_fields(opponent, species_stats) | phase_summary_fields(opponent, shiny_phase),
                    thumbnail=get_anti_shiny_sprite(opponent),
                    colour="000000",
                ),
            )

        # Discord Pokémon matching custom filter encountered
        if (
            not already_reported_pokemon
            and context.config.discord.custom_filter_pokemon_encounter.enable
            and encounter.value is EncounterValue.CustomFilterMatch
        ):
            already_reported_pokemon = True
            send_discord_message(
                webhook_config=context.config.discord.custom_filter_pokemon_encounter,
                content=f"{encounter.type.verb.title()} a {opponent.species_name_for_stats} matching custom filter: `{encounter.catch_filters_result}`!",
                embed=DiscordMessageEmbed(
                    description=pokemon_label(opponent),
                    fields=pokemon_fields(opponent, species_stats) | phase_summary_fields(opponent, shiny_phase),
                    thumbnail=get_regular_sprite(opponent),
                    colour="6a89cc",
                    image=encounter.gif_path,
                ),
            )

        # Discord TCG cards
        if (
            context.config.discord.tcg_cards.enable
            and context.config.logging.tcg_cards
            and encounter.tcg_card_path is not None
        ):
            send_discord_message(
                webhook_config=context.config.discord.tcg_cards,
                content="",
                image=encounter.tcg_card_path,
            )

        return None
