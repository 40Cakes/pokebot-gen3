from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from modules.context import context
from modules.pokemon import Pokemon

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
    }
)


def iv_colour(value: int) -> str:
    if value == 31:
        return "yellow"
    if value == 0:
        return "purple"
    if value >= 26:
        return "green"
    if value <= 5:
        return "red"
    return "white"


def iv_sum_colour(value: int) -> str:
    if value == 186:
        return "yellow"
    if value == 0:
        return "purple"
    if value >= 140:
        return "green"
    if value <= 50:
        return "red"
    return "white"


def sv_colour(value: int) -> str:
    if value <= 7:
        return "yellow"
    if value >= 65528:
        return "purple"
    return "red"


def print_stats(total_stats: dict, pokemon: Pokemon, session_pokemon: list, encounter_rate: int) -> None:
    type_colour = pokemon.species.types[0].name.lower()
    rich_name = f"[{type_colour}]{pokemon.species.name}[/]"
    console.print("\n")
    console.rule(f"{rich_name} encountered at {pokemon.location_met}", style=type_colour)

    match context.config.logging.console.encounter_data:
        case "verbose":
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
            console.print(
                f"{rich_name}: PID: {str(hex(pokemon.personality_value)[2:]).upper()} | "
                f"Lv.: {pokemon.level:,} | "
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
                    console.print(
                        f"[{move_colour}]Move {i + 1}[/]: {move.name} | "
                        f"{move.type.kind} | "
                        f"[{move_colour}]{move.type.name}[/] | "
                        f"Pwr: {move.base_power} | "
                        f"Acc: {move.accuracy} | "
                        f"PP: {learned_move.pp}"
                    )

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

            for p in sorted(set(session_pokemon)):
                stats_table.add_row(
                    p,
                    f"[red]{total_stats['pokemon'][p].get('phase_lowest_iv_sum', -1)}[/] / [green]{total_stats['pokemon'][p].get('phase_highest_iv_sum', -1)}",
                    f"[green]{total_stats['pokemon'][p].get('phase_lowest_sv', -1):,}[/] / [{sv_colour(total_stats['pokemon'][p].get('phase_highest_sv', -1))}]{total_stats['pokemon'][p].get('phase_highest_sv', -1):,}",
                    f"{total_stats['pokemon'][p].get('phase_encounters', 0):,}",
                    f"{(total_stats['pokemon'][p].get('phase_encounters', 0) / total_stats['totals'].get('phase_encounters', 0)) * 100:0.2f}%",
                    f"{total_stats['pokemon'][p].get('shiny_encounters', 0):,}",
                    f"{total_stats['pokemon'][p].get('encounters', 0):,}",
                    f"{total_stats['pokemon'][p].get('shiny_average', 'N/A')}",
                )
            stats_table.add_row(
                "[bold yellow]Total",
                f"[red]{total_stats['totals'].get('phase_lowest_iv_sum', -1)}[/] / [green]{total_stats['totals'].get('phase_highest_iv_sum', -1)}",
                f"[green]{total_stats['totals'].get('phase_lowest_sv', -1):,}[/] / [{sv_colour(total_stats['totals'].get('phase_highest_sv', -1))}]{total_stats['totals'].get('phase_highest_sv', -1):,}",
                f"[bold yellow]{total_stats['totals'].get('phase_encounters', 0):,}",
                "[bold yellow]100%",
                f"[bold yellow]{total_stats['totals'].get('shiny_encounters', 0):,}",
                f"[bold yellow]{total_stats['totals'].get('encounters', 0):,}",
                f"[bold yellow]{total_stats['totals'].get('shiny_average', 'N/A')}",
            )
            console.print(stats_table)
        case "basic":
            console.print(
                f"{rich_name} Phase Encounters: {total_stats['pokemon'][pokemon.species.name].get('phase_encounters', 0):,} | "
                f"{rich_name} Total Encounters: {total_stats['pokemon'][pokemon.species.name].get('encounters', 0):,} | "
                f"{rich_name} Shiny Encounters: {total_stats['pokemon'][pokemon.species.name].get('shiny_encounters', 0):,}"
            )
            console.print(
                f"{rich_name} Phase IV Records [red]{total_stats['pokemon'][pokemon.species.name].get('phase_lowest_iv_sum', -1)}[/]/[green]{total_stats['pokemon'][pokemon.species.name].get('phase_highest_iv_sum', -1)}[/] | "
                f"{rich_name} Phase SV Records [green]{total_stats['pokemon'][pokemon.species.name].get('phase_lowest_sv', -1):,}[/]/[{sv_colour(total_stats['pokemon'][pokemon.species.name].get('phase_highest_sv', -1))}]{total_stats['pokemon'][pokemon.species.name].get('phase_highest_sv', -1):,}[/] | "
                f"{rich_name} Shiny Average: {total_stats['pokemon'][pokemon.species.name].get('shiny_average', 'N/A')}"
            )
            console.print(
                f"Phase Encounters: {total_stats['totals'].get('phase_encounters', 0):,} | "
                f"Phase IV Records [red]{total_stats['totals'].get('phase_lowest_iv_sum', -1)}[/]/[green]{total_stats['totals'].get('phase_highest_iv_sum', -1)}[/] | "
                f"Phase SV Records [green]{total_stats['totals'].get('phase_lowest_sv', -1):,}[/]/[{sv_colour(total_stats['totals'].get('phase_highest_sv', -1))}]{total_stats['totals'].get('phase_highest_sv', -1):,}[/]"
            )
            console.print(
                f"Total Shinies: {total_stats['totals'].get('shiny_encounters', 0):,} | "
                f"Total Encounters: {total_stats['totals'].get('encounters', 0):,} | "
                f"Total Shiny Average: {total_stats['totals'].get('shiny_average', 'N/A')})"
            )

    console.print(f"[yellow]Encounter rate[/]: {encounter_rate:,}/h")


console = Console(theme=theme)
