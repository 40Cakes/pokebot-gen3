from modules.console import console
from modules.context import context
from modules.files import save_pk3
from modules.gui.desktop_notification import desktop_notification
from modules.pc_storage import import_into_storage
from modules.pokemon import Pokemon
from modules.stats import total_stats


def encounter_pokemon(pokemon: Pokemon) -> None:
    """
    Call when a Pokémon is encountered, decides whether to battle, flee or catch.
    Expects the trainer's state to be MISC_MENU (battle started, no longer in the overworld).
    It also calls the function to save the pokemon as a pk file if required in the config.

    :return:
    """
    config = context.config
    if config.logging.save_pk3.all:
        save_pk3(pokemon)

    if pokemon.is_shiny:
        config.reload_file('catch_block')

    custom_filter_result = total_stats.custom_catch_filters(pokemon)
    custom_found = isinstance(custom_filter_result, str)

    total_stats.log_encounter(pokemon, config.catch_block.block_list, custom_filter_result)

    context.message = f"Encountered a {pokemon.species.name} with a shiny value of {pokemon.shiny_value:,}!"

    # TODO temporary until auto-catch is ready
    if pokemon.is_shiny or custom_found:
        if pokemon.is_shiny:
            if not config.logging.save_pk3.all and config.logging.save_pk3.shiny:
                save_pk3(pokemon)
            state_tag = "shiny"
            console.print("[bold yellow]Shiny found!")
            context.message = "Shiny found! Bot has been switched to manual mode so you can catch it."

            alert_title = "Shiny found!"
            alert_message = f"Found a shiny {pokemon.species.name}. 🥳"

        elif custom_found:
            if not config.logging.save_pk3.all and config.logging.save_pk3.custom:
                save_pk3(pokemon)
            state_tag = "customfilter"
            console.print("[bold green]Custom filter Pokemon found!")
            context.message = f"Custom filter triggered ({custom_filter_result})! Bot has been switched to manual mode so you can catch it."

            alert_title = "Custom filter triggered!"
            alert_message = f"Found a {pokemon.species.name} that matched one of your filters. ({custom_filter_result})"
        else:
            state_tag = ""
            alert_title = None
            alert_message = None

        if not custom_found and pokemon.species.name in config.catch_block.block_list:
            console.print(f"[bold yellow]{pokemon.species.name} is on the catch block list, skipping encounter...")
        else:
            filename_suffix = f"{state_tag}_{pokemon.species.safe_name}"
            context.emulator.create_save_state(suffix=filename_suffix)

            # TEMPORARY until auto-battle/auto-catch is done
            # if the mon is saved and imported, no need to catch it by hand
            if config.logging.import_pk3:
                if import_into_storage(pokemon.data):
                    return

            context.bot_mode = "Manual"
            context.emulation_speed = 1
            context.video = True

            if alert_title is not None and alert_message is not None:
                desktop_notification(title=alert_title, message=alert_message)
