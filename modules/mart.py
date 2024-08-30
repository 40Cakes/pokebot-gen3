from modules.context import context
from modules.items import Item, get_item_by_index
from modules.memory import read_symbol, unpack_uint32, unpack_uint16


def get_mart_buyable_items() -> list[Item]:
    if context.rom.is_emerald:
        item_list_pointer = unpack_uint32(read_symbol("sMartInfo", offset=8, size=4))
    elif context.rom.is_frlg:
        item_list_pointer = unpack_uint32(read_symbol("sShopData", offset=4, size=4))
    else:
        item_list_pointer = unpack_uint32(read_symbol("gMartInfo", offset=4, size=4))

    last_item_index = None
    item_list = []
    while item_list_pointer and last_item_index != 0:
        last_item_index = unpack_uint16(context.emulator.read_bytes(item_list_pointer, length=2))
        if last_item_index != 0:
            item_list.append(get_item_by_index(last_item_index))
        item_list_pointer += 2

    return item_list


def get_mart_main_menu_scroll_position() -> int:
    if context.rom.is_rs:
        return get_mart_buy_menu_scroll_position()
    else:
        return read_symbol("sMenu", offset=2, size=1)[0]


def get_mart_buy_menu_scroll_position() -> int:
    if context.rom.is_emerald:
        shop_data_ptr = unpack_uint32(read_symbol("sShopData"))
        shop_data = context.emulator.read_bytes(shop_data_ptr + 8192 + 6, length=4)
        selected_row = unpack_uint16(shop_data[0:2])
        scroll_offset = unpack_uint16(shop_data[2:4])
    elif context.rom.is_frlg:
        shop_data = read_symbol("sShopData", offset=12, size=4)
        selected_row = unpack_uint16(shop_data[0:2])
        scroll_offset = unpack_uint16(shop_data[2:4])
    else:
        data = read_symbol("gMartInfo", offset=9, size=3)
        selected_row = data[0]
        scroll_offset = data[2]

    return selected_row + scroll_offset
