import inspect

from functools import wraps


class DebugUtil:
    def __init__(self):
        self.enabled = False
        self.action_stack = []
        self.debug_values = {}

    def reset(self):
        self.action_stack = []
        self.debug_values = {}

    def track(self, generator_function):
        @wraps(generator_function)
        def wrapper_function(*args, **kwargs):
            if self.enabled:
                name = generator_function.__name__
                formatted_args = []
                spec = inspect.getfullargspec(generator_function)
                if len(args) > 0 and spec.args and spec.args[0] in ("self", "cls"):
                    name = f"{args[0].__class__.__name__}.{name}"
                    for arg in args[1:]:
                        formatted_args.append(repr(arg))
                else:
                    for arg in args:
                        formatted_args.append(repr(arg))
                for key, value in kwargs.items():
                    formatted_args.append(f"{key}={repr(value)}")
                self.action_stack.append(f"{name}({', '.join(formatted_args)})")

            try:
                yield from generator_function(*args, **kwargs)
            finally:
                if self.enabled:
                    self.action_stack.pop()

        return wrapper_function


debug = DebugUtil()
