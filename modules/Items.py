from modules.Console import console
from modules.Memory import GetSaveBlock, GetItemOffsets, GetItemKey, unpack_uint16
from modules.Pokemon import get_item_by_index


def GetItems() -> dict:
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

        item_offsets = GetItemOffsets()
        b_Items = GetSaveBlock(1, item_offsets[0][0], item_offsets[4][0] + item_offsets[4][1])

        for i in range(6):
            p = item_offsets[i][0] - item_offsets[0][0]
            for j in range(0, int(item_offsets[i][1] / 4)):
                q = unpack_uint16(b_Items[p + (j * 4 + 2) : p + (j * 4 + 4)])
                item_id = unpack_uint16(b_Items[p + (j * 4) : p + (j * 4 + 2)])

                if item_id:
                    name = get_item_by_index(item_id).name
                    quantity = int(q ^ GetItemKey()) if i != 0 else q
                    items[pockets[i]][name] = quantity
        return items
    except:
        console.print_exception(show_locals=True)
