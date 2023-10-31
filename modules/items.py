from modules.console import console
from modules.context import context
from modules.memory import get_save_block, unpack_uint16
from modules.pokemon import get_item_by_index


def get_item_offsets() -> list[tuple[int, int]]:
    # Game specific offsets
    # Source: https://bulbapedia.bulbagarden.net/wiki/Save_data_structure_(Generation_III)#Section_1_-_Team_.2F_Items
    match context.rom.game_title:
        case "POKEMON FIRE" | "POKEMON LEAF":
            return [(0x298, 120), (0x310, 168), (0x3B8, 120), (0x430, 52), (0x464, 232), (0x54C, 172)]
        case "POKEMON EMER":
            return [(0x498, 200), (0x560, 120), (0x5D8, 120), (0x650, 64), (0x690, 256), (0x790, 184)]
        case _:
            return [(0x498, 200), (0x560, 80), (0x5B0, 80), (0x600, 64), (0x640, 256), (0x740, 184)]


def get_item_key() -> int:
    match context.rom.game_title:
        case "POKEMON FIRE" | "POKEMON LEAF":
            return unpack_uint16(get_save_block(2, 0xF20, 2))
        case "POKEMON EMER":
            return unpack_uint16(get_save_block(2, 0xAC, 2))
        case _:
            return 0


def get_items() -> dict:
    """
    Get all items and their quantities from the PC, Items pocket, Key Items pocket, Poké Balls pocket, TMs & HMs pocket,
    Berries pocket.

    :return: trainer's items (dict)
    """
    try:
        items = {}
        pockets = ["PC", "Items", "Key Items", "Poké Balls", "TMs & HMs", "Berries"]
        for pocket in pockets:
            items[pocket] = {}

        item_offsets = get_item_offsets()
        b_Items = get_save_block(1, item_offsets[0][0], item_offsets[4][0] + item_offsets[4][1])

        for i in range(6):
            p = item_offsets[i][0] - item_offsets[0][0]
            for j in range(0, int(item_offsets[i][1] / 4)):
                q = unpack_uint16(b_Items[p + (j * 4 + 2) : p + (j * 4 + 4)])
                item_id = unpack_uint16(b_Items[p + (j * 4) : p + (j * 4 + 2)])

                if item_id:
                    name = get_item_by_index(item_id).name
                    quantity = int(q ^ get_item_key()) if i != 0 else q
                    items[pockets[i]][name] = quantity
        return items
    except:
        console.print_exception(show_locals=True)
