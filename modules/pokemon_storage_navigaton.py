from modules.context import context
from modules.memory import read_symbol, unpack_uint32
from modules.menuing import BaseMenuNavigator
from modules.tasks import get_task, task_is_active

PokeInBoxOptions = ["MOVE", "SUMMARY", "WITHDRAW", "MARK", "RELEASE", "CANCEL"]

PCPokeOptions = ["WITHDRAW_POKEMON", "DEPOSIT_POKEMON", "MOVE_POKEMON", "MOVE_ITEMS"]

# Not implemented yet
PCOptions = ["POKE_PC", "ITEM_PC", "HALL_OF_FAME_PC", "EXIT"]

BoxOptions = ["JUMP", "WALLPAPER", "NAME", "CANCEL"]


def pc_slot_from_number(slot: int) -> tuple[int, int]:
    """
    Returns the x and y for a given slot in the PC.
    Slot number must be between 0 and 29.
    """
    if slot > 29:
        raise ValueError("Slot must be between 0 and 29")
    return slot % 6, slot // 6


class PCMainMenuNavigator(BaseMenuNavigator):
    def __init__(self, desired_option: str):
        super().__init__()
        if desired_option.upper() not in PCPokeOptions:
            raise ValueError(f"Option not in PC Main Menu, options are {PCPokeOptions}")
        self.desired_option = desired_option.upper()
        self.cursor = StorageCursor()
        self.wait_counter = 0
        match context.rom.game_title:
            case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
                self.pc_task = "Task_PCMainMenu"
            case "POKEMON RUBY" | "POKEMON SAPP":
                self.pc_task = "Task_PokemonStorageSystem"
            case _:
                raise ValueError("Game not supported")
        self.current_step = None

    def get_next_func(self):
        match self.current_step:
            case None:
                self.current_step = "wait_for_pc"
            case "wait_for_pc":
                self.current_step = "navigate_to_option"
            case "navigate_to_option":
                self.current_step = "confirm_option"
            case "confirm_option":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "wait_for_pc":
                self.navigator = self.wait_for_pc()
            case "navigate_to_option":
                self.navigator = self.navigate_to_option()
            case "confirm_option":
                self.navigator = self.confirm_option()

    def wait_for_pc(self):
        while not task_is_active(self.pc_task) and self.wait_counter < 20:
            self.wait_counter += 1
            yield
        if self.wait_counter >= 20:
            raise ValueError("PC did not open")
        self.wait_counter = 0

    def navigate_to_option(self):
        while get_task(self.pc_task).data[2] != PCPokeOptions.index(self.desired_option):
            context.emulator.press_button("Down")
            yield

    def confirm_option(self):
        while task_is_active(self.pc_task):
            context.emulator.press_button("A")
            yield


class MenuNavigator(BaseMenuNavigator):
    def __init__(self, desired_option: str, menu: list):
        super().__init__()
        if desired_option in menu:
            self.desired_option = desired_option
            self.menu = menu
            self.cursor = StorageCursor()
            self.wait_counter = 0
        else:
            raise ValueError("Option not in given menu")
        self.current_step = None

    def get_next_func(self):
        match self.current_step, self.desired_option:
            case None, _:
                self.current_step = "wait_for_menu"
            case "wait_for_menu", "YES":
                self.current_step = "select_yes"
            case "wait_for_menu", _:
                self.current_step = "navigate_to_option"
            case "select_yes", _:
                self.current_step = "exit"
            case "navigate_to_option", _:
                self.current_step = "confirm_option"
            case "confirm_option", "RELEASE":
                self.current_step = "wait_for_menu"
                self.desired_option = "YES"
            case "confirm_option", _:
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "wait_for_menu":
                self.navigator = self.wait_for_menu()
            case "navigate_to_option":
                self.navigator = self.navigate_to_option()
            case "confirm_option":
                self.navigator = self.confirm_option()
            case "select_yes":
                self.navigator = self.select_yes()

    def wait_for_menu(self):
        while self.cursor.menu_cur_pos is None and self.wait_counter < 20 or self.wait_counter <= 4:
            self.wait_counter += 1
            yield
        if self.wait_counter >= 20:
            raise ValueError("Menu did not open")
        self.wait_counter = 0

    def select_yes(self):
        while self.wait_counter < 6:
            context.emulator.press_button("Up")
            self.wait_counter += 1
            yield
        while task_is_active("Task_ReleaseMon"):
            context.emulator.press_button("A")
            yield
        self.wait_counter = 0

    def navigate_to_option(self):
        while self.cursor.menu_cur_pos != self.menu.index(self.desired_option):
            context.emulator.press_button("Down")
            yield

    def confirm_option(self):
        while self.wait_counter < 10:
            if self.wait_counter == 5:
                context.emulator.press_button("A")
            self.wait_counter += 1
            yield
        self.wait_counter = 0


