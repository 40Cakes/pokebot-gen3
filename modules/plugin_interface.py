from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from modules.battle import BattleOutcome
    from modules.modes import BotMode, BotListener
    from modules.pokemon import Pokemon
    from modules.profiles import Profile


class BotPlugin:
    def get_additional_bot_modes(self) -> Iterable[type["BotMode"]]:
        return []

    def get_additional_bot_listeners(self) -> Iterable["BotListener"]:
        return []

    def on_profile_loaded(self, profile: "Profile") -> None:
        pass

    def on_battle_started(self, opponent: "Pokemon") -> None:
        pass

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        pass

    def on_pokemon_evolved(self, evolved_pokemon: "Pokemon") -> None:
        pass

    def on_egg_hatched(self, hatched_pokemon: "Pokemon") -> None:
        pass

    def on_whiteout(self) -> None:
        pass
