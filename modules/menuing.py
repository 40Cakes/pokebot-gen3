from enum import IntEnum
from typing import Generator

from modules.context import context
from modules.game_stats import get_game_stat, GameStat
from modules.items import Item, get_item_bag
from modules.memory import GameState, get_event_flag, get_game_state, read_symbol, unpack_uint16
from modules.menu_parsers import (
    CursorOptionEmerald,
    CursorOptionFRLG,
    CursorOptionRS,
    get_cursor_options,
    get_party_menu_cursor_pos,
    parse_menu,
    parse_party_menu,
    parse_start_menu,
)
from modules.modes._asserts import assert_has_pokemon_with_any_move
from modules.modes._interface import BotModeError
from modules.pokemon import get_move_by_name
from modules.pokemon_party import get_party, get_party_size
from modules.tasks import get_task, task_is_active


def is_fade_active() -> bool:
    return bool(read_symbol("gPaletteFade", offset=0x07, size=1)[0] & 0x80)


def party_menu_is_open() -> bool:
    """
    helper function to determine whether the Pokémon party menu is active

    :return: True if the party menu is active, false otherwise.
    """
    if not context.rom.is_rs:
        return get_game_state() == GameState.PARTY_MENU
    else:
        return (
            task_is_active("HANDLEDEFAULTPARTYMENU")
            or task_is_active("HANDLEPARTYMENUSWITCHPOKEMONINPUT")
            or task_is_active("HANDLEBATTLEPARTYMENU")
        )


def scroll_to_item_in_bag(item: Item) -> Generator:
    """
    This will select the correct bag pocket and scroll to the correct position therein.

    It will _not_ activate the item (pressing A) and it does _not_ open the bag menu.
    It is assumed that the bag menu is already open.

    :param item: Item to scroll to
    """

    def open_pocket_index() -> int:
        if context.rom.is_emerald:
            return read_symbol("gBagPosition", offset=0x05, size=1)[0]
        elif context.rom.is_rs:
            return read_symbol("sCurrentBagPocket")[0]
        else:
            return read_symbol("gBagMenuState", offset=0x06, size=1)[0]

    def currently_selected_slot() -> int:
        bag_index = open_pocket_index()
        if context.rom.is_emerald:
            cursor_position = unpack_uint16(read_symbol("gBagPosition", offset=8 + (bag_index * 2), size=2))
            scroll_position = unpack_uint16(read_symbol("gBagPosition", offset=18 + (bag_index * 2), size=2))
        elif context.rom.is_rs:
            cursor_position, scroll_position = read_symbol("gBagPocketScrollStates", offset=4 * bag_index, size=2)
        else:
            cursor_position = unpack_uint16(read_symbol("gBagMenuState", offset=8 + (bag_index * 2), size=2))
            scroll_position = unpack_uint16(read_symbol("gBagMenuState", offset=14 + (bag_index * 2), size=2))
        return cursor_position + scroll_position

    # Wait for fade-in to finish (happens when the bag is opened, during which time inputs
    # are not yet active.)
    while (
        get_game_state() != GameState.BAG_MENU
        or unpack_uint16(read_symbol("gPaletteFade", offset=0x07, size=0x02)) & 0x80 != 0
    ):
        yield

    # Select the correct pocket
    target_pocket_index = item.pocket.index
    while open_pocket_index() != target_pocket_index:
        if open_pocket_index() < target_pocket_index:
            context.emulator.press_button("Right")
        else:
            context.emulator.press_button("Left")
        for _ in range(26):
            yield

    # Scroll to the item
    slot_index = get_item_bag().first_slot_index_for(item)
    if slot_index is None:
        raise RuntimeError(f"Could not find any {item.name}")
    while currently_selected_slot() != slot_index:
        if currently_selected_slot() < slot_index:
            context.emulator.press_button("Down")
        else:
            context.emulator.press_button("Up")
        yield
        yield
        yield
        if context.rom.is_rs:
            yield


def scroll_to_party_menu_index(target_index: int) -> Generator:
    if get_party_size() <= target_index:
        raise RuntimeError(
            f"Cannot scroll to party index #{target_index} because the party only contains {get_party_size()} Pokémon."
        )

    # Wait for fade-in to finish (happens when the bag is opened, during which time inputs
    # are not yet active.)
    while (
        get_game_state() != GameState.PARTY_MENU
        or unpack_uint16(read_symbol("gPaletteFade", offset=0x07, size=0x02)) & 0x80 != 0
    ):
        yield

    while True:
        cursor = get_current_party_menu_index()

        if cursor == target_index:
            break
        elif cursor < target_index:
            context.emulator.press_button("Down")
        else:
            context.emulator.press_button("Up")
        yield
        yield


