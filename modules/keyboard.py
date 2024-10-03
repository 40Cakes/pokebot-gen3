import contextlib
import json
from pathlib import Path

from modules.context import context
from modules.game import decode_string
from modules.memory import read_symbol, unpack_uint32
from modules.tasks import task_is_active

DATA_DIRECTORY = Path(__file__).parent / "data"

with open(f"{DATA_DIRECTORY}/keyboard.json", "r", encoding="utf-8") as f:
    key_layout = json.load(f)

# Will have to add more languages later and detect it
lang = "en"

valid_characters = []
for page in key_layout[lang]:
    for row in page["array"]:
        valid_characters.extend(row)


class Keyboard:
    @property
    def enabled(self) -> bool:
        if task_is_active("Task_NamingScreen"):
            return True
        elif task_is_active("Task_NamingScreenMain"):
            return True
        else:
            return False

    @property
    def text_buffer(self) -> str:
        try:
            if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
                return decode_string(
                    context.emulator.read_bytes(unpack_uint32(read_symbol("sNamingScreen")) + 0x1800, 16)
                )
            else:
                return decode_string(
                    context.emulator.read_bytes(unpack_uint32(read_symbol("namingScreenDataPtr")) + 0x11, 16)
                )
        except Exception:
            return None

    @property
    def cur_page(self) -> int:
        try:
            if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
                return [1, 2, 0].index(
                    context.emulator.read_bytes(unpack_uint32(read_symbol("sNamingScreen")) + 0x1E22, 1)[0]
                )
            else:
                return [0x3C, 0x42, 0x3F].index(context.emulator.read_bytes(0x03001858, 1)[0])
        except Exception:
            return None

    @property
    def cur_pos(self) -> tuple:
        x_val = None
        y_val = None
        if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
            x_val = int(context.emulator.read_bytes(0x03007D98, 1)[0])
            if context.rom.game_title == "POKEMON EMER":
                y_val = int(context.emulator.read_bytes(0x030023A8, 1)[0] / 16) - 5
            else:
                y_val = int(context.emulator.read_bytes(0x030031D8, 1)[0] / 16) - 5
        else:
            with contextlib.suppress(Exception):
                x_val = (
                    [0x1B, 0x33, 0x4B, 0x63, 0x7B, 0x93, 0xBC].index(context.emulator.read_bytes(0x0300185E, 1)[0])
                    if self.cur_page == 2
                    else [
                        0x1B,
                        0x2B,
                        0x3B,
                        0x53,
                        0x63,
                        0x73,
                        0x83,
                        0x9B,
                        0xBC,
                    ].index(context.emulator.read_bytes(0x0300185E, 1)[0])
                )
            y_val = int(context.emulator.read_bytes(0x0300185C, 1)[0] / 16) - 4
        return x_val, y_val


class BaseMenuNavigator:
    def __init__(self, step: str = "None"):
        self.navigator = None
        self.current_step = step

    def step(self):
        """
        Iterates through the steps of navigating the menu for the desired outcome.
        """
        while self.current_step != "exit":
            if not self.navigator:
                self.get_next_func()
                self.update_navigator()
            else:
                yield from self.navigator
                self.navigator = None

    def get_next_func(self):
        """
        Advances through the steps of navigating the menu.
        """
        ...

    def update_navigator(self):
        """
        Sets the navigator for the object to follow the steps for the desired outcome.
        """
        ...


