from typing import TYPE_CHECKING, Iterable, Generator

if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome
    from modules.encounter import EncounterInfo
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

    def on_battle_started(self, encounter: "EncounterInfo | None") -> Generator | None:
        pass

    def on_wild_encounter_visible(self, encounter: "EncounterInfo") -> Generator | None:
        pass

    def on_battle_ended(self, outcome: "BattleOutcome") -> Generator | None:
        pass

    def on_logging_encounter(self, encounter: "EncounterInfo") -> None:
        pass

    def on_pokemon_evolved(self, evolved_pokemon: "Pokemon") -> Generator | None:
        pass

    def on_egg_starting_to_hatch(self, hatching_pokemon: "EncounterInfo") -> Generator | None:
        pass

    def on_egg_hatched(self, hatched_pokemon: "EncounterInfo") -> Generator | None:
        pass

    def on_whiteout(self) -> Generator | None:
        pass

    def on_judge_encounter(self, opponent: "Pokemon") -> str | bool:
        return False

    def on_should_nickname_pokemon(self, pokemon: "Pokemon") -> str | None:
        return None
