"""
Contains definitions for the `BotMode` base class as well as the `BotModeError` type, so we
can import that anywhere without having to worry about circular import issues.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Generator, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from modules.battle import BattleOutcome
    from modules.memory import GameState
    from modules.pokemon import Pokemon


class BattleAction(Enum):
    Fight = auto()
    RunAway = auto()
    Catch = auto()
    CustomAction = auto()


class BotMode:
    @staticmethod
    def name() -> str:
        """
        :return: The name of this mode that will be displayed in the bot mode selection drop-down.
        """
        raise NotImplementedError

    @staticmethod
    def is_selectable() -> bool:
        """
        Indicates whether this bot mode is available for the current state of the game.
        If this returns `False`, the bot mode will not be hidden from the bot mode selection menu.

        Therefore, this should only do a very rough sanity check, such as verifying that the player
        is at least on the correct map. It should not check for very particular things such as
        having an empty party slot etc.

        Those things should be checked within the `run()` method and raise a `BotModeError` if
        necessary, so that the user can get a meaningful error message.

        Otherwise, it might be very confusing for users if a bot mode they expect to see is missing
        without any clear indication as to what exactly is wrong.

        :return: Whether this bot mode should be selectable.
        """
        return True

    def run(self) -> Generator:
        """
        Contains the actual handling code.

        This should be a Generator function (i.e. a function that uses the `yield` keyword)
        which will be called once per frame -- so each time it calls `yield`, the emulator
        will process another frame and only then the function resumes.

        The generator might not be called for every frame: If a battle started, by default
        the battle handler will be used instead until the battle finishes. This behaviour
        can be prevented by making `self.disable_default_battle_handler()` return `True`,
        in which case this Generator function will also be called inside of battles.
        """
        raise NotImplementedError

    def on_battle_started(self) -> BattleAction | None:
        """
        This is called when a battle starts, i.e. a wild Pokemon is encountered or a trainer
        battle commenced.

        When this method is called, the game state is already `GameState.BATTLE`.

        :return: What to do when the battle starts, or `None` if this mode wants to handle
                 the battle itself.
        """
        return None

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        """
        This is called when a battle is over, i.e. the final result is known.

        At that point, the game state is still `GameState.BATTLE`.

        :param outcome: Indicates how the battle ended.
        """
        pass

    def on_spotted_by_trainer(self) -> None:
        """
        This is called whenever a trainer has spotted the player in the
        overworld and is about to walk up to them and initiate a battle.

        It will not be called if the player initiates the battle by walking
        up to the trainer and pressing A.
        """
        pass

    def on_pokenav_call(self) -> None:
        """
        This is called whenever the PokeNav is ringing.
        """
        pass

    def on_repel_effect_ended(self) -> None:
        """
        When the Repel effect expires (number of steps have been reached), the game will
        display a message.

        The bot will confirm/close that message, and then call this method.
        """
        pass

    def on_pokemon_fainted_due_to_poison(self, pokemon: "Pokemon", party_index: int) -> None:
        """
        This is called when a Pokemon faints due to poison while walking around the overworld
        (i.e. this will not be called if it happens during a battle.)

        :param pokemon: Data of the Pokemon that fainted.
        :param party_index: Party index (0-5) of the Pokemon that fainted.
        """
        pass

    def on_whiteout(self) -> bool:
        """
        This is called when all party members have been defeated and the player
        is about to be sent back to the last healing spot.

        That can happen either at the end of a battle, or if the last remaining
        party member succumbs to poison.

        :return: Indicates whether the bot mode would like to handle this event.
                 By default (False), the bot will be switched back to manual mode
                 so the user can handle this case.
        """
        return False

    def on_safari_zone_timeout(self) -> bool:
        """
        This is called after the player has been kicked out of the Safari Zone,
        either due to using up all the Safari Balls or because the number of
        allowed steps have been reached.

        The bot will call this method after the player has been sent back to the
        Safari Zone entrance and can be controlled again.

        :return: Indicates whether the bot mode would like to handle this event.
                 By default (False), the bot will be switched back to manual mode
                 so the user can handle this case.
        """
        return False

    def on_egg_hatched(self, pokemon: "Pokemon", party_index: int) -> None:
        """
        This is called when an egg is hatching.

        The bot will call this method when the hatched Pokemon's sprite is
        visible during the cutscene.

        :param pokemon: The Pokemon that has hatched.
        :param party_index: Party index (0-5) of the Pokemon that has hatched.
        """
        pass

    def __init__(self):
        self._iterator = self.run()

    def __next__(self):
        return next(self._iterator)


class BotModeError(Exception):
    pass


@dataclass
class FrameInfo:
    frame_count: int
    game_state: "GameState"
    script_stack: list[str]
    active_tasks: list[str]
    previous_frame: Optional["FrameInfo"]

    def game_state_changed(self) -> bool:
        return self.previous_frame is None or self.game_state != self.previous_frame.game_state

    def game_state_changed_to(self, game_state_to_check: "GameState") -> bool:
        return self.game_state_changed() and self.game_state == game_state_to_check

    def game_state_changed_from(self, game_state_to_check: "GameState") -> bool:
        return (
            self.game_state_changed()
            and self.previous_frame is not None
            and self.previous_frame.game_state == game_state_to_check
        )

    def task_is_active(self, task_name: str) -> bool:
        return task_name.lower() in self.active_tasks

    def script_is_active(self, script_name: str) -> bool:
        return script_name in self.script_stack


class BotListener:
    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        raise NotImplementedError
