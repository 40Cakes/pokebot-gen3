from typing import TYPE_CHECKING, Iterable, Generator

if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome
    from modules.encounter import EncounterInfo
    from modules.modes import BotMode, BotListener
    from modules.pokemon import Pokemon
    from modules.profiles import Profile


class BotPlugin:
    def get_additional_bot_modes(self) -> Iterable[type["BotMode"]]:
        """
        This hook can return an iterable (i.e. a list, tuple, or generator) of bot modes
        that should be added to the default ones.

        It can be used to add custom bot modes without modifying the regular bot code
        (which would get replaced during updates.)

        :return: Iterable of bot mode _types_. Note that this must be a reference to the
                 class itself and not an instance of it. So do `yield MyMode` instead of
                 `yield MyMode()`.
        """
        return []

    def get_additional_bot_listeners(self) -> Iterable["BotListener"]:
        """
        This hook returns a list of bot listeners that should be loaded.

        Bot listeners are classes implementing `BotListener`, and these have a
        `handle_frame()` method that gets called -- you guessed it -- every frame.

        This can be useful to wait for certain in-game events to happen and then
        act upon it without having to do it within a bot mode.

        Bot listeners can also be added in other hooks (by calling
        `context.bot_listeners.append(MyListener())`), in case they don't have to
        run all the time.

        :return: List of _instances_ of bot listeners.
        """

        return []

    def on_profile_loaded(self, profile: "Profile") -> None:
        """
        This is called after a profile has been selected via the GUI or a command-line
        option and the emulation has started.

        :param profile: The profile selected by the user.
        """
        pass

    def on_battle_started(self, encounter: "EncounterInfo | None") -> Generator | None:
        """
        This is called once the game entered battle mode, so when the screen has faded
        to black.

        :param encounter: Information about the encounter if this is a wild Pokémon
                          encounter, otherwise (in trainer battles) None.
        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """

        pass

    def on_wild_encounter_visible(self, encounter: "EncounterInfo") -> Generator | None:
        """
        This is called once a wild encounter is fully visible, i.e. the sliding-in
        animation has completed, the Pokémon has done it's cry and the 'Wild XYZ appeared!'
        message is visible.

        :param encounter: Information about the wild encounter.
        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """
        pass

    def on_battle_ended(self, outcome: "BattleOutcome") -> Generator | None:
        """
        This is called once a battle has ended. At this point, the game is still in battle
        mode and not yet in the overworld. It's just the point at which the outcome of the
        battle is known.

        :param outcome: How the battle ended, e.g. won, lost, ran away, ...
        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """
        pass

    def on_logging_encounter(self, encounter: "EncounterInfo") -> None:
        """
        This is called whenever an encounter is being logged. This _may_ happen because of a
        wild encounter battle, but it also gets triggered by hatching eggs. Bot modes can
        trigger this too by calling `log_encounter()`, which is done for gift Pokémon.

        :param encounter: Information about the wild encounter.
        """
        pass

    def on_pokemon_evolved(self, evolved_pokemon: "Pokemon") -> Generator | None:
        """
        This is called when a Pokémon has evolved. It is not called if an evolution has been
        interrupted by pressing `B`.

        :param evolved_pokemon: Data of the Pokémon _after_ evolution.
        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """
        pass

    def on_egg_starting_to_hatch(self, hatching_pokemon: "EncounterInfo") -> Generator | None:
        """
        This is called when the egg hatching cutscene starts.

        :param hatching_pokemon: Data of the egg that is about to hatch.
        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """

        pass

    def on_egg_hatched(self, hatched_pokemon: "EncounterInfo") -> Generator | None:
        """
        This is called during the egg-hatching cutscene once the egg has hatched and the
        Pokémon is visible.

        :param hatched_pokemon: Data of the Pokémon that has hatched.
        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """
        pass

    def on_whiteout(self) -> Generator | None:
        """
        This is called when the player has whited out (due to being defeated in battle, or
        the last party Pokémon fainting due to poison.)

        When this is called, the white-out dialogue has already been completed and the player
        is standing in front of the last Pokémon Center.

        :return: This _may_ return a Generator (so you can use `yield` inside here), in
                 which case the current bot mode is suspended and this generator function
                 takes control.
        """
        pass

    def on_judge_encounter(self, opponent: "Pokemon") -> str | bool:
        """
        This is called during `judge_encounter()`, which is supposed to decide whether a
        Pokémon is worth catching or not.

        Shiny and Roamer Pokémon are matched automatically, but this can be used to add custom
        filter rules for Pokémon.

        :param opponent: Information about the encountered Pokémon.
        :return: `False` is this Pokémon is considered to NOT be of interest, otherwise a string
                 describing why it has value. This string is displayed in some log messages.
        """
        return False

    def on_should_nickname_pokemon(self, pokemon: "Pokemon") -> str | None:
        """
        This is called when the player is asked whether to give a nickname to a newly
        acquired Pokémon.

        :param pokemon: The newly received Pokémon.
        :return: The nickname (max. 10 characters) to give to the Pokémon, or `None` to
                 not give a nickname.
        """
        return None
