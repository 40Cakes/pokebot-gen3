import random

from modules.context import context
from ._interface import BotMode
from ..encounter import encounter_pokemon
from ..main import work_queue
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
            # Some checks are copy pasted from the main.py loop as this mode never yields to avoid battle handlers
            # and encounter handles taking control of the inputs
            if context.bot_mode == "Manual":
                yield

            while not work_queue.empty():
                callback = work_queue.get_nowait()
                callback()

            if get_game_state() == GameState.BATTLE:
                if opponent_changed():
                    encounter_pokemon(get_opponent(), log_only=True)
            context.emulator.press_button(random.choice(["A", "B", "Start", "Right", "Left", "Up", "Down"]))

            for _ in range(4):  # Press 1 random button every 5 frames
                context.emulator.run_single_frame()
