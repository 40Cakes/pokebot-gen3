import json
from dataclasses import dataclass
from enum import Enum
from typing import Generator

from modules.context import context
from modules.debug import debug
from modules.game import decode_string
from modules.game_sprites import get_game_sprite_by_id
from modules.memory import read_symbol, unpack_uint32, get_game_state, GameState
from modules.modes import BotModeError
from modules.roms import ROMLanguage
from modules.runtime import get_data_path
from modules.tasks import get_task


class KeyboardLayout:
    def __init__(self, data: dict):
        self.pages: tuple[KeyboardPage, KeyboardPage, KeyboardPage] = (
            KeyboardPage.from_data(data[2]),
            KeyboardPage.from_data(data[0]),
            KeyboardPage.from_data(data[1]),
        )

    @property
    def valid_characters(self) -> list[str]:
        valid_characters = []
        for page in self.pages:
            valid_characters.extend(page.characters)
        return valid_characters

    def strip_invalid_characters(self, name: str) -> str:
        valid_characters = self.valid_characters
        return "".join([char if char in valid_characters else " " for char in name])


@dataclass
class KeyboardPage:
    width: int
    height: int
    rows: tuple[list[str], list[str], list[str], list[str]]

    @classmethod
    def from_data(cls, data: dict) -> "KeyboardPage":
        return KeyboardPage(
            width=data["width"],
            height=data["height"],
            rows=(
                data["array"][0],
                data["array"][1],
                data["array"][2],
                data["array"][3],
            ),
        )

    @property
    def characters(self) -> list[str]:
        return [*self.rows[0], *self.rows[1], *self.rows[2], *self.rows[3]]

    def character_position(self, character: str) -> tuple[int, int]:
        for row_index, characters in enumerate(self.rows):
            if character in characters:
                return characters.index(character), row_index
        return 0, 0


with open(get_data_path() / "keyboard.json", "r", encoding="utf-8") as f:
    _raw_keyboard_layouts: dict[str, dict] = json.load(f)

keyboard_layouts: dict[str, KeyboardLayout] = {}
for language_code in _raw_keyboard_layouts:
    keyboard_layouts[language_code] = KeyboardLayout(_raw_keyboard_layouts[language_code])


def get_current_keyboard_layout() -> KeyboardLayout:
    if context.rom is None or context.rom.language.value not in keyboard_layouts:
        return keyboard_layouts["E"]
    else:
        return keyboard_layouts[context.rom.language.value]


class KeyboardPageType(Enum):
    DigitsAndSymbols = 0
    Uppercase = 1
    Lowercase = 2


class NamingScreenState(Enum):
    FadeIn = 0
    WaitForFadeIn = 1
    HandleInput = 2
    MoveToOKButton = 3
    PageSwap = 4
    WaitForPageSwap = 5
    PressedOK = 6
    WaitForSentToPCMessage = 7
    FadeOut = 8
    Exit = 9


@dataclass
class NamingScreen:
    enabled: bool
    state: NamingScreenState
    current_input: str
    keyboard_page: KeyboardPageType
    cursor_position: tuple[int, int]


def get_naming_screen_data() -> NamingScreen | None:
    task = get_task("Task_HandleInput")
    if task is None:
        return None

    if context.rom.is_rs:
        pointer = unpack_uint32(read_symbol("namingScreenDataPtr"))
        if pointer == 0:
            return None
        data = context.emulator.read_bytes(pointer, 0x4A)
        cursor_sprite = get_game_sprite_by_id(data[0x0F])
        language_offset = 0 if context.rom.language == ROMLanguage.Japanese else 1

        return NamingScreen(
            enabled=bool(task.data_value(0)),
            state=NamingScreenState(data[0x00]),
            current_input=decode_string(data[0x11:0x21]),
            keyboard_page=KeyboardPageType((data[0x0E] + language_offset) % 3),
            cursor_position=(cursor_sprite.data_value(0), cursor_sprite.data_value(1)),
        )
    else:
        pointer = unpack_uint32(read_symbol("sNamingScreen"))
        if pointer == 0:
            return None
        data = context.emulator.read_bytes(pointer + 0x1E10, 0x14)
        cursor_sprite = get_game_sprite_by_id(data[0x1E23 - 0x1E10])
        return NamingScreen(
            enabled=bool(task.data_value(0)),
            state=NamingScreenState(data[0]),
            current_input=decode_string(context.emulator.read_bytes(pointer + 0x1800, length=16)),
            keyboard_page=KeyboardPageType(data[0x1E22 - 0x1E10]),
            cursor_position=(cursor_sprite.data_value(0), cursor_sprite.data_value(1)),
        )


