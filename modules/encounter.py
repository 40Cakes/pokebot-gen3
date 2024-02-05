import time
from enum import Enum, auto
from pathlib import Path
from threading import Thread

from modules.console import console
from modules.context import context
from modules.discord import discord_message
from modules.files import save_pk3
from modules.gui.desktop_notification import desktop_notification
from modules.modes import BattleAction
from modules.pokemon import Pokemon, get_opponent
from modules.roamer import get_roamer
from modules.runtime import get_sprites_path


def send_discord_encounter_gif(gif_path: Path, wait: int = 0) -> None:
    """
    Intended to be called in a thread, use the wait parameter to post the GIF after the embed webhook

    :param gif_path: Path to GIF file
    :param wait: n seconds to wait before posting
    """
    time.sleep(wait)
    discord_message(image=gif_path)


def wild_encounter_gif(post_to_discord: bool = False) -> None:
    """
    Generates a GIF from frames 220-260 after wild encounter is logged to capture the shiny sparkles
    TODO add GIFs for other modes if applicable
    """
    if get_opponent() is not None and get_opponent().is_shiny:  # Disables GIF generation for daycare/gift modes
        gif = context.emulator.generate_gif(start_frame=220, duration=37)

        if post_to_discord:
            Thread(target=send_discord_encounter_gif, args=(gif, 3)).start()


def _default_battle_action() -> BattleAction:
    if context.config.battle.battle:
        return BattleAction.Fight
    else:
        return BattleAction.RunAway


def run_custom_catch_filters(pokemon: Pokemon) -> str | bool:
    from modules.stats import total_stats

    result = total_stats.custom_catch_filters(pokemon)
    if result is True:
        result = "Matched a custom catch filter"
    return result


class EncounterValue(Enum):
    Shiny = auto()
    ShinyOnBlockList = auto()
    Roamer = auto()
    RoamerOnBlockList = auto()
    CustomFilterMatch = auto()
    NotOfInterest = auto()

    @property
    def is_of_interest(self):
        return self in (EncounterValue.Shiny, EncounterValue.Roamer, EncounterValue.CustomFilterMatch)


def judge_encounter(pokemon: Pokemon) -> EncounterValue:
    """
    Checks whether an encountered Pokémon matches any of the criteria that makes it
    eligible for catching (is shiny, matches custom catch filter, ...)

    :param pokemon: The Pokémon that has been encountered.
    :return: The perceived 'value' of the encounter.
    """

    if pokemon.is_shiny:
        context.config.reload_file("catch_block")
        if pokemon.species.name in context.config.catch_block.block_list:
            return EncounterValue.ShinyOnBlockList
        else:
            return EncounterValue.Shiny

    if run_custom_catch_filters(pokemon) is not False:
        return EncounterValue.CustomFilterMatch

    roamer = get_roamer()
    if (
        roamer is not None
        and roamer.personality_value == pokemon.personality_value
        and roamer.species == pokemon.species
    ):
        context.config.reload_file("catch_block")
        if pokemon.species.name in context.config.catch_block.block_list:
            return EncounterValue.RoamerOnBlockList
        else:
            return EncounterValue.Roamer

    return EncounterValue.NotOfInterest


def log_encounter(pokemon: Pokemon, action: BattleAction | None = None) -> None:
    from modules.stats import total_stats

    total_stats.log_encounter(pokemon, context.config.catch_block.block_list, run_custom_catch_filters(pokemon))
    if context.config.logging.save_pk3.all:
        save_pk3(pokemon)

    fun_facts = [
            f"Nature:\xa0{pokemon.nature.name}",
            f"Ability:\xa0{pokemon.ability.name}",
            f"Item:\xa0{pokemon.held_item.name if pokemon.held_item is not None else '-'}",
            f"IV\xa0sum:\xa0{pokemon.ivs.sum()}",
            f"SV:\xa0{pokemon.shiny_value}",
        ]

    species_name = pokemon.species.name
    if pokemon.is_shiny:
        species_name = "Shiny " + species_name
    if pokemon.gender == "male":
        species_name += " ♂"
    elif pokemon.gender == "female":
        species_name += " ♀"
    if pokemon.species.name == "Unown":
        species_name += f" ({pokemon.unown_letter})"
    if pokemon.species.name == "Wurmple":
        fun_facts.append(f"Evo: {pokemon.wurmple_evolution.title()}")

    match action:
        case BattleAction.RunAway:
            message_action = "Will try to catch it."
        case BattleAction.CustomAction:
            message_action = "Switched to manual mode so you can catch it."
        case BattleAction.Fight:
            message_action = "Will fight it."
        case BattleAction.RunAway:
            message_action = "Trying to run away."
        case _:
            message_action = ""

    context.message = f"Encountered {species_name}. {message_action}\n\n{' | '.join(fun_facts)}"


def handle_encounter(
    pokemon: Pokemon, disable_auto_catch: bool = False, disable_auto_battle: bool = False
) -> BattleAction:
    encounter_value = judge_encounter(pokemon)
    match encounter_value:
        case EncounterValue.Shiny:
            console.print(f"[bold yellow]Shiny {pokemon.species.name} found![/]")
            alert = "Shiny found!", f"Found a ✨shiny {pokemon.species.name}✨! 🥳"
            wild_encounter_gif(post_to_discord=context.config.discord.shiny_pokemon_encounter.enable)
            if not context.config.logging.save_pk3.all and context.config.logging.save_pk3.shiny:
                save_pk3(pokemon)
            is_of_interest = True

        case EncounterValue.CustomFilterMatch:
            filter_result = run_custom_catch_filters(pokemon)
            console.print(f"[pink green]Custom filter triggered for {pokemon.species.name}: '{filter_result}'[/]")
            alert = "Custom filter triggered!", f"Found a {pokemon.species.name} that matched one of your filters."
            is_of_interest = True

        case EncounterValue.Roamer:
            console.print(f"[pink yellow]Roaming {pokemon.species.name} found![/]")
            alert = "Roaming Pokemon found!", f"Encountered a roaming {pokemon.species.name}."
            if not context.config.logging.save_pk3.all and context.config.logging.save_pk3.custom:
                save_pk3(pokemon)
            is_of_interest = True

        case EncounterValue.ShinyOnBlockList | EncounterValue.RoamerOnBlockList:
            console.print(f"[bold yellow]{pokemon.species.name} is on the catch block list, skipping encounter...[/]")
            alert = None
            is_of_interest = False

        case EncounterValue.NotOfInterest | _:
            alert = None
            is_of_interest = False

    if alert is not None:
        alert_icon = (
            get_sprites_path()
            / "pokemon"
            / f"{'shiny' if pokemon.is_shiny else 'normal'}"
            / f"{pokemon.species.name}.png"
        )
        desktop_notification(title=alert[0], message=alert[1], icon=alert_icon)

    if is_of_interest:
        filename_suffix = f"{encounter_value.name}_{pokemon.species.safe_name}"
        context.emulator.create_save_state(suffix=filename_suffix)

        if context.config.battle.auto_catch and not disable_auto_catch:
            decision = BattleAction.Catch
        else:
            context.set_manual_mode()
            decision = BattleAction.CustomAction
    elif context.config.battle.battle and not disable_auto_battle:
        decision = BattleAction.Fight
    else:
        decision = BattleAction.RunAway

    log_encounter(pokemon, decision)
    return decision
