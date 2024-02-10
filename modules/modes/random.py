import random

from modules.context import context
from . import BattleAction
from ._interface import BotMode
from ..encounter import log_encounter
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

    def on_battle_started(self) -> BattleAction | None:
        return BattleAction.CustomAction

    def run(self) -> None:
        inputs = ["Start", "Select"]
        inputs.extend(["A"] * 150)
        inputs.extend(["B"] * 50)
        inputs.extend(["Right"] * 150)
        inputs.extend(["Left"] * 150)
        inputs.extend(["Up"] * 150)
        inputs.extend(["Down"] * 150)

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
                    log_encounter(get_opponent())
            context.emulator.press_button(random.choice(inputs))

            for _ in range(4):  # Press 1 random button every 5 frames
                context.emulator.run_single_frame()