class BoxNavigator(BaseMenuNavigator):
    """
    This class is for navigating the box menu.
    goto_pos can be either a tuple [x,y] or int 0-29
    goto_box is the box number 0-13
    desired_option is the option to select in the menu
    """

    def __init__(self, goto_pos: tuple[int, int], goto_box: int, desired_option: str):
        super().__init__()
        if isinstance(goto_pos, int):
            goto_pos = pc_slot_from_number(goto_pos)
        if goto_pos[0] > 7:
            raise ValueError("Not implemented yet")
        self.goto_pos = goto_pos
        self.desired_option = desired_option.upper()
        self.cursor = StorageCursor()
        self.wait_counter = 0
        self.goto_box = goto_box
        self.subnavigator = None
        self.current_step = None

    def get_next_func(self):
        match self.current_step:
            case None:
                self.current_step = "wait_for_box"
            case "wait_for_box":
                self.current_step = "navigate_to_pos"
            case "navigate_to_pos":
                self.current_step = "confirm_option"
            case "confirm_option":
                self.current_step = "select_sub_option"

    def update_navigator(self):
        match self.current_step:
            case "wait_for_box":
                self.navigator = self.wait_for_box()
            case "navigate_to_pos":
                self.navigator = self.navigate_to_pos()
            case "confirm_option":
                self.navigator = self.confirm_option()
            case "select_sub_option":
                self.navigator = self.select_sub_option()

    def wait_for_box(self):
        while not self.cursor.box_mode_enabled and self.wait_counter < 20:
            self.wait_counter += 1
            yield
        if self.wait_counter >= 20:
            raise ValueError("Box did not open")
        self.wait_counter = 0

    def navigate_to_pos(self):
        while self.cursor.box_cur_pos != self.goto_pos or self.goto_box != self.cursor.current_box:
            if self.cursor.box_cur_pos is not None:
                if self.cursor.current_box != self.goto_box:
                    if self.cursor.box_cur_pos[0] != 7:
                        context.emulator.press_button("Start")
                    elif (self.goto_box - self.cursor.current_box + 13) % 13 > (
                        self.cursor.current_box - self.goto_box + 13
                    ) % 13:
                        context.emulator.press_button("Left")
                    else:
                        context.emulator.press_button("Right")
                elif self.cursor.box_cur_pos[0] > 6 and self.goto_pos[0] < 7:
                    context.emulator.press_button("Down")
                elif self.goto_pos[1] != -1:
                    if self.cursor.box_cur_pos[0] > self.goto_pos[0]:
                        context.emulator.press_button("Left")
                    elif self.cursor.box_cur_pos[0] < self.goto_pos[0]:
                        context.emulator.press_button("Right")
                    elif self.cursor.box_cur_pos[1] > self.goto_pos[1]:
                        context.emulator.press_button("Up")
                    elif self.cursor.box_cur_pos[1] < self.goto_pos[1]:
                        context.emulator.press_button("Down")
                else:
                    if self.cursor.box_cur_pos[0] == 8 and self.goto_pos[0] == 9:
                        context.emulator.press_button("Right")
                    if self.cursor.box_cur_pos[0] < self.goto_pos[0]:
                        context.emulator.press_button("Up")
                    elif self.cursor.box_cur_pos[0] > self.goto_pos[0]:
                        context.emulator.press_button("Down")
                yield
            yield

    def confirm_option(self):
        while self.wait_counter < 10:
            if self.wait_counter == 5:
                context.emulator.press_button("A")
            self.wait_counter += 1
            yield
        self.wait_counter = 0

    def select_sub_option(self):
        if not self.subnavigator:
            if self.goto_pos[1] != -1 and self.goto_pos[0] < 6:
                self.subnavigator = MenuNavigator(self.desired_option, PokeInBoxOptions)
            elif self.goto_pos[0] == 7:
                self.subnavigator = MenuNavigator(self.desired_option, BoxOptions)
            elif self.goto_pos[0] == 8:
                raise ValueError("Not implemented yet")
            yield
        else:
            yield from self.subnavigator.step()
            match self.subnavigator.current_step:
                case "exit":
                    self.subnavigator = None
                    self.current_step = "exit"


