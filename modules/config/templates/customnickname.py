from modules.console import console
from modules.pokemon import Pokemon


def custom_should_nickname_pokemon(pokemon: Pokemon) -> str:
    """
    See readme for documentation: WILL ADD IF THIS MAKES SENSE @TODO

    :param pokemon: Pokémon object of the current encounter
    """
    try:
        ### Edit below this line ###
        # if pokemon.is_anti_shiny:
        #     return "dull"

        return ""
    except Exception:
        console.print_exception(show_locals=True)
        console.print(
            "[red bold]Failed to get nickname for pokemon, potentially due to invalid custom_should_nickname_pokemon..."
        )
        return ""
