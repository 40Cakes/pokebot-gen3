from typing import TYPE_CHECKING

from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from modules.battle_state import EncounterType
from modules.context import context

if TYPE_CHECKING:
    from modules.encounter import EncounterInfo
    from modules.stats import GlobalStats, EncounterSummary

theme = Theme(
    {
        "normal": "#a8a878",
        "fire": "#f08030",
        "water": "#6890f0",
        "electric": "#f8d030",
        "grass": "#78c850",
        "ice": "#98d8d8",
        "fighting": "#c03028",
        "poison": "#a040a0",
        "ground": "#e0c068",
        "flying": "#a890f0",
        "psychic": "#f85888",
        "bug": "#a8b820",
        "rock": "#b8a038",
        "ghost": "#705898",
        "dragon": "#7038f8",
        "dark": "#705848",
        "steel": "#b8b8d0",
        "question_marks": "#68a090",
    }
)


def iv_colour(value: "SpeciesRecord | int | None") -> str:
    if value is None:
        return "grey"
    elif int(value) == 31:
        return "yellow"
    elif int(value) == 0:
        return "purple"
    elif int(value) >= 26:
        return "green"
    elif int(value) <= 5:
        return "red"
    else:
        return "white"


def iv_sum_colour(value: "SpeciesRecord | int | None") -> str:
    if value is None:
        return "grey"
    elif int(value) == 186:
        return "yellow"
    elif int(value) == 0:
        return "purple"
    elif int(value) >= 140:
        return "green"
    elif int(value) <= 50:
        return "red"
    else:
        return "white"


def sv_colour(value: "SpeciesRecord | int | None") -> str:
    if value is None:
        return "grey"
    elif int(value) <= 7:
        return "yellow"
    elif int(value) >= 65528:
        return "purple"
    else:
        return "red"


