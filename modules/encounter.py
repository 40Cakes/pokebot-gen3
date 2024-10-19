import importlib
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from modules.battle_state import get_encounter_type, EncounterType
from modules.console import console, print_stats
from modules.context import context
from modules.files import save_pk3, make_string_safe_for_file_name
from modules.gui.desktop_notification import desktop_notification
from modules.map_data import get_map_enum
from modules.memory import get_game_state, GameState
from modules.modes import BattleAction
from modules.player import get_player, get_player_avatar
from modules.plugins import plugin_judge_encounter, plugin_logging_encounter
from modules.pokedex import get_pokedex
from modules.roamer import get_roamer
from modules.runtime import get_sprites_path
from modules.tcg_card import generate_tcg_card

if TYPE_CHECKING:
    from modules.map_data import MapRSE, MapFRLG
    from modules.pokemon import Pokemon


_custom_catch_filters: Callable[["Pokemon"], str | bool] | None = None


@dataclass
class EncounterInfo:
    pokemon: "Pokemon"
    encounter_time: "datetime"
    type: "EncounterType"
    value: "EncounterValue | None"
    map: "MapRSE | MapFRLG | None"
    coordinates: tuple[int, int] | None
    bot_mode: str
    catch_filters_result: str | None
    battle_action: "BattleAction | None" = None
    gif_path: Path | None = None
    tcg_card_path: Path | None = None

    @classmethod
    def create(cls, pokemon: "Pokemon", type: "EncounterType | None" = None) -> "EncounterInfo":
        catch_filters_result = run_custom_catch_filters(pokemon)
        if catch_filters_result is True:
            catch_filters_result = "Match"
        player_avatar = get_player_avatar()
        map_enum = get_map_enum(player_avatar.map_group_and_number)
        local_coordinates = player_avatar.local_coordinates
        return cls(
            pokemon=pokemon,
            encounter_time=datetime.now(timezone.utc),
            type=type if type is not None else get_encounter_type(),
            value=judge_encounter(pokemon),
            map=map_enum,
            coordinates=local_coordinates,
            bot_mode=context.bot_mode,
            catch_filters_result=catch_filters_result,
        )

    @property
    def is_shiny(self) -> bool:
        return self.pokemon.is_shiny

    @property
    def is_of_interest(self) -> bool:
        return self.value.is_of_interest


def run_custom_catch_filters(pokemon: "Pokemon") -> str | bool:
    global _custom_catch_filters
    if _custom_catch_filters is None:
        if (context.profile.path / "customcatchfilters.py").is_file():
            module = importlib.import_module(".customcatchfilters", f"profiles.{context.profile.path.name}")
            _custom_catch_filters = module.custom_catch_filters
        else:
            from profiles.customcatchfilters import custom_catch_filters

            _custom_catch_filters = custom_catch_filters

    result = _custom_catch_filters(pokemon) or plugin_judge_encounter(pokemon)
    if result is True:
        result = "Matched a custom catch filter"
    return result


class EncounterValue(Enum):
    Shiny = auto()
    ShinyOnBlockList = auto()
    Roamer = auto()
    RoamerOnBlockList = auto()
    CustomFilterMatch = auto()
    Trash = auto()

    @property
    def is_of_interest(self):
        return self in (EncounterValue.Shiny, EncounterValue.CustomFilterMatch)


def judge_encounter(pokemon: "Pokemon") -> EncounterValue:
    """
    Checks whether an encountered Pokémon matches any of the criteria that makes it
    eligible for catching (is shiny, matches custom catch filter, ...)

    :param pokemon: The Pokémon that has been encountered.
    :return: The perceived 'value' of the encounter.
    """

    if pokemon.is_shiny:
        context.config.reload_file("catch_block")
        block_list = context.config.catch_block.block_list
        if pokemon.species_name_for_stats in block_list or pokemon.species.name in block_list:
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
        block_list = context.config.catch_block.block_list
        if pokemon.species_name_for_stats in block_list or pokemon.species.name in block_list:
            return EncounterValue.RoamerOnBlockList
        else:
            return EncounterValue.Roamer

    return EncounterValue.Trash


