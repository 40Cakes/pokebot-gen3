from typing import TYPE_CHECKING, Iterable, Generator


if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome
    from modules.encounter import ActiveWildEncounter
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

    def on_battle_started(self, opponent: "Pokemon", wild_encounter: "ActiveWildEncounter | None") -> Generator | None:
        pass

    def on_wild_encounter_visible(self, wild_encounter: "ActiveWildEncounter") -> Generator | None:
        pass

    def on_battle_ended(self, outcome: "BattleOutcome") -> Generator | None:
        pass

    def on_pokemon_evolved(self, evolved_pokemon: "Pokemon") -> Generator | None:
        pass

    def on_egg_hatched(self, hatched_pokemon: "Pokemon") -> Generator | None:
        pass

    def on_whiteout(self) -> Generator | None:
        pass

    def on_judge_encounter(self, opponent: "Pokemon") -> str | bool:
        return False

    def on_should_nickname_pokemon(self, pokemon: "Pokemon") -> str | None:
        return None