class StorageCursor:
    @property
    def box_mode_enabled(self) -> bool:
        return bool(self.box_cur_pos)

    @property
    def current_box(self) -> int:
        if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
            return int(context.emulator.read_bytes(unpack_uint32(read_symbol("gPokemonStoragePtr")), 1)[0])
        else:
            return int(
                context.emulator.read_bytes(unpack_uint32(read_symbol("gPokemonStorageSystemPtr")) + 0x117D, 1)[0]
            )

    @property
    def menu_cur_pos(self) -> int:
        try:
            match context.rom.game_title:
                case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
                    if task_is_active("Task_PCMainMenu"):
                        cur_pos = get_task("Task_PCMainMenu").data[2]
                    else:
                        if context.rom.game_title == "POKEMON EMER":
                            start_cur = 236
                            offset = 0x03007CE8
                        else:
                            start_cur = 67
                            offset = 0x03007CFC
                        cur_pos = int(context.emulator.read_bytes(offset, 1)[0])
                        cur_pos = 0 if cur_pos == start_cur else cur_pos // 16 - 1
                case "POKEMON RUBY" | "POKEMON SAPP":
                    cur_pos = int(context.emulator.read_bytes(0x030006B2, 1)[0])
            return cur_pos
        except Exception:
            return None

    @property
    def box_cur_pos(self) -> tuple[int, int]:
        """
        x position greater than 6 means either box, party, or close in that order
        y position is -1 if x position is greater than 6
        """
        try:
            x_pos_bytes = [0x54, 0x6C, 0x84, 0x9C, 0xB4, 0xCC, 0x3F, 0x92, 0x68, 0xC0]
            y_pos_bytes = [0x10, 0x28, 0x40, 0x58, 0x70, 0xFC, 0xF8]
            match context.rom.game_title:
                case "POKEMON EMER":
                    x_without_offset = 0x0300230A
                    x_with_offset = 0x0300231A
                    y_without_offset = 0x03002308
                    y_with_offset = 0x03002318
                case "POKEMON FIRE" | "POKEMON LEAF":
                    x_without_offset = 0x0300313A
                    x_with_offset = 0x0300314A
                    y_without_offset = 0x03003138
                    y_with_offset = 0x03003148
                case "POKEMON RUBY" | "POKEMON SAPP":
                    x_pos_bytes = [0x54, 0x6C, 0x84, 0x9C, 0xB4, 0xCC, 0x00, 0x92, 0x68, 0xC0]
                    x_without_offset = 0x030017BE
                    x_with_offset = 0x030017CE
                    y_without_offset = 0x030017BC
                    y_with_offset = 0x030017CC
            x_pos = x_pos_bytes.index(context.emulator.read_bytes(x_without_offset, 1)[0])
            if x_pos == 6:
                # This means the box slot has a Pokémon in it
                x_pos = x_pos_bytes.index(context.emulator.read_bytes(x_with_offset, 1)[0])
                y_pos = y_pos_bytes.index(context.emulator.read_bytes(y_with_offset, 1)[0])
            elif x_pos < 6:
                y_pos = y_pos_bytes.index(context.emulator.read_bytes(y_without_offset, 1)[0])
            else:
                y_pos = -1
            return x_pos, y_pos
        except Exception:
            return None
