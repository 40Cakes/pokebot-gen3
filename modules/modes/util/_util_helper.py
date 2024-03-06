from functools import wraps

from modules.context import context


def isolate_inputs(generator_function):
    @wraps(generator_function)
    def wrapper_function(*args, **kwargs):
        previous_inputs = context.emulator.reset_held_buttons()
        yield from generator_function(*args, **kwargs)
        context.emulator.restore_held_buttons(previous_inputs)

    return wrapper_function
