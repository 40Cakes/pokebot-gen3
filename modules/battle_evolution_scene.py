from typing import Generator

from modules.battle_move_replacing import (
    get_learn_move_state,
    LearnMoveState,
    handle_move_replacement_dialogue,
    get_move_learning_state_index,
)
from modules.battle_strategies import BattleStrategy
from modules.context import context
from modules.debug import debug
from modules.pokemon import get_party
from modules.tasks import get_task, task_is_active


@debug.track
def handle_evolution_scene(strategy: BattleStrategy) -> Generator:
    queried_stategy = False
    should_stop = True
    while True:
        task = get_task("Task_EvolutionScene")
        if task is None:
            break

        task_state = task.data_value(0)
        if task_state == get_move_learning_state_index():
            while get_learn_move_state() != LearnMoveState.AskWhetherToLearn and task_is_active("Task_EvolutionScene"):
                context.emulator.press_button("A")
                yield
            yield from handle_move_replacement_dialogue(strategy)

        if not queried_stategy:
            if task_state >= 4:
                party_index = task.data_value(10)
                should_stop = not strategy.should_allow_evolution(get_party()[party_index], party_index)
                queried_stategy = True

        context.emulator.press_button("B" if should_stop else "A")
        yield
