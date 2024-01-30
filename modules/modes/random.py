import random

from modules.context import context
from ._interface import BotMode
from ..encounter import encounter_pokemon
from ..memory import get_game_state, GameState
from ..pokemon import opponent_changed, get_opponent


class RandomMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Random Inputs"

    @staticmethod
    def is_selectable() -> bool:
        return True

    def run(self) -> None:
        while True:
            if context.bot_mode == "Manual":
                yield

            if not context.emulator.get_frame_count() % 5:
                if get_game_state() == GameState.BATTLE:
                    if opponent_changed():
                        encounter_pokemon(get_opponent(), log_only=True)
                context.emulator.press_button(random.choice(["A", "B", "Select", "Start", "Right", "Left", "Up", "Down", "R", "L"]))
            context.emulator.run_single_frame()
