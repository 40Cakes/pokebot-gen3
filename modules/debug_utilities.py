from datetime import datetime
from pathlib import Path

from modules.context import context
from modules.game import _event_flags, _event_vars
from modules.memory import get_event_flag, get_event_var, set_event_flag, set_event_var


def export_flags_and_vars(file_path: Path) -> None:
    """
    Exports event flags and event vars into a file, using an INI-like format.
    :param file_path: Path to the target file that flags and vars should be written to.
    """
    with open(file_path, "w") as file:
        file.writelines(
            [
                f"# Exported on {datetime.now().isoformat()}\n",
                f"# Game: {context.rom.game_name} ({context.rom.language.name})\n"
                f"# Profile: {context.profile.path.name}\n"
                "\n[flags]\n",
                *[f"{flag_name} = {'1' if get_event_flag(flag_name) else '0'}\n" for flag_name in _event_flags],
                "\n[vars]\n",
                *[f"{var_name} = {get_event_var(var_name)}\n" for var_name in _event_vars],
            ]
        )


def import_flags_and_vars(file_path: Path) -> None:
    """
    Reads event flags and variables from a file and updates them.
    :param file_path: Path to the file to read from.
    """
    in_flags_section = True
    with open(file_path, "r") as file:
        line_number = 0
        for line in file.readlines():
            line_number += 1
            line = line.split("#", 1)[0].strip()
            if line.lower() == "[flags]":
                in_flags_section = True
                continue
            elif line.lower() == "[vars]":
                in_flags_section = False
                continue
            elif line == "":
                continue
            elif "=" not in line:
                raise SyntaxError(f"Error in line #{line_number}: Missing a `=` character.")
            else:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if in_flags_section:
                    if value == "1":
                        set_event_flag(key, True)
                    elif value == "0":
                        set_event_flag(key, False)
                    else:
                        raise ValueError(
                            f"Error in line #{line_number}: Invalid value '{value}' for event flag '{key}'."
                        )
                else:
                    set_event_var(key, int(value))