def log_encounter(encounter_info: EncounterInfo) -> None:
    pokemon = encounter_info.pokemon
    if (
        context.stats.last_encounter is not None
        and context.stats.last_encounter.pokemon.personality_value == pokemon.personality_value
    ):
        # Avoid double-logging an encounter.
        return

    log_entry = context.stats.log_encounter(encounter_info)
    if context.config.logging.log_encounters_to_console:
        print_stats(context.stats.get_global_stats(), encounter_info)
    plugin_logging_encounter(encounter_info)
    if encounter_info.is_shiny:
        context.stats.reset_shiny_phase(log_entry)

    # Generate the bot message shown below the video
    fun_facts = [
        f"Nature:\xa0{pokemon.nature.name}",
        f"Ability:\xa0{pokemon.ability.name}",
        f"Item:\xa0{pokemon.held_item.name if pokemon.held_item is not None else '-'}",
        f"IV\xa0sum:\xa0{pokemon.ivs.sum()}",
        f"SV:\xa0{pokemon.shiny_value:,}",
    ]

    species_name = pokemon.species.name
    if pokemon.is_shiny:
        species_name = f"Shiny {species_name}"
    if pokemon.gender == "male":
        species_name += " ♂"
    elif pokemon.gender == "female":
        species_name += " ♀"
    if pokemon.species.name == "Unown":
        species_name += f" ({pokemon.unown_letter})"
    if pokemon.species.name == "Wurmple":
        fun_facts.append(f"Evo: {pokemon.wurmple_evolution.title()}")

    match encounter_info.battle_action:
        case BattleAction.Catch:
            message_action = ", catching..."
        case BattleAction.CustomAction:
            message_action = ", switched to manual mode so you can catch it."
        case BattleAction.Fight:
            message_action = ", FIGHT!"
        case BattleAction.RunAway:
            message_action = ", running away..."
        case _:
            message_action = "."

    context.message = f"{encounter_info.type.verb.title()} {species_name}{message_action}\n\n{' | '.join(fun_facts)}"


def handle_encounter(
    encounter_info: EncounterInfo,
    disable_auto_catch: bool = False,
    enable_auto_battle: bool = False,
    do_not_log_battle_action: bool = False,
) -> BattleAction:
    pokemon = encounter_info.pokemon
    match encounter_info.value:
        case EncounterValue.Shiny:
            console.print(f"[bold yellow]Shiny {pokemon.species.name} found![/]")
            alert = "Shiny found!", f"Found a ✨shiny {pokemon.species.name}✨! 🥳"
            if context.config.logging.save_pk3.shiny:
                save_pk3(pokemon)
            is_of_interest = True

        case EncounterValue.CustomFilterMatch:
            filter_result = encounter_info.catch_filters_result
            console.print(f"[pink green]Custom filter triggered for {pokemon.species.name}: '{filter_result}'[/]")
            alert = "Custom filter triggered!", f"Found a {pokemon.species.name} that matched one of your filters."
            if context.config.logging.save_pk3.custom:
                save_pk3(pokemon)
            is_of_interest = True

        case EncounterValue.Roamer:
            console.print(f"[pink yellow]Roaming {pokemon.species.name} found![/]")
            alert = "Roaming Pokémon found!", f"Encountered a roaming {pokemon.species.name}."
            # If this is the first time the Roamer is encountered
            if pokemon.species not in get_pokedex().seen_species and context.config.logging.save_pk3.roamer:
                save_pk3(pokemon)
            is_of_interest = True

        case EncounterValue.ShinyOnBlockList:
            console.print(f"[bold yellow]{pokemon.species.name} is on the catch block list, skipping encounter...[/]")
            alert = None
            if context.config.logging.save_pk3.shiny:
                save_pk3(pokemon)
            is_of_interest = False

        case EncounterValue.RoamerOnBlockList:
            console.print(f"[bold yellow]{pokemon.species.name} is on the catch block list, skipping encounter...[/]")
            alert = None
            # If this is the first time the Roamer is encountered
            if pokemon.species not in get_pokedex().seen_species and context.config.logging.save_pk3.roamer:
                save_pk3(pokemon)
            is_of_interest = False

        case EncounterValue.Trash | _:
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

    battle_is_active = get_game_state() in (GameState.BATTLE, GameState.BATTLE_STARTING, GameState.BATTLE_ENDING)

    if is_of_interest:
        filename_suffix = (
            f"{encounter_info.value.name}_{make_string_safe_for_file_name(pokemon.species_name_for_stats)}"
        )
        context.emulator.create_save_state(suffix=filename_suffix)

        if context.config.battle.auto_catch and not disable_auto_catch and battle_is_active:
            encounter_info.battle_action = BattleAction.Catch
        else:
            context.set_manual_mode()
            encounter_info.battle_action = BattleAction.CustomAction
    elif enable_auto_battle:
        encounter_info.battle_action = BattleAction.Fight
    else:
        encounter_info.battle_action = BattleAction.RunAway

    if do_not_log_battle_action:
        encounter_info.battle_action = None

    # During battles the logging is done by `BattleListener` once the encounter is
    # actually visible (rather than at the start of the battle.)
    if not battle_is_active:
        log_encounter(encounter_info)

    return encounter_info.battle_action
