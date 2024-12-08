from modules.memory import get_event_flag, get_event_var, set_event_flag, set_event_var
from modules.game import _event_flags, _event_vars
from modules.runtime import get_base_path

PROFILES_DIRECTORY = get_base_path() / "profiles"
EVENT_FLAGS_FILE_PATH = PROFILES_DIRECTORY / "event_flags.txt"
EVENT_VARS_FILE_PATH = PROFILES_DIRECTORY / "event_vars.txt"


def export_flags_and_vars() -> None:
    def reset_and_write(file_name: str, lines: list[str]) -> None:
        with open(file_name, "w") as file:
            file.write("\n".join(lines) + "\n")

    event_flag_lines = [f"{flag_name} = {'1' if get_event_flag(flag_name) else '0'}" for flag_name in _event_flags]
    event_var_lines = [f"{var_name} = {get_event_var(var_name)}" for var_name in _event_vars]

    reset_and_write(EVENT_FLAGS_FILE_PATH, event_flag_lines)
    reset_and_write(EVENT_VARS_FILE_PATH, event_var_lines)


def write_flags_and_vars() -> None:
    """
    Reads event flags and variables from their respective files and updates them.
    """

    def process_line(line: str, is_boolean_value: bool) -> None:
        if "=" in line:
            name, value = line.strip().split(" = ")
            if is_boolean_value:
                set_event_flag(name, value == "1")
            else:
                set_event_var(name, int(value))

    def read_file(file_path: str, is_boolean_value: bool) -> None:
        try:
            with open(file_path, "r") as file:
                for line in file:
                    process_line(line, is_boolean_value)
        except FileNotFoundError:
            context.message = f"File '{file_path}' not found."
            context.set_manual_mode()
        except IOError as e:
            context.message(f"An error occurred while reading '{file_path}': {e}")
            context.set_manual_mode()

    def reset_and_write(file_name: str, lines: list[str]) -> None:
        with open(file_name, "w") as file:
            file.write("\n".join(lines) + "\n")

    read_file(EVENT_FLAGS_FILE_PATH, is_boolean_value=True)
    read_file(EVENT_VARS_FILE_PATH, is_boolean_value=False)

    event_flag_lines = [f"{flag_name} = {'1' if get_event_flag(flag_name) else '0'}" for flag_name in _event_flags]
    event_var_lines = [f"{var_name} = {get_event_var(var_name)}" for var_name in _event_vars]

    reset_and_write(EVENT_FLAGS_FILE_PATH, event_flag_lines)
    reset_and_write(EVENT_VARS_FILE_PATH, event_var_lines)
