from enum import Enum, auto
from typing import Generator

from modules.battle_state import battle_is_active
from modules.battle_strategies import BattleStrategy
from modules.context import context
from modules.debug import debug
from modules.game import get_symbol
from modules.memory import read_symbol, unpack_uint32
from modules.memory import unpack_uint16
from modules.pokemon import get_move_by_index, get_party
from modules.tasks import task_is_active, get_task, Task


class LearnMoveState(Enum):
    Unknown = auto()
    DialogueNotActive = auto()
    AskWhetherToLearn = auto()
    ConfirmCancellation = auto()
    SelectMoveToReplace = auto()


def get_learn_move_state() -> LearnMoveState:
    """
    Determines what step of the move_learning process we're on.
    """
    move_selection_task = _get_evolution_task_name()

    if task_is_active("Task_EvolutionScene"):
        if task_is_active(move_selection_task):
            return LearnMoveState.SelectMoveToReplace

        task_evolution_scene = get_task("Task_EvolutionScene")
        is_in_move_learning_stage = task_evolution_scene.data_value(0) == get_move_learning_state_index()

        if is_in_move_learning_stage and _is_asking_whether_to_replace_move(task_evolution_scene):
            return LearnMoveState.AskWhetherToLearn

        if is_in_move_learning_stage and _is_asking_whether_to_cancel_learning_move(task_evolution_scene):
            return LearnMoveState.ConfirmCancellation

    elif battle_is_active():
        ask_to_learn_move_script = get_symbol("BattleScript_AskToLearnMove")[0]
        script_length = get_symbol("BattleScript_ForgotAndLearnedNewMove")[0] - ask_to_learn_move_script
        current_script_instruction = unpack_uint32(read_symbol("gBattleScriptCurrInstr", size=4))

        if (
            current_script_instruction < ask_to_learn_move_script
            or current_script_instruction > ask_to_learn_move_script + script_length
        ):
            return LearnMoveState.DialogueNotActive
        elif task_is_active(move_selection_task):
            return LearnMoveState.SelectMoveToReplace
        elif current_script_instruction == ask_to_learn_move_script + 0x11:
            return LearnMoveState.AskWhetherToLearn
        elif current_script_instruction == ask_to_learn_move_script + 0x20:
            return LearnMoveState.ConfirmCancellation
        else:
            return LearnMoveState.Unknown

    return LearnMoveState.DialogueNotActive


@debug.track
def handle_move_replacement_dialogue(strategy: BattleStrategy) -> Generator:
    move_to_forget = 4
    already_confirmed = False
    while True:
        evolution_task = get_task("Task_EvolutionScene")
        if evolution_task is not None and evolution_task.data_value(0) != get_move_learning_state_index():
            yield
            break

        state = get_learn_move_state()
        if state == LearnMoveState.DialogueNotActive:
            yield
            break

        if state == LearnMoveState.AskWhetherToLearn and not already_confirmed:
            debug.action_stack.append("LearnMoveState.AskWhetherToLearn")
            move_to_learn = get_move_by_index(unpack_uint16(read_symbol("gMoveToLearn", size=2)))
            if context.rom.is_rs:
                if evolution_task is not None:
                    party_index = evolution_task.data_value(12)
                else:
                    party_index = context.emulator.read_bytes(0x02016018, length=1)[0]
            else:
                party_index = read_symbol("gBattleStruct", 16, 1)[0]
            pokemon = get_party()[party_index]
            decision = strategy.which_move_should_be_replaced(pokemon, move_to_learn)

            if decision in (0, 1, 2, 3):
                move_to_forget = decision
                while get_learn_move_state() != LearnMoveState.SelectMoveToReplace:
                    context.emulator.press_button("A")
                    yield
            else:
                while get_learn_move_state() != LearnMoveState.ConfirmCancellation:
                    context.emulator.press_button("B")
                    yield
            already_confirmed = True
            debug.action_stack.pop()

        elif state == LearnMoveState.ConfirmCancellation:
            debug.action_stack.append("LearnMoveState.ConfirmCancellation")
            while get_learn_move_state() != LearnMoveState.Unknown:
                context.emulator.press_button("A")
                yield
            debug.action_stack.pop()

        elif state == LearnMoveState.SelectMoveToReplace:
            debug.action_stack.append("LearnMoveState.SelectMoveToReplace")
            cursor = _get_move_selection_cursor()
            if cursor < move_to_forget:
                context.emulator.press_button("Down")
                yield
                yield
            elif cursor > move_to_forget:
                context.emulator.press_button("Up")
                yield
                yield
            else:
                while get_learn_move_state() not in (LearnMoveState.Unknown, LearnMoveState.DialogueNotActive):
                    context.emulator.press_button("A")
                    yield
            debug.action_stack.pop()

        else:
            context.emulator.press_button("B")
            yield


def get_move_learning_state_index() -> int:
    if context.rom.is_rs:
        return 21
    else:
        return 22


def _get_evolution_task_name() -> str:
    if context.rom.is_rs:
        return "sub_809E260"
    elif context.rom.is_emerald:
        return "Task_HandleReplaceMoveInput"
    else:
        return "Task_InputHandler_SelectOrForgetMove"


def _is_asking_whether_to_replace_move(evolution_task: Task) -> bool:
    if context.rom.is_rs:
        return (
            evolution_task.data_value(8) == 4
            and evolution_task.data_value(9) == 5
            and evolution_task.data_value(10) == 9
        )
    elif context.rom.is_emerald:
        return evolution_task.data_value(6) == 4 and evolution_task.data_value(7) == 5
    else:
        return (
            evolution_task.data_value(6) == 4
            and evolution_task.data_value(7) == 5
            and evolution_task.data_value(8) == 10
        )


def _is_asking_whether_to_cancel_learning_move(evolution_task: Task) -> bool:
    if context.rom.is_rs:
        return (
            evolution_task.data_value(8) == 4
            and evolution_task.data_value(9) == 10
            and evolution_task.data_value(10) == 0
        )
    elif context.rom.is_emerald:
        return evolution_task.data_value(6) == 4 and evolution_task.data_value(7) == 11
    else:
        return (
            evolution_task.data_value(6) == 4
            and evolution_task.data_value(7) == 11
            and evolution_task.data_value(8) == 0
        )


def _get_move_selection_cursor() -> int:
    if context.rom.is_emerald:
        pointer = unpack_uint32(read_symbol("sMonSummaryScreen")) + 0x40C6
        return context.emulator.read_bytes(pointer, 1)[0]
    elif context.rom.is_frlg:
        return read_symbol("sMoveSelectionCursorPos", size=1)[0]
    else:
        return read_symbol("gSharedMem", offset=0x18079, size=1)[0]
