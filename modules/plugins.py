import inspect
from types import GeneratorType
from typing import TYPE_CHECKING, Iterable, Generator

from modules.battle_state import BattleOutcome
from modules.context import context
from modules.plugin_interface import BotPlugin
from modules.pokemon import Pokemon
from modules.runtime import get_base_path

if TYPE_CHECKING:
    from modules.encounter import EncounterInfo
    from modules.modes import BotMode, BotListener
    from modules.profiles import Profile


plugins: list[BotPlugin] = []


def load_plugins():
    plugins_dir = get_base_path() / "plugins"
    if not plugins_dir.exists():
        return

    for file in plugins_dir.iterdir():
        if file.name.endswith(".py"):
            module_name = file.name[:-3]
            imported_module = __import__(f"plugins.{module_name}")
            classes = list(
                filter(
                    lambda c: issubclass(c[1], BotPlugin) and c[1] is not BotPlugin,
                    inspect.getmembers(getattr(imported_module, module_name), inspect.isclass),
                )
            )

            if len(classes) == 0:
                raise RuntimeError(f"Could not load plugin `{file.name}`: It did not contain any plugin class.")

            for class_name, plugin_class in classes:
                plugins.append(plugin_class())


def load_built_in_plugins():
    # This plugin needs to be loaded first so that is executed first. That's because it is supposed
    # to set the `gif_path` and `tcg_card_path` properties on wild encounters so that other plugins
    # can use them.
    if context.config.logging.shiny_gifs or context.config.logging.tcg_cards:
        from modules.built_in_plugins.generate_encounter_media import GenerateEncounterMediaPlugin

        plugins.insert(0, GenerateEncounterMediaPlugin())

    if context.config.obs.screenshot or context.config.obs.replay_buffer:
        from modules.built_in_plugins.obs import OBSPlugin

        plugins.insert(1, OBSPlugin())

    if context.config.discord.is_anything_enabled():
        from modules.built_in_plugins.discord_integration import DiscordPlugin

        plugins.insert(1, DiscordPlugin())


def plugin_get_additional_bot_modes() -> Iterable["BotMode"]:
    for plugin in plugins:
        yield from plugin.get_additional_bot_modes()


def plugin_get_additional_bot_listeners() -> Iterable["BotListener"]:
    for plugin in plugins:
        yield from plugin.get_additional_bot_listeners()


def plugin_profile_loaded(profile: "Profile") -> None:
    for plugin in plugins:
        plugin.on_profile_loaded(profile)


def plugin_config_reloaded() -> None:
    for plugin in plugins:
        plugin.on_config_reload()


def plugin_battle_started(encounter: "EncounterInfo | None") -> Generator:
    for plugin in plugins:
        result = plugin.on_battle_started(encounter)
        if isinstance(result, GeneratorType):
            yield from result


def plugin_wild_encounter_visible(encounter: "EncounterInfo") -> Generator:
    for plugin in plugins:
        result = plugin.on_wild_encounter_visible(encounter)
        if isinstance(result, GeneratorType):
            yield from result


def plugin_battle_ended(outcome: "BattleOutcome") -> Generator:
    for plugin in plugins:
        result = plugin.on_battle_ended(outcome)
        if isinstance(result, GeneratorType):
            yield from result


def plugin_logging_encounter(encounter: "EncounterInfo") -> None:
    for plugin in plugins:
        plugin.on_logging_encounter(encounter)


def plugin_pokemon_evolved(evolved_pokemon: "Pokemon") -> Generator:
    for plugin in plugins:
        result = plugin.on_pokemon_evolved(evolved_pokemon)
        if isinstance(result, GeneratorType):
            yield from result


def plugin_egg_starting_to_hatch(hatching_pokemon: "EncounterInfo") -> Generator:
    for plugin in plugins:
        result = plugin.on_egg_starting_to_hatch(hatching_pokemon)
        if isinstance(result, GeneratorType):
            yield from result


def plugin_egg_hatched(hatched_pokemon: "EncounterInfo") -> Generator:
    for plugin in plugins:
        result = plugin.on_egg_hatched(hatched_pokemon)
        if isinstance(result, GeneratorType):
            yield from result


def plugin_whiteout() -> Generator:
    for plugin in plugins:
        result = plugin.on_whiteout()
        if isinstance(result, GeneratorType):
            yield from result


def plugin_judge_encounter(pokemon: Pokemon) -> str | bool:
    for plugin in plugins:
        judgement = plugin.on_judge_encounter(pokemon)
        if judgement is not False:
            return judgement

    return False


def plugin_should_nickname_pokemon(pokemon: Pokemon) -> str | None:
    for plugin in plugins:
        nickname = plugin.on_should_nickname_pokemon(pokemon)
        if nickname:
            return nickname

    return None
