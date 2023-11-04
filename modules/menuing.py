from modules.context import context
from modules.memory import get_game_state, GameState, get_task
from modules.menu_parsers import (
    parse_start_menu,
    parse_party_menu,
    get_cursor_options,
    parse_menu,
    get_party_menu_cursor_pos,
)
from modules.pokemon import get_party


class MenuWrapper:

    def __init__(self, menu_handler: object):
        self.menu_handler = menu_handler.step()

    def step(self):
        while True:
            yield from self.menu_handler


def party_menu_is_open() -> bool:
    """
    helper function to determine whether the Pokémon party menu is active

    :return: True if the party menu is active, false otherwise.
    """
    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        return get_game_state() == GameState.PARTY_MENU
    else:
        return (
            get_task("HANDLEDEFAULTPARTYMENU") != {}
            or get_task("HANDLEPARTYMENUSWITCHPOKEMONINPUT") != {}
            or get_task("HANDLEBATTLEPARTYMENU") != {}
        )


def switch_pokemon_active() -> bool:
    """
    helper function to determine if the Pokémon party menu is currently ready to switch the places of two Pokémon.

    :return: True if the Pokémon party menu is ready to switch two Pokémon, false otherwise.
    """
    task = get_task("HANDLEPARTYMENUSWITCHPOKEMONINPUT")
    if task != {} and task["isActive"]:
        return True
    else:
        return False


class BaseMenuNavigator:
    def __init__(self, step: str = "None"):
        self.navigator = None
        self.current_step = step

    def step(self):
        """
        Iterates through the steps of navigating the menu for the desired outcome.
        """
        while not self.current_step == "exit":
            if not self.navigator:
                self.get_next_func()
                self.update_navigator()
            else:
                for _ in self.navigator:
                    yield _
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


class StartMenuNavigator(BaseMenuNavigator):
    """
    Opens the start menu and moves to the option with the desired index from the menu.

    :param desired_option: The option to select from the menu.
    """

    def __init__(self, desired_option: str):
        super().__init__()
        self.desired_option = desired_option
        self.start_menu = parse_start_menu()

    def update_start_menu(self):
        self.start_menu = parse_start_menu()

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "open_start_menu"
            case "open_start_menu":
                self.current_step = "navigate_to_option"
            case "navigate_to_option":
                self.current_step = "confirm_option"
            case "confirm_option":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "open_start_menu":
                self.navigator = self.open_start_menu()
            case "navigate_to_option":
                self.navigator = self.navigate_to_option()
            case "confirm_option":
                self.navigator = self.confirm_option()

    def open_start_menu(self):
        while not self.start_menu["open"]:
            self.update_start_menu()
            context.emulator.press_button("Start")
            yield

    def navigate_to_option(self):
        while self.start_menu["cursor_pos"] != self.start_menu["actions"].index(self.desired_option):
            self.update_start_menu()
            if self.start_menu["cursor_pos"] == self.start_menu["actions"].index(self.desired_option):
                up_presses = 0
                down_presses = 0
            elif self.start_menu["cursor_pos"] < self.start_menu["actions"].index(self.desired_option):
                up_presses = (
                    self.start_menu["cursor_pos"]
                    + len(self.start_menu["actions"])
                    - self.start_menu["actions"].index(self.desired_option)
                )
                down_presses = self.start_menu["actions"].index(self.desired_option) - self.start_menu["cursor_pos"]
            else:
                up_presses = self.start_menu["cursor_pos"] - self.start_menu["actions"].index(self.desired_option)
                down_presses = (
                    self.start_menu["actions"].index(self.desired_option)
                    - self.start_menu["cursor_pos"]
                    + len(self.start_menu["actions"])
                )
            if down_presses > up_presses:
                context.emulator.press_button("Up")
            elif up_presses > down_presses or (up_presses > 0 or down_presses > 0):
                context.emulator.press_button("Down")
            yield

    def confirm_option(self):
        while self.start_menu["open"]:
            self.update_start_menu()
            context.emulator.press_button("A")
            yield


