from modules.context import context
from modules.pokemon import Pokemon
from modules.roms import ROMLanguage


def max_pokemon_name_length() -> int:
    if context.rom.language == ROMLanguage.Japanese:
        return 5
    return 10


def should_nickname_pokemon(pokemon: Pokemon) -> str:
    from modules.plugins import plugin_should_nickname_pokemon

    return plugin_should_nickname_pokemon(pokemon)