def print_stats(stats: "GlobalStats", encounter: "EncounterInfo") -> None:
    pokemon = encounter.pokemon
    type_colour = pokemon.species.types[0].name.lower()
    rich_name = f"[{type_colour}]{pokemon.species_name_for_stats}[/]"

    match context.config.logging.console.encounter_data:
        case "verbose":
            console.rule(f"\n{rich_name} {encounter.type.verb} at {pokemon.location_met}", style=type_colour)
            pokemon_table = Table()
            pokemon_table.add_column("PID", justify="center", width=10)
            pokemon_table.add_column("Level", justify="center")
            pokemon_table.add_column("Item", justify="center", width=10)
            pokemon_table.add_column("Nature", justify="center", width=10)
            pokemon_table.add_column("Ability", justify="center", width=15)
            pokemon_table.add_column(
                "Hidden Power", justify="center", width=15, style=pokemon.hidden_power_type.name.lower()
            )
            pokemon_table.add_column("Shiny Value", justify="center", style=sv_colour(pokemon.shiny_value), width=10)
            pokemon_table.add_row(
                str(hex(pokemon.personality_value)[2:]).upper(),
                str(pokemon.level),
                pokemon.held_item.name if pokemon.held_item else "-",
                pokemon.nature.name,
                pokemon.ability.name,
                f"{pokemon.hidden_power_type.name} ({pokemon.hidden_power_damage})",
                f"{pokemon.shiny_value:,}",
            )
            console.print(pokemon_table)
        case "basic":
            console.rule(f"\n{rich_name} {encounter.type.verb} at {pokemon.location_met}", style=type_colour)
            console.print(
                f"{rich_name}: PID: {str(hex(pokemon.personality_value)[2:]).upper()} | "
                f"Lv: {pokemon.level:,} | "
                f"Item: {pokemon.held_item.name if pokemon.held_item else '-'} | "
                f"Nature: {pokemon.nature.name} | "
                f"Ability: {pokemon.ability.name} | "
                f"Shiny Value: {pokemon.shiny_value:,}"
            )

    match context.config.logging.console.encounter_ivs:
        case "verbose":
            iv_table = Table(title=f"{pokemon.species.name} IVs")
            iv_table.add_column("HP", justify="center", style=iv_colour(pokemon.ivs.hp))
            iv_table.add_column("ATK", justify="center", style=iv_colour(pokemon.ivs.attack))
            iv_table.add_column("DEF", justify="center", style=iv_colour(pokemon.ivs.defence))
            iv_table.add_column("SPATK", justify="center", style=iv_colour(pokemon.ivs.special_attack))
            iv_table.add_column("SPDEF", justify="center", style=iv_colour(pokemon.ivs.special_defence))
            iv_table.add_column("SPD", justify="center", style=iv_colour(pokemon.ivs.speed))
            iv_table.add_column("Total", justify="right", style=iv_sum_colour(pokemon.ivs.sum()))
            iv_table.add_row(
                f"{pokemon.ivs.hp}",
                f"{pokemon.ivs.attack}",
                f"{pokemon.ivs.defence}",
                f"{pokemon.ivs.special_attack}",
                f"{pokemon.ivs.special_defence}",
                f"{pokemon.ivs.speed}",
                f"{pokemon.ivs.sum()}",
            )
            console.print(iv_table)
        case "basic":
            console.print(
                f"IVs: HP: [{iv_colour(pokemon.ivs.hp)}]{pokemon.ivs.hp}[/] | "
                f"ATK: [{iv_colour(pokemon.ivs.attack)}]{pokemon.ivs.attack}[/] | "
                f"DEF: [{iv_colour(pokemon.ivs.defence)}]{pokemon.ivs.defence}[/] | "
                f"SPATK: [{iv_colour(pokemon.ivs.special_attack)}]{pokemon.ivs.special_attack}[/] | "
                f"SPDEF: [{iv_colour(pokemon.ivs.special_defence)}]{pokemon.ivs.special_defence}[/] | "
                f"SPD: [{iv_colour(pokemon.ivs.speed)}]{pokemon.ivs.speed}[/] | "
                f"Sum: [{iv_sum_colour(pokemon.ivs.sum())}]{pokemon.ivs.sum()}[/]"
            )

    def format_shiny_average(encounter_summary: "EncounterSummary | EncounterTotals") -> str:
        if encounter_summary.shiny_encounters > 0:
            return f"1/{int(encounter_summary.total_encounters / encounter_summary.shiny_encounters)}"
        else:
            return "N/A"

    match context.config.logging.console.encounter_moves:
        case "verbose":
            move_table = Table(title=f"{pokemon.species.name} Moves")
            move_table.add_column("Name", justify="left", width=20)
            move_table.add_column("Kind", justify="center", width=10)
            move_table.add_column("Type", justify="center", width=10)
            move_table.add_column("Power", justify="center", width=10)
            move_table.add_column("Accuracy", justify="center", width=10)
            move_table.add_column("PP", justify="center", width=5)
            for i in range(4):
                learned_move = pokemon.move(i)
                if learned_move is not None:
                    move = learned_move.move
                    move_table.add_row(
                        move.name,
                        move.type.kind,
                        move.type.name,
                        str(move.base_power),
                        str(move.accuracy),
                        str(learned_move.pp),
                    )
            console.print(move_table)
        case "basic":
            for i in range(4):
                learned_move = pokemon.move(i)
                if learned_move is not None:
                    move = learned_move.move
                    move_colour = move.type.name.lower()
                    if move_colour == "???":
                        move_colour = "question_marks"
                    console.print(
                        f"[{move_colour}]Move {i + 1}[/]: {move.name} | "
                        f"{move.type.kind} | "
                        f"[{move_colour}]{move.type.name}[/] | "
                        f"Pwr: {move.base_power} | "
                        f"Acc: {move.accuracy} | "
                        f"PP: {learned_move.pp}"
                    )

    number = lambda x: f"{int(x):,}" if x is not None else "-"
    percentage = lambda x, y: f"{100*x/y:0.2f}%" if x is not None and y is not None and y > 0 else "-"

    match context.config.logging.console.statistics:
        case "verbose":
            stats_table = Table(title="Statistics")
            stats_table.add_column("", justify="left", width=10)
            stats_table.add_column("Phase IV Records", justify="center", width=10)
            stats_table.add_column("Phase SV Records", justify="center", width=15)
            stats_table.add_column("Phase Encounters", justify="right", width=10)
            stats_table.add_column("Phase %", justify="right", width=10)
            stats_table.add_column("Shiny Encounters", justify="right", width=10)
            stats_table.add_column("Total Encounters", justify="right", width=10)
            stats_table.add_column("Shiny Average", justify="right", width=10)

            encounter_summaries: list["EncounterSummary"] = list(
                filter(lambda e: e.phase_encounters > 0, stats.encounter_summaries.values())
            )
            encounter_summaries.sort(key=lambda e: e.species_name)
            for summary in encounter_summaries:
                stats_table.add_row(
                    summary.species_name,
                    f"[red]{number(summary.phase_lowest_iv_sum)}[/] / [green]{number(summary.phase_highest_iv_sum)}",
                    f"[green]{number(summary.phase_lowest_sv)}[/] / [{sv_colour(summary.phase_highest_sv)}]{number(summary.phase_highest_sv)}",
                    f"{number(summary.phase_encounters)}",
                    f"{percentage(summary.phase_encounters, stats.totals.phase_encounters)}",
                    f"{number(summary.shiny_encounters)}",
                    f"{number(summary.total_encounters)}",
                    format_shiny_average(summary),
                )
            stats_table.add_row(
                "[bold yellow]Total",
                f"[red]{number(stats.totals.phase_lowest_iv_sum)}[/] / [green]{number(stats.totals.phase_highest_iv_sum)}",
                f"[green]{number(stats.totals.phase_lowest_sv)}[/] / [{sv_colour(stats.totals.phase_highest_sv)}]{number(stats.totals.phase_highest_sv)}",
                f"[bold yellow]{number(stats.totals.phase_encounters)}",
                "[bold yellow]100%",
                f"[bold yellow]{number(stats.totals.shiny_encounters)}",
                f"[bold yellow]{number(stats.totals.total_encounters)}",
                format_shiny_average(stats.totals),
            )
            console.print(stats_table)
        case "basic":
            console.print(
                f"{rich_name} Phase Encounters: {number(stats.encounter_summaries[pokemon.species.index].phase_encounters)} | "
                f"{rich_name} Total Encounters: {number(stats.encounter_summaries[pokemon.species.index].total_encounters)} | "
                f"{rich_name} Shiny Encounters: {number(stats.encounter_summaries[pokemon.species.index].shiny_encounters)}"
            )
            console.print(
                f"{rich_name} Phase IV Records [red]{number(stats.encounter_summaries[pokemon.species.index].phase_lowest_iv_sum)}[/]/[green]{number(stats.encounter_summaries[pokemon.species.index].phase_highest_iv_sum)}[/] | "
                f"{rich_name} Phase SV Records [green]{number(stats.encounter_summaries[pokemon.species.index].phase_lowest_sv)}[/]/[{sv_colour(stats.encounter_summaries[pokemon.species.index].phase_highest_sv)}]{number(stats.encounter_summaries[pokemon.species.index].phase_highest_sv)}[/] | "
                f"{rich_name} Shiny Average: {format_shiny_average(stats.encounter_summaries[pokemon.species.index])}"
            )
            console.print(
                f"Phase Encounters: {number(stats.totals.phase_encounters)} | "
                f"Phase IV Records [red]{number(stats.totals.phase_lowest_iv_sum)}[/]/[green]{number(stats.totals.phase_highest_iv_sum)}[/] | "
                f"Phase SV Records [green]{number(stats.totals.phase_lowest_sv)}[/]/[{sv_colour(stats.totals.phase_highest_sv)}]{number(stats.totals.phase_highest_sv)}[/]"
            )
            console.print(
                f"Total Shinies: {number(stats.totals.shiny_encounters)} | "
                f"Total Encounters: {number(stats.totals.total_encounters)} | "
                f"Total Shiny Average: {format_shiny_average(stats.totals)})"
            )


console = Console(theme=theme)
