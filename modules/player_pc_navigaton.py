from modules.context import context
from modules.game import decode_string
from modules.memory import read_symbol, unpack_uint16
from modules.menuing import BaseMenuNavigator, scroll_to_item_in_bag
from modules.items import Item, get_item_bag, get_item_storage
from modules.tasks import task_is_active


def player_pc_menu_index() -> int | None:
    if context.rom.is_rs:
        raise NotImplementedError("Player PC menu index is not implemented for ruby and sapphire")
    elif context.rom.is_emerald:
        symbol_name = "gPlayerPCItemPageInfo"
    elif context.rom.is_frlg:
        symbol_name = "gPlayerPcMenuManager"

    cursor_pos = unpack_uint16(read_symbol(symbol_name, 0x0, 2))
    items_above = unpack_uint16(read_symbol(symbol_name, 0x2, 2))

    return cursor_pos + items_above


def withdraw_amount() -> int | None:
    amount = decode_string(read_symbol("gStringVar4", size=0x3E8))
    if len(amount) <= 1:
        return None
    try:
        amount = int(amount[1:])
        return amount
    except ValueError:
        return None


class WithdrawItemNavigator(BaseMenuNavigator):
    def __init__(self, desired_item: Item, desired_quantity: int):
        super().__init__()

        if not context.rom.is_emerald:
            raise NotImplementedError("Withdrawing items from the player PC is only implemented for emerald")

        current_quantity_in_bag = get_item_bag().quantity_of(desired_item)
        required_quantity = desired_quantity - current_quantity_in_bag

        if required_quantity <= 0:
            raise ValueError(
                f"Cannot withdraw {desired_quantity} of {desired_item.name} from player PC there are already {current_quantity_in_bag} in bag"
            )

        if get_item_storage().quantity_of(desired_item) < required_quantity:
            raise ValueError(f"Desired item {desired_item.name} not in the player PC")

        if not get_item_bag().has_space_for(desired_item):
            raise ValueError(
                f"Bag is full, cannot withdraw {desired_quantity} of {desired_item.name} from the player PC"
            )

        self.desired_quantity = desired_quantity
        self.desired_item_index = get_item_storage().first_slot_index_for(desired_item)
        self.desired_item = desired_item

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "scroll_to_item"
            case "scroll_to_item":
                self.current_step = "withdraw_item"
            case "withdraw_item":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "scroll_to_item":
                self.navigator = self.scroll_to_item()
            case "withdraw_item":
                self.navigator = self.withdraw_item()

    def withdraw_item(self):
        context.emulator.press_button("A")
        while not task_is_active("ItemStorage_HandleQuantityRolling"):
            yield

        while withdraw_amount() != self.desired_quantity:
            old_value = withdraw_amount()
            while old_value == withdraw_amount():
                if withdraw_amount() < self.desired_quantity:
                    context.emulator.press_button("Up")
                else:
                    context.emulator.press_button("Down")
                yield

        while not task_is_active("ItemStorage_ProcessInput"):
            context.emulator.press_button("A")
            yield

    def scroll_to_item(self):
        while player_pc_menu_index() != self.desired_item_index:
            if player_pc_menu_index() is not None and player_pc_menu_index() < self.desired_item_index:
                context.emulator.press_button("Down")
            else:
                context.emulator.press_button("Up")
            for _ in range(3):
                yield
        for _ in range(20):
            yield


class DepositItemNavigator(BaseMenuNavigator):
    def __init__(self, desired_item: Item, desired_quantity: int):
        super().__init__()

        if context.rom.is_rs:
            raise NotImplementedError(
                "Depositing items from the bag into the player PC is not implemented for ruby and sapphire"
            )

        current_quantity_in_bag = get_item_bag().quantity_of(desired_item)
        self.quantity_to_remove = current_quantity_in_bag - desired_quantity

        if self.quantity_to_remove <= 0:
            raise ValueError(
                f"Cannot remove {desired_quantity} of {desired_item.name} since there are only {current_quantity_in_bag} in bag"
            )

        if not get_item_storage().has_space_for(desired_item):
            raise ValueError(f"Player PC is full, cannot deposit {desired_quantity} of {desired_item.name}")

        self.desired_quantity = desired_quantity
        self.desired_item = desired_item

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "scroll_to_item"
            case "scroll_to_item":
                self.current_step = "deposit_item"
            case "deposit_item":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "scroll_to_item":
                self.navigator = self.scroll_to_item()
            case "deposit_item":
                self.navigator = self.deposit_item()

    def deposit_item(self):
        if context.rom.is_frlg:
            deposit_task = "Task_SelectQuantityToDeposit"
            deposited_message_task = "Task_WaitAB_RedrawAndReturnToBag"
        else:
            deposit_task = "Task_ChooseHowManyToDeposit"
            deposited_message_task = "Task_RemoveItemFromBag"

        while not task_is_active(deposit_task):
            context.emulator.press_button("A")
            for _ in range(5):
                yield

        while withdraw_amount() != self.quantity_to_remove:
            old_value = withdraw_amount()
            while old_value == withdraw_amount():
                if withdraw_amount() > self.desired_quantity:
                    context.emulator.press_button("Up")
                else:
                    context.emulator.press_button("Down")
                yield

        while not task_is_active(deposited_message_task):
            context.emulator.press_button("A")
            for _ in range(5):
                yield

        while not task_is_active("Task_BagMenu_HandleInput"):
            context.emulator.press_button("A")
            for _ in range(5):
                yield

    def scroll_to_item(self):
        yield from scroll_to_item_in_bag(self.desired_item)
