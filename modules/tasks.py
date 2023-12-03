"""
'Tasks' are the game's implementation of coroutines. This files contains
abstractions and utilities for working with them.
"""
from functools import cached_property
from typing import Iterator

from modules.memory import unpack_uint32, read_symbol, get_symbol_name
from modules.state_cache import state_cache


class Task:
    def __init__(self, data: bytes):
        self._data = data

    def __eq__(self, other):
        if isinstance(other, Task):
            return other._data == self._data
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Task):
            return other._data != self._data
        else:
            return NotImplemented

    @property
    def function_pointer(self) -> int:
        return unpack_uint32(self._data[0:4]) - 1

    @cached_property
    def symbol(self) -> str:
        symbol = get_symbol_name(self.function_pointer, True)
        if symbol == "":
            return hex(self.function_pointer)
        else:
            return symbol

    @property
    def priority(self) -> int:
        return self._data[7]

    @property
    def data(self) -> bytes:
        return self._data[8:16]


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
            task_data = self._data[index * 40: (index + 1) * 40]
            # offset 4 is `is_active` and offsets 0 through 3 are the function pointer
            if task_data[4] != 0 and task_data[0:4] != b"\x00\x00\x00\x00":
                task = Task(task_data)
                if task.symbol != "TaskDummy":
                    tasks[task.symbol.lower()] = task
        return tasks


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