def get_current_party_menu_index():
    if context.rom.is_rs:
        cursor = context.emulator.read_bytes(0x0202002F + get_party_size() * 136 + 3, length=1)[0]
    else:
        party_menu = read_symbol("gPartyMenu")
        cursor = party_menu[9]

    return cursor


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
            if self.desired_option == "SAVE":
                break
            else:
                yield


class PokemonPartySubMenuNavigator(BaseMenuNavigator):
    def __init__(self, desired_option: str | int, item_to_give: Item | None = None):
        super().__init__()
        self.party_menu_internal = None
        self.update_party_menu()
        self.wait_counter = 0
        self.desired_option = desired_option
        self.item_to_give = item_to_give

    def update_party_menu(self):
        party_menu_internal = parse_party_menu()
        if self.party_menu_internal != party_menu_internal:
            self.party_menu_internal = party_menu_internal

    def wait_for_init(self):
        while self.party_menu_internal["numActions"] > 8:
            if self.wait_counter > 30:
                context.message = "Error navigating menu, switching to manual mode..."
                context.set_manual_mode()
            self.update_party_menu()
            self.wait_counter += 1
            yield

    def get_index_from_option(self) -> int:
        for i in range(self.party_menu_internal["numActions"]):
            if isinstance(self.desired_option, IntEnum):
                if self.party_menu_internal["actions"][i] == self.desired_option.value:
                    return i
            elif get_cursor_options(self.party_menu_internal["actions"][i]) == self.desired_option or (
                self.desired_option in ("SHIFT", "SWITCH", "SEND_OUT")
                and get_cursor_options(self.party_menu_internal["actions"][i]) in ("SEND_OUT", "SWITCH", "SHIFT")
            ):
                return i
        context.message = f"Couldn't find option {self.desired_option}, switching to manual mode..."
        context.set_manual_mode()

    def select_desired_option(self):
        if isinstance(self.desired_option, (str, IntEnum)):
            self.desired_option = self.get_index_from_option()
        if self.desired_option < 0 or self.desired_option > parse_menu()["maxCursorPos"]:
            context.message = f"Error selecting option {self.desired_option}, switching to manual mode..."
            context.set_manual_mode()
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

        if self.item_to_give is not None:
            while not task_is_active("Task_BagMenu_HandleInput") or get_task("Task_BagMenu_HandleInput").data[0] != 1:
                yield
            yield from scroll_to_item_in_bag(self.item_to_give)
            while not task_is_active("Task_PrintAndWaitForText"):
                context.emulator.press_button("A")
                yield
            while task_is_active("Task_PrintAndWaitForText"):
                context.emulator.press_button("A")
                yield
            for _ in range(5):
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
    def __init__(self, idx: int, mode: str, cursor_option: IntEnum | None = None, item_to_give: Item | None = None):
        super().__init__()
        self.idx = idx
        self.game = context.rom.game_title
        self.mode = mode
        if cursor_option is None:
            self.primary_option = None
            self.get_primary_option()
        else:
            self.primary_option = cursor_option
        self.item_to_give = item_to_give
        self.subnavigator = None
        self.party = get_party()

    def get_primary_option(self):
        if self.mode in ["take_item", "give_item"]:
            self.primary_option = "ITEM"
        if self.mode == "summary":
            self.primary_option = "SUMMARY"
        elif self.mode in ["switch", "select_switch"]:
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
                    case "summary":
                        self.current_step = "select_summary"
                    case _:
                        self.current_step = "exit"
            case "navigate_to_lead":
                self.current_step = "confirm_lead"
            case "select_take_item" | "select_give_item" | "confirm_lead" | "select_summary" | "select_switch":
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
            case "select_summary":
                self.navigator = self.select_summary()
            case "select_switch":
                self.navigator = self.select_switch()

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

    def select_summary(self):
        spam_a_button = True
        while not task_is_active("Task_DuckBGMForPokemonCry"):
            if spam_a_button:
                if task_is_active("Task_HandleInput") or task_is_active("SummaryScreenHandleKeyInput"):
                    spam_a_button = False
                else:
                    context.emulator.press_button("A")
            yield

    def select_mon(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            # This is required so that selecting the first party member doesn't fail.
            if not task_is_active("Task_HandleChooseMonInput"):
                while not task_is_active("Task_HandleChooseMonInput"):
                    yield
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
            while parse_party_menu()["numActions"] >= 3 and self.navigator is not None:
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(self.primary_option).step()
                else:
                    yield from self.subnavigator
                    self.navigator = None
                    self.subnavigator = None
        else:
            while task_is_active("SUB_8089D94") and not task_is_active("SUB_808A060"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(self.primary_option).step()
                else:
                    yield from self.subnavigator
                    self.navigator = None
                    self.subnavigator = None

    def select_switch(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while not task_is_active("Task_HandleSelectionMenuInput"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator("SHIFT").step()
                else:
                    yield from self.subnavigator
                    self.navigator = None
                    self.subnavigator = None
        else:
            while task_is_active("TASK_HANDLEPOPUPMENUINPUT"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(0).step()
                else:
                    yield from self.subnavigator
                    self.navigator = None
                    self.subnavigator = None

    def select_take_item(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_party()[self.idx].held_item is not None:
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator("TAKE_ITEM").step()
                else:
                    yield from self.subnavigator
                    self.navigator = None
                    self.subnavigator = None
        else:
            while task_is_active("SUB_808A060") or task_is_active("Task_PartyMenuPrintRun"):
                if not self.subnavigator:
                    self.subnavigator = PokemonPartySubMenuNavigator(1).step()
                else:
                    yield from self.subnavigator
                    self.navigator = None
                    self.subnavigator = None

    def select_give_item(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while get_party()[self.idx].held_item is None:
                yield from PokemonPartySubMenuNavigator("GIVE_ITEM", self.item_to_give).step()
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
        while task_is_active("Task_HandleChooseMonInput") or task_is_active("HANDLEBATTLEPARTYMENU"):
            context.emulator.press_button("A")
            yield

    def select_option(self):
        if self.game in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            while task_is_active("Task_HandleSelectionMenuInput"):
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()
        else:
            while task_is_active("TASK_HANDLEPOPUPMENUINPUT"):
                yield from PokemonPartySubMenuNavigator(self.primary_option).step()


def get_items_available_for_pickup() -> list[str]:
    if context.rom.is_rs:
        return [
            "Super Potion",
            "Ultra Ball",
            "Full Restore",
            "Full Heal",
            "Nugget",
            "Revive",
            "Rare Candy",
            "Protein",
            "PP Up",
            "King’s Rock",
        ]
    elif context.rom.is_frlg:
        return [
            "Oran Berry",
            "Aspear Berry",
            "Cheri Berry",
            "Chesto Berry",
            "Pecha Berry",
            "Persim Berry",
            "Rawst Berry",
            "Nugget",
            "PP Up",
            "Rare Candy",
            "TM10",
            "Belue Berry",
            "Durin Berry",
            "Pamtre Berry",
            "Spelon Berry",
            "Watmel Berry",
        ]
    else:
        return [
            "Potion",
            "Antidote",
            "Super Potion",
            "Great Ball",
            "Repel",
            "Escape Rope",
            "X Attack",
            "Full Heal",
            "Ultra Ball",
            "Hyper Potion",
            "Nugget",
            "King’s Rock",
            "Rare Candy",
            "Full Restore",
            "Ether",
            "Protein",
            "Revive",
            "White Herb",
            "HP Up",
            "TM44",
            "Elixir",
            "Max Revive",
            "TM01",
            "PP Up",
            "Leftovers",
            "Max Elixir",
            "TM26",
        ]


class CheckForPickup(BaseMenuNavigator):
    """
    class that handles pickup farming.
    """

    def __init__(self):
        super().__init__()

        self.possible_pickup_items = get_items_available_for_pickup()
        self.party = get_party()
        self.pokemon_with_pickup = 0
        self.pokemon_with_pickup_and_item = []
        self.picked_up_items = []
        self.current_mon = -1
        self.pickup_threshold_met = None
        self.check_threshold_met = False
        self.check_pickup_threshold()
        self.checked = False
        self.game = context.rom.game_title
        self.party_menu_opener = None
        self.party_menu_navigator = None

    def get_pokemon_with_pickup_and_item(self):
        for i, mon in enumerate(self.party):
            if mon.ability.name == "Pickup":
                self.pokemon_with_pickup += 1
                if mon.held_item is not None and mon.held_item.name in self.possible_pickup_items:
                    self.pokemon_with_pickup_and_item.append(i)
                    self.picked_up_items.append(mon.held_item)

    def check_pickup_threshold(self):
        if context.config.cheats.faster_pickup:
            self.check_threshold_met = True
            self.checked = True
        else:
            self.check_threshold_met = (
                get_game_stat(GameStat.TOTAL_BATTLES) % context.config.battle.pickup_check_frequency == 0
            )
        self.get_pokemon_with_pickup_and_item()
        if context.config.battle.pickup_threshold > self.pokemon_with_pickup > 0:
            threshold = self.pokemon_with_pickup
            context.message = (
                f"Number of pickup pokemon is {threshold}, which is lower than config. "
                f"Using party value of {threshold} instead."
            )
        else:
            threshold = context.config.battle.pickup_threshold
        self.pickup_threshold_met = self.check_threshold_met and len(self.pokemon_with_pickup_and_item) >= threshold
        if self.pickup_threshold_met:
            context.stats.log_pickup_items(self.picked_up_items)
            context.message = "Pickup threshold is met! Gathering items..."

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
            while task_is_active("Task_PrintAndWaitForText"):
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
        if (
            not context.config.cheats.faster_pickup
            and self.check_threshold_met
            and not self.checked
            and self.pokemon_with_pickup > 0
        ):
            return True
        elif self.pickup_threshold_met:
            return True
        else:
            return False

    def check_space_in_bag(self):
        if self.current_mon is not None:
            pokemon = self.party[self.current_mon]
            if not get_item_bag().has_space_for(pokemon.held_item):
                context.message = (
                    f"Item bag is full! {pokemon.species.name} (party slot #{self.current_mon + 1}) is holding a "
                    f"{pokemon.held_item.name} but there is no space left for it in the bag."
                )
                context.set_manual_mode()

    def get_next_func(self):
        match self.current_step:
            case "None":
                if self.should_open_party_menu():
                    self.current_step = "open_party_menu"
                else:
                    self.current_step = "exit"
            case "open_party_menu":
                self.checked = True
                if self.pickup_threshold_met and len(self.pokemon_with_pickup_and_item) > 0:
                    self.current_mon = self.pokemon_with_pickup_and_item[0]
                    self.check_space_in_bag()
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
            context.message = "I forgot how to count, switching to manual mode..."
            context.set_manual_mode()
        else:
            self.current_mon = self.pokemon_with_pickup_and_item[next_idx]
            self.check_space_in_bag()

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
                context.message = "Error exiting to overworld, switching to manual mode..."
                context.set_manual_mode()
            else:
                context.emulator.press_button("B")
                self.counter += 1
                yield


class MenuWrapper:
    def __init__(self, menu_handler: BaseMenuNavigator):
        self.menu_handler = menu_handler.step()

    def step(self):
        yield from self.menu_handler


def should_check_for_pickup():
    if not context.config.battle.pickup:
        return False

    if context.config.cheats.faster_pickup:
        pokemon_with_items_to_pick_up = 0
        items_available_for_pickup = get_items_available_for_pickup()
        for pokemon in get_party():
            if (
                pokemon.ability.name == "Pickup"
                and not pokemon.is_egg
                and pokemon.held_item is not None
                and pokemon.held_item.name in items_available_for_pickup
            ):
                pokemon_with_items_to_pick_up += 1
        if pokemon_with_items_to_pick_up >= context.config.battle.pickup_threshold:
            return True
    else:
        return get_game_stat(GameStat.TOTAL_BATTLES) % context.config.battle.pickup_check_frequency == 0


def use_party_hm_move(move_name: str):
    assert_has_pokemon_with_any_move([move_name], "No Pokémon with move {move_name} in party.")
    move_name_upper = move_name.upper()
    # badge checks
    if context.rom.is_rse:
        match move_name_upper:
            case "CUT":
                if not get_event_flag("BADGE01_GET"):
                    raise BotModeError("You do not have the Stone Badge to use Cut outside of battle.")
            case "FLASH":
                if not get_event_flag("BADGE02_GET"):
                    raise BotModeError("You do not have the Knuckle Badge to use Flash outside of battle.")
            case "ROCK SMASH":
                if not get_event_flag("BADGE03_GET"):
                    raise BotModeError("You do not have the Dynamo Badge to use Rock Smash outside of battle.")
            case "STRENGTH":
                if not get_event_flag("BADGE04_GET"):
                    raise BotModeError("You do not have the Heat Badge to use Strength outside of battle.")
            case "SURF":
                if not get_event_flag("BADGE05_GET"):
                    raise BotModeError("You do not have the Balance Badge to use Surf outside of battle.")
            case "FLY":
                if not get_event_flag("BADGE06_GET"):
                    raise BotModeError("You do not have the Feather Badge to use Fly outside of battle.")
            case "DIVE":
                if not get_event_flag("BADGE07_GET"):
                    raise BotModeError("You do not have the Mind Badge to use Dive outside of battle.")
            case "WATERFALL":
                if not get_event_flag("BADGE08_GET"):
                    raise BotModeError("You do not have the Rain Badge to use Waterfall outside of battle.")
            case _:
                raise BotModeError("Invalid HM move name.")
    if context.rom.is_frlg:
        match move_name_upper:
            case "FLASH":
                if not get_event_flag("BADGE01_GET"):
                    raise BotModeError("You do not have the Boulder Badge to use Flash outside of battle.")
            case "CUT":
                if not get_event_flag("BADGE02_GET"):
                    raise BotModeError("You do not have the Cascade Badge to use Cut outside of battle.")
            case "FLY":
                if not get_event_flag("BADGE03_GET"):
                    raise BotModeError("You do not have the Thunder Badge to use Fly outside of battle.")
            case "STRENGTH":
                if not get_event_flag("BADGE04_GET"):
                    raise BotModeError("You do not have the Rainbow Badge to use Strength outside of battle.")
            case "SURF":
                if not get_event_flag("BADGE05_GET"):
                    raise BotModeError("You do not have the Soul Badge to use Surf outside of battle.")
            case "ROCK SMASH":
                if not get_event_flag("BADGE06_GET"):
                    raise BotModeError("You do not have the Marsh Badge to use Rock Smash outside of battle.")
            case "WATERFALL":
                if not get_event_flag("BADGE07_GET"):
                    raise BotModeError("You do not have the Volcano Badge to use Waterfall outside of battle.")
            case _:
                raise BotModeError("Invalid HM move name.")

    yield from StartMenuNavigator("POKEMON").step()

    # find Pokémon with desired HM move
    move_wanted = get_move_by_name(move_name)
    move_pokemon = get_party().first_pokemon_with_move(move_wanted)
    if move_pokemon is None:
        raise RuntimeError(f"Could not find a Pokémon that knows {move_wanted.name}.")

    cursor = None
    if context.rom.is_emerald:
        cursor = CursorOptionEmerald
    elif context.rom.is_rs:
        cursor = CursorOptionRS
    elif context.rom.is_frlg:
        cursor = CursorOptionFRLG

    match move_name_upper:
        case "CUT":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.CUT).step()
        case "FLY":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.FLY).step()
        case "SURF":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.SURF).step()
        case "STRENGTH":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.STRENGTH).step()
        case "FLASH":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.FLASH).step()
        case "ROCK SMASH":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.ROCK_SMASH).step()
        case "WATERFALL":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.WATERFALL).step()
        case "DIVE":
            yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.DIVE).step()
        case _:
            raise BotModeError("Invalid HM move name.")
    return