class KeyboardNavigator(BaseMenuNavigator):
    def __init__(self, name: str, max_length: int = 8):
        super().__init__()
        if len(name) > max_length:
            name = name[:max_length]
        self.name = "".join([char if char in valid_characters else " " for char in name])
        self.h = key_layout[lang][0]["height"]
        self.w = key_layout[lang][0]["width"]
        self.keyboard = Keyboard()

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "Check keyboard status"
            case "Check keyboard status":
                self.current_step = "Wait for keyboard"
            case "Wait for keyboard":
                self.current_step = "Navigate keyboard"
            case "Navigate keyboard":
                self.current_step = "Release keys"
            case "Release keys":
                self.current_step = "Confirm name"
            case "Confirm name":
                self.current_step = "exit"
            case "Clear Input":
                self.current_step = "None"

    def update_navigator(self):
        match self.current_step:
            case "Check keyboard status":
                self.check_keyboard_status()
            case "Wait for keyboard":
                self.navigator = self.wait_for_keyboard()
            case "Navigate keyboard":
                self.navigator = self.navigate_keyboard()
            case "Release keys":
                self.navigator = self.release_keys()
            case "Confirm name":
                self.navigator = self.confirm_name()
            case "Clear Input":
                self.navigator = self.clear_input()

    def check_keyboard_status(self):
        if not self.keyboard.enabled:
            self.current_step = "exit"
            context.message = "Keyboard is not open"

    def wait_for_keyboard(self):
        while (
            self.keyboard.cur_pos[0] is None
            or (self.keyboard.cur_pos[0] > self.w and self.keyboard.cur_pos[1] > self.h)
            or len(self.keyboard.text_buffer) > 0
        ):
            context.emulator.press_button("B")
            yield

    def navigate_keyboard(self):
        last_pos = None
        cur_char = 0
        goto = [0, 0, 0]
        for page in range(len(key_layout[lang])):
            for num, row in enumerate(key_layout[lang][page]["array"]):
                if self.name[0] in row:
                    goto = [row.index(self.name[0]), num, page]
                    break
        while context.bot_mode != "Manual":
            page = self.keyboard.cur_page
            if page <= 3:
                if self.h != key_layout[lang][page]["height"] or self.w != key_layout[lang][page]["width"]:
                    self.h = key_layout[lang][page]["height"]
                    self.w = key_layout[lang][page]["width"]
                spot = self.keyboard.cur_pos
                if spot == last_pos or (last_pos is None and spot[0] <= self.w and spot[1] <= self.h):
                    if page != goto[2]:  # Press Select until on correct page
                        while page != goto[2]:
                            context.emulator.press_button("Select")
                            yield
                            page = self.keyboard.cur_page
                        last_pos = None
                    elif spot[0] == goto[0] and spot[1] == goto[1]:  # Press A if on correct character
                        last_pos = spot
                        while len(self.keyboard.text_buffer) < cur_char + 1:
                            context.emulator.press_button("A")
                            yield
                        cur_char += 1
                        if len(self.keyboard.text_buffer) >= len(self.name):
                            break
                        found = False
                        for num, row in enumerate(key_layout[lang][page]["array"]):
                            if self.name[cur_char] in row:
                                goto = [row.index(self.name[cur_char]), num, page]
                                found = True
                                break
                        if not found:
                            for page_num, new_page in enumerate(key_layout[lang]):
                                for num, row in enumerate(new_page["array"]):
                                    if self.name[cur_char] in row:
                                        goto = [row.index(self.name[cur_char]), num, page_num]
                                        found = True
                                        break
                                if found:
                                    break
                    else:
                        if spot[0] < goto[0]:
                            press = "Right"
                        elif spot[0] > goto[0]:
                            press = "Left"
                        elif (spot[1] < goto[1] or (spot[1] == self.h - 1 and goto[1] == 0)) and (
                            spot[1] != 0 or goto[1] != self.h - 1
                        ):
                            press = "Down"
                        else:
                            press = "Up"
                        context.emulator.press_button(press)
                        yield
                        yield
                        last_pos = None
                else:
                    last_pos = spot
                    yield
            else:
                yield

    def release_keys(self):
        context.emulator.release_button("A")
        context.emulator.release_button("Down")
        context.emulator.release_button("Up")
        context.emulator.release_button("Left")
        context.emulator.release_button("Right")
        context.emulator.release_button("Start")
        context.emulator.release_button("Select")
        yield

    def clear_input(self):
        while len(self.keyboard.text_buffer) > 0:
            context.emulator.press_button("B")
            yield

    def confirm_name(self):
        while self.keyboard.enabled:
            if (
                context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"] and self.keyboard.cur_pos[0] > self.w
            ) or (self.keyboard.cur_pos == (6, 0)):
                context.emulator.press_button("A")
            else:
                if self.keyboard.text_buffer == self.name:
                    context.emulator.press_button("Start")
                    yield
                    yield
                    yield
                    context.emulator.press_button("A")
                else:
                    self.navigator = None
                    self.current_step = "Clear Input"
                    break
            yield