@debug.track
def type_in_naming_screen(name: str, max_length: int = 8):
    """
    This will type a given string into the in-game keyboard.
    It expects the Naming Screen to be active.

    :param name: String to enter into the keyboard.
    :param max_length: Maximum length that is supported at this point.
    """

    layout = get_current_keyboard_layout()
    name = layout.strip_invalid_characters(name)[:max_length]

    while True:
        naming_screen = get_naming_screen_data()
        if naming_screen is None:
            raise BotModeError("The naming screen keyboard is not active.")

        if not naming_screen.enabled or naming_screen.state != NamingScreenState.HandleInput:
            yield
            continue

        current_page: KeyboardPage = layout.pages[naming_screen.keyboard_page.value]

        # Input exactly matched the name -> confirm
        if naming_screen.current_input == name:
            # Wait for cursor to get to the 'OK' button
            if naming_screen.cursor_position != (current_page.width, 2):
                context.emulator.press_button("Start")
                yield
                continue

            # Spam 'A' until the naming screen is no longer active
            while get_naming_screen_data() is not None or get_game_state() is GameState.NAMING_SCREEN:
                context.emulator.press_button("A")
                yield

            return

        # If the current input does not match the name, delete the last character and try again.
        if not name.startswith(naming_screen.current_input):
            context.emulator.press_button("B")
            yield
            continue

        next_character = name[len(naming_screen.current_input)]

        # If the next character is not on the current page, switch pages.
        if next_character not in current_page.characters:
            context.emulator.press_button("Select")
            yield
            continue

        character_position = current_page.character_position(next_character)

        # Move to the correct column
        if character_position[0] != naming_screen.cursor_position[0]:
            distance = abs(character_position[0] - naming_screen.cursor_position[0])
            if character_position[0] > naming_screen.cursor_position[0]:
                context.emulator.press_button("Right" if distance <= (current_page.width + 1) // 2 else "Left")
            else:
                context.emulator.press_button("Left" if distance <= (current_page.width + 1) // 2 else "Right")
            yield
            continue

        # Move to the correct row
        if character_position[1] != naming_screen.cursor_position[1]:
            distance = abs(character_position[1] - naming_screen.cursor_position[1])
            if character_position[1] > naming_screen.cursor_position[1]:
                context.emulator.press_button("Down" if distance <= current_page.height // 2 else "Up")
            else:
                context.emulator.press_button("Up" if distance <= current_page.height // 2 else "Down")
            yield
            continue

        # We have reached the correct character -> press A to confirm
        context.emulator.press_button("A")
        yield


@debug.track
def handle_naming_screen(nickname_choice: str) -> Generator:
    # Wait for the naming dialogue to appear (i.e. skip the 'Do you want to give a nickname
    # to X' dialogue.)
    while get_game_state() != GameState.NAMING_SCREEN:
        context.emulator.press_button("A")
        yield

    # Wait for the keyboard to become usable (skips the fade-in of the naming menu)
    while get_naming_screen_data() is None:
        yield

    # Enter the name.
    max_pokemon_name_length = 10 if context.rom.language is not ROMLanguage.Japanese else 5
    yield from type_in_naming_screen(nickname_choice, max_pokemon_name_length)