class RotatePokemon(BaseMenuNavigator):
    def __init__(self, first_party_index: int, second_party_index: int = 0):
        super().__init__()
        self.party = get_party()

        if first_party_index >= len(self.party):
            raise RuntimeError(
                f"Cannot rotate Pokémon #{first_party_index} because the party only has {len(self.party)} Pokémon."
            )

        if second_party_index >= len(self.party):
            raise RuntimeError(
                f"Cannot rotate Pokémon #{second_party_index} because the party only has {len(self.party)} Pokémon."
            )

        if first_party_index == second_party_index:
            raise RuntimeError(f"Cannot rotate Pokémon #{first_party_index} with itself.")

        self._first_party_index = first_party_index
        self._second_party_index = second_party_index

    def get_next_func(self):
        match self.current_step:
            case "None":
                match self._first_party_index:
                    case None:
                        self.current_step = "exit"
                    case _:
                        self.current_step = "open_party_menu"
            case "open_party_menu":
                self.current_step = "select_first_pokemon"
            case "select_first_pokemon":
                self.current_step = "select_second_pokemon"
            case "select_second_pokemon":
                self.current_step = "exit_to_overworld"
            case "exit_to_overworld":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "open_party_menu":
                self.navigator = StartMenuNavigator("POKEMON").step()
            case "select_first_pokemon":
                self.navigator = PokemonPartyMenuNavigator(idx=self._first_party_index, mode="select_switch").step()
            case "select_second_pokemon":
                self.navigator = self.select_replacement()
            case "exit_to_overworld":
                self.navigator = PartyMenuExit().step()

    def select_replacement(self):
        while get_party_menu_cursor_pos(len(self.party))["slot_id_2"] != self._second_party_index:
            if get_party_menu_cursor_pos(len(self.party))["slot_id_2"] > self._second_party_index:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("Down")
            yield

        while not task_is_active("Task_SlideSelectedSlotsOnscreen") and not task_is_active("sub_806D198"):
            context.emulator.press_button("A")
            yield
        while task_is_active("Task_SlideSelectedSlotsOnscreen") or task_is_active("sub_806D198"):
            yield
