"""
'Tasks' are the game's implementation of coroutines. This files contains
abstractions and utilities for working with them.
"""

from functools import cached_property
from typing import Iterator

from modules.context import context
from modules.game import get_symbol_name_before
from modules.memory import get_symbol_name, read_symbol, unpack_uint16, unpack_uint32
from modules.state_cache import state_cache


class Task:
    def __init__(self, data: bytes):
        self._data = data

    def __eq__(self, other):
        return other._data == self._data if isinstance(other, Task) else NotImplemented

    def __ne__(self, other):
        return other._data != self._data if isinstance(other, Task) else NotImplemented

    @property
    def function_pointer(self) -> int:
        return unpack_uint32(self._data[:4]) - 1

    @cached_property
    def symbol(self) -> str:
        symbol = get_symbol_name(self.function_pointer, True)
        return hex(self.function_pointer) if symbol == "" else symbol

    @property
    def priority(self) -> int:
        return self._data[7]

    @property
    def data(self) -> bytes:
        return self._data[8:]

    def data_value(self, index: int) -> int:
        return unpack_uint16(self.data[(index * 2) : ((index + 1) * 2)])


class TaskList:
    def __init__(self, data: bytes):
        self._data = data

    def __eq__(self, other):
        if isinstance(other, TaskList):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, TaskList):
            return other._data != self._data
        else:
            return NotImplemented

    def __iter__(self) -> Iterator[Task]:
        yield from self._dict.values()

    def __contains__(self, task_name: str):
        return task_name.lower() in self._dict

    def __getitem__(self, item: str) -> Task | None:
        return self._dict.get(item.lower(), None)

    @cached_property
    def _dict(self) -> dict[str, Task]:
        tasks: dict[str, Task] = {}
        for index in range(16):
            task_data = self._data[index * 40 : (index + 1) * 40]
            # offset 4 is `is_active` and offsets 0 through 3 are the function pointer
            if task_data[4] != 0 and task_data[:4] != b"\x00\x00\x00\x00":
                task = Task(task_data)
                if task.symbol != "TaskDummy":
                    tasks[task.symbol.lower()] = task
        return tasks


class ScriptContext:
    def __init__(self, data: bytes):
        self._data = data

    def __eq__(self, other):
        if isinstance(other, ScriptContext):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, ScriptContext):
            return other._data != self._data
        else:
            return NotImplemented

    @property
    def is_active(self) -> bool:
        return self._data[1] != 0

    @property
    def mode(self) -> str:
        match self._data[1]:
            case 0:
                return "Stopped"
            case 1:
                return "Bytecode"
            case 2:
                return "Native"
            case _:
                return ""

    @property
    def stack_depth(self) -> int:
        return self._data[0]

    @property
    def comparison_result(self) -> int:
        return self._data[2]

    @property
    def native_pointer(self):
        return unpack_uint32(self._data[4:8])

    @property
    def native_function_name(self):
        return get_symbol_name_before(self.native_pointer, pretty_name=True)

    @property
    def bytecode_pointer(self):
        return unpack_uint32(self._data[8:12])

    @property
    def script_function_name(self):
        return get_symbol_name_before(self.bytecode_pointer, pretty_name=True)

    @cached_property
    def stack(self) -> list[str]:
        result = []
        for index in range(self.stack_depth):
            offset = 12 + (index * 4)
            pointer = unpack_uint32(self._data[offset : offset + 4])
            result.append(get_symbol_name_before(pointer, pretty_name=True))
        result.append(self.script_function_name)
        return result

    @property
    def data(self) -> tuple[int, int, int, int]:
        return (
            unpack_uint32(self._data[100:104]),
            unpack_uint32(self._data[104:108]),
            unpack_uint32(self._data[108:112]),
            unpack_uint32(self._data[112:116]),
        )


def get_tasks() -> TaskList:
    if state_cache.tasks.age_in_frames == 0:
        return state_cache.tasks.value

    task_list = TaskList(read_symbol("gTasks"))
    state_cache.tasks = task_list
    return task_list


def get_task(task_name: str) -> Task | None:
    return get_tasks()[task_name]


def task_is_active(task_name: str) -> bool:
    return task_name in get_tasks()


def get_global_script_context() -> ScriptContext:
    if state_cache.global_script_context.age_in_frames == 0:
        return state_cache.global_script_context.value

    ctx = ScriptContext(read_symbol("sScriptContext1" if context.rom.is_rs else "sGlobalScriptContext"))
    state_cache.global_script_context = ctx
    return ctx


def get_immediate_script_context() -> ScriptContext:
    if state_cache.immediate_script_context.age_in_frames == 0:
        return state_cache.immediate_script_context.value

    ctx = ScriptContext(read_symbol("sScriptContext2" if context.rom.is_rs else "sImmediateScriptContext"))
    state_cache.immediate_script_context = ctx
    return ctx


def is_waiting_for_input() -> bool:
    """
    :return: Whether the game is currently waiting for the A or B button to be pressed in order
             to advance some dialogue or scripted event.
    """
    if get_global_script_context().native_function_name == "WaitForAorBPress":
        return True

    if context.rom.is_rs:
        if task_is_active("Task_FieldMessageBox"):
            text_printer_state = read_symbol("gFieldMessageBoxWindow", offset=0x16, size=1)[0]
            return text_printer_state in (8, 9)
    else:
        text_printer_data = read_symbol("sTextPrinters", offset=0x1B, size=2)
        text_printer_is_active = text_printer_data[0]
        text_printer_state = text_printer_data[1]
        return text_printer_is_active and text_printer_state in (2, 3)