class PokemonPartySubMenuNavigator(BaseMenuNavigator):
    def __init__(self, desired_option: str | int):
        super().__init__()
        self.party_menu_internal = None
        self.update_party_menu()
        self.wait_counter = 0
        self.desired_option = desired_option

    def update_party_menu(self):
        party_menu_internal = parse_party_menu()
        if self.party_menu_internal != party_menu_internal:
            self.party_menu_internal = party_menu_internal

    def wait_for_init(self):
        while self.party_menu_internal["numActions"] > 8:
            if self.wait_counter > 30:
                context.message = "Error navigating menu. Manual mode is now on."
                context.bot_mode = "Manual"
            self.update_party_menu()
            self.wait_counter += 1
            yield

    def get_index_from_option(self) -> int:
        for i in range(self.party_menu_internal["numActions"]):
            if get_cursor_options(self.party_menu_internal["actions"][i]) == self.desired_option or (
                self.desired_option in ("SHIFT", "SWITCH", "SEND_OUT")
                and get_cursor_options(self.party_menu_internal["actions"][i]) in ("SEND_OUT", "SWITCH", "SHIFT")
            ):
                return i
        context.message = f"Couldn't find option {self.desired_option}. Switching to manual mode."
        context.bot_mode = "Manual"

    def select_desired_option(self):
        if isinstance(self.desired_option, str):
            self.desired_option = self.get_index_from_option()
        if self.desired_option < 0 or self.desired_option > parse_menu()["maxCursorPos"]:
            context.message = f"Error selecting option {self.desired_option}. Switching to manual mode."
            context.bot_mode = "Manual"
        while parse_menu()["cursorPos"] != self.desired_option:
            if parse_menu()["cursorPos"] < self.desired_option:
                up_presses = parse_menu()["cursorPos"] + self.party_menu_internal["numActions"] - self.desired_option
                down_presses = self.desired_option - parse_menu()["cursorPos"]
            else:
                up_presses = parse_menu()["cursorPos"] - self.desired_option
                down_presses = self.desired_option - parse_menu()["cursorPos"] + self.party_menu_internal["numActions"]
            if down_presses > up_presses:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("Down")
            yield

    @staticmethod
    def confirm_desired_option():
        context.emulator.press_button("A")
        yield

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "wait_for_init"
            case "wait_for_init":
                self.current_step = "navigate_to_option"
            case "navigate_to_option":
                self.current_step = "confirm_option"
            case "confirm_option":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "wait_for_init":
                self.navigator = self.wait_for_init()
            case "navigate_to_option":
                self.navigator = self.select_desired_option()
            case "confirm_option":
                self.navigator = self.confirm_desired_option()


class PokemonPartyMenuNavigator(BaseMenuNavigator):
    def __init__(self, idx: int, mode: str):
        super().__init__()
        self.idx = idx
        self.game = context.rom.game_title
        self.mode = mode
        self.primary_option = None
        self.get_primary_option()

    def get_primary_option(self):
        if self.mode in ["take_item", "give_item"]:
            self.primary_option = "ITEM"
        if self.mode == "switch":
            self.primary_option = "SWITCH"

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "navigate_to_mon"
            case "navigate_to_mon":
                self.current_step = "select_mon"
            case "select_mon":
                self.current_step = "select_option"
            case "select_option":
                match self.mode:
                    case "take_item":
                        self.current_step = "select_take_item"
                    case "give_item":
                        self.current_step = "select_give_item"
                    case "switch":
                        self.current_step = "select_switch"
                    case _:
                        self.current_step = "exit"
            case "select_take_item" | "select_give_item" | "select_switch":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "navigate_to_mon":
                self.navigator = self.navigate_to_mon()
            case "select_mon":
                self.navigator = self.select_mon()
            case "select_option":
                self.navigator = self.select_option()
            case "select_take_item":
                self.navigator = self.select_take_item()
            case "select_give_item":
                self.navigator = self.select_give_item()

    def navigate_to_mon(self):
        while get_party_menu_cursor_pos()["slot_id"] != self.idx:
            if get_party_menu_cursor_pos()["slot_id"] > self.idx:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("Down")
            yield

    def select_mon(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_task("TASK_HANDLESELECTIONMENUINPUT") == {}:
                context.emulator.press_button("A")
                yield
        else:
            while get_task("SUB_8089D94") == {}:
                context.emulator.press_button("A")
                yield

    def select_option(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while parse_party_menu()["numActions"] > 3:
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()
        else:
            while get_task("SUB_8089D94") != {} and get_task("SUB_808A060") == {}:
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()

    def select_shift(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_task("TASK_HANDLESELECTIONMENUINPUT") != {}:
                yield from PokemonPartySubMenuNavigator("SHIFT").step()
        else:
            while get_task("TASK_HANDLEPOPUPMENUINPUT") != {}:
                yield from PokemonPartySubMenuNavigator(0).step()

    def select_take_item(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_party()[self.idx].held_item.name != "None":
                yield from PokemonPartySubMenuNavigator("TAKE_ITEM").step()
        else:
            while get_task("SUB_808A060") != {}:
                yield from PokemonPartySubMenuNavigator(1).step()

    def select_give_item(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_party()[self.idx].held_item.name == "None":
                yield from PokemonPartySubMenuNavigator("GIVE_ITEM").step()
        else:
            while get_task("SUB_808A060") != {}:
                yield from PokemonPartySubMenuNavigator(0).step()


class BattlePartyMenuNavigator(PokemonPartyMenuNavigator):
    def select_option(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_task("TASK_HANDLESELECTIONMENUINPUT") != {}:
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()
        else:
            while get_task("TASK_HANDLEPOPUPMENUINPUT") != {}:
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()
