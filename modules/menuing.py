from modules.context import context
from modules.memory import get_game_state, GameState
from modules.menu_parsers import (
    parse_start_menu,
    parse_party_menu,
    get_cursor_options,
    parse_menu,
    get_party_menu_cursor_pos,
)
from modules.pokemon import get_party
from modules.tasks import task_is_active

config = context.config


def party_menu_is_open() -> bool:
    """
    helper function to determine whether the Pokémon party menu is active

    :return: True if the party menu is active, false otherwise.
    """
    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        return get_game_state() == GameState.PARTY_MENU
    else:
        return (
            task_is_active("HANDLEDEFAULTPARTYMENU")
            or task_is_active("HANDLEPARTYMENUSWITCHPOKEMONINPUT")
            or task_is_active("HANDLEBATTLEPARTYMENU")
        )


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

    def confirm_desired_option(self):
        while self.wait_counter < 5:
            if self.wait_counter == 1:
                context.emulator.press_button("A")
            self.wait_counter += 1
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
                self.wait_counter = 0
                self.navigator = self.confirm_desired_option()


class PokemonPartyMenuNavigator(BaseMenuNavigator):
    def __init__(self, idx: int, mode: str):
        super().__init__()
        self.idx = idx
        self.game = context.rom.game_title
        self.mode = mode
        self.primary_option = None
        self.get_primary_option()
        self.subnavigator = None
        self.party = get_party()

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
                        self.current_step = "navigate_to_lead"
                    case _:
                        self.current_step = "exit"
            case "navigate_to_lead":
                self.current_step = "confirm_lead"
            case "select_take_item" | "select_give_item" | "confirm_lead":
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
            case "navigate_to_lead":
                self.navigator = self.navigate_to_lead()
            case "confirm_lead":
                self.navigator = self.switch_mon()

    def navigate_to_mon(self):
        while get_party_menu_cursor_pos(len(self.party))["slot_id"] != self.idx:
            if get_party_menu_cursor_pos(len(self.party))["slot_id"] > self.idx:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("Down")
            yield

    def navigate_to_lead(self):
        while get_party_menu_cursor_pos(len(self.party))["slot_id_2"] != 0:
            context.emulator.press_button("Left")
            yield

    def select_mon(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while task_is_active("TASK_HANDLECHOOSEMONINPUT"):
                context.emulator.press_button("A")
                yield
        else:
            while not task_is_active("SUB_8089D94"):
                context.emulator.press_button("A")
                yield

    @staticmethod
    def switch_mon():
        while task_is_active("TASK_HANDLECHOOSEMONINPUT") or task_is_active("HANDLEPARTYMENUSWITCHPOKEMONINPUT"):
            context.emulator.press_button("A")
            yield

    def select_option(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while parse_party_menu()["numActions"] > 3 and self.navigator is not None:
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(self.primary_option).step()
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.navigator = None
                    self.subnavigator = None
        else:
            while task_is_active("SUB_8089D94") and not task_is_active("SUB_808A060"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(self.primary_option).step()
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.navigator = None
                    self.subnavigator = None

    def select_switch(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while not task_is_active("TASK_HANDLESELECTIONMENUINPUT"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator("SHIFT").step()
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.navigator = None
                    self.subnavigator = None
        else:
            while task_is_active("TASK_HANDLEPOPUPMENUINPUT"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(0).step()
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.navigator = None
                    self.subnavigator = None

    def select_take_item(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_party()[self.idx].held_item is not None:
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator("TAKE_ITEM").step()
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.navigator = None
                    self.subnavigator = None
        else:
            while task_is_active("SUB_808A060"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(1).step()
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.navigator = None
                    self.subnavigator = None

    def select_give_item(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_party()[self.idx].held_item is None:
                yield from PokemonPartySubMenuNavigator("GIVE_ITEM").step()
        else:
            while task_is_active("SUB_808A060"):
                yield from PokemonPartySubMenuNavigator(0).step()


class BattlePartyMenuNavigator(PokemonPartyMenuNavigator):
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
                    case _:
                        self.current_step = "exit"
            case "navigate_to_lead":
                self.current_step = "confirm_lead"
            case "select_take_item" | "select_give_item" | "confirm_lead":
                self.current_step = "exit"

    def select_mon(self):
        while task_is_active("TASK_HANDLECHOOSEMONINPUT") or task_is_active("HANDLEBATTLEPARTYMENU"):
            context.emulator.press_button("A")
            yield

    def select_option(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while task_is_active("TASK_HANDLESELECTIONMENUINPUT"):
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()
        else:
            while task_is_active("TASK_HANDLEPOPUPMENUINPUT"):
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()


class CheckForPickup(BaseMenuNavigator):
    """
    class that handles pickup farming.
    """

    def __init__(self, encounter_total: int):
        super().__init__()
        self.party = get_party()
        self.pokemon_with_pickup = 0
        self.pokemon_with_pickup_and_item = []
        self.current_mon = -1
        self.pickup_threshold_met = None
        self.check_threshold_met = False
        self.check_pickup_threshold(encounter_total)
        self.checked = False
        self.game = context.rom.game_title
        self.party_menu_opener = None
        self.party_menu_navigator = None

    def get_pokemon_with_pickup_and_item(self):
        for i, mon in enumerate(self.party):
            if mon.ability.name == "Pickup":
                self.pokemon_with_pickup += 1
                if mon.held_item is not None:
                    self.pokemon_with_pickup_and_item.append(i)

    def check_pickup_threshold(self, encounter_total):
        if config.cheats.pickup:
            self.check_threshold_met = True
            self.checked = True
        else:
            self.check_threshold_met = encounter_total >= config.battle.pickup_check_frequency
        self.get_pokemon_with_pickup_and_item()
        if config.battle.pickup_threshold > self.pokemon_with_pickup > 0:
            threshold = self.pokemon_with_pickup
            context.message = f"Number of pickup pokemon is {threshold}, which is lower than config. Using\nparty value of {threshold} instead."
        else:
            threshold = config.battle.pickup_threshold
        self.pickup_threshold_met = self.check_threshold_met and len(self.pokemon_with_pickup_and_item) >= threshold
        if self.pickup_threshold_met:
            context.message = "Pickup threshold is met! Gathering items."

    def open_party_menu(self):
        while not party_menu_is_open():
            if self.party_menu_opener is None:
                self.party_menu_opener = StartMenuNavigator("POKEMON")
            if self.party_menu_opener.current_step != "exit":
                yield from self.party_menu_opener.step()
            else:
                context.emulator.press_button("A")
                yield

    def return_to_party_menu(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while task_is_active("TASK_PRINTANDWAITFORTEXT"):
                context.emulator.press_button("B")
                yield
        else:
            while (
                task_is_active("HANDLEDEFAULTPARTYMENU")
                and task_is_active("HANDLEPARTYMENUSWITCHPOKEMONINPUT")
                and task_is_active("HANDLEBATTLEPARTYMENU")
            ):
                context.emulator.press_button("B")
                yield

    def should_open_party_menu(self):
        if not config.cheats.pickup and self.check_threshold_met and not self.checked and self.pokemon_with_pickup > 0:
            return True
        elif self.pickup_threshold_met:
            return True
        else:
            return False

    def get_next_func(self):
        match self.current_step:
            case "None":
                if self.should_open_party_menu():
                    self.current_step = "open_party_menu"
                else:
                    self.current_step = "exit"
            case "open_party_menu":
                self.checked = True
                if self.pickup_threshold_met:
                    self.current_mon = self.pokemon_with_pickup_and_item[0]
                    self.current_step = "take_mon_item"
                else:
                    self.current_step = "exit_to_overworld"
            case "take_mon_item":
                self.current_step = "return_to_party_menu"
            case "return_to_party_menu":
                if self.current_mon == self.pokemon_with_pickup_and_item[-1]:
                    self.current_step = "exit_to_overworld"
                else:
                    self.get_next_mon()
                    self.current_step = "take_mon_item"
            case "exit_to_overworld":
                self.current_step = "exit"

    def get_next_mon(self):
        next_idx = self.pokemon_with_pickup_and_item.index(self.current_mon) + 1
        if next_idx > len(self.pokemon_with_pickup_and_item) - 1:
            context.message = "I forgot how to count. Switching to manual mode."
            context.bot_mode = "Manual"
        else:
            self.current_mon = self.pokemon_with_pickup_and_item[next_idx]

    def update_navigator(self):
        match self.current_step:
            case "open_party_menu":
                self.navigator = self.open_party_menu()
            case "take_mon_item":
                self.navigator = PokemonPartyMenuNavigator(idx=self.current_mon, mode="take_item").step()
            case "return_to_party_menu":
                self.navigator = self.return_to_party_menu()
            case "exit_to_overworld":
                self.navigator = PartyMenuExit().step()


class PartyMenuExit(BaseMenuNavigator):
    def __init__(self):
        super().__init__()
        self.counter = 0

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "exit_party_menu"
            case "exit_party_menu":
                self.current_step = "wait_for_start_menu"
            case "wait_for_start_menu":
                self.current_step = "exit_start_menu"
            case "exit_start_menu":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "exit_party_menu" | "exit_start_menu":
                self.navigator = self.exit_menu()
            case "wait_for_start_menu":
                self.navigator = self.wait_for_start_menu()

    @staticmethod
    def exit_menu():
        while get_game_state() != GameState.OVERWORLD or parse_start_menu()["open"]:
            context.emulator.press_button("B")
            yield

    def wait_for_start_menu(self):
        while get_game_state() == GameState.OVERWORLD and not parse_start_menu()["open"]:
            if self.counter > 60:
                context.message = "Error exiting to overworld. Switching to manual mode."
                context.bot_mode = "Manual"
            else:
                context.emulator.press_button("B")
                self.counter += 1
                yield


class MenuWrapper:
    def __init__(self, menu_handler: BaseMenuNavigator):
        self.menu_handler = menu_handler.step()

    def step(self):
        for _ in self.menu_handler:
            yield _


def should_check_for_pickup(x: int):
    if config.cheats.pickup or x >= config.battle.pickup_check_frequency:
        return True
    return False
