import json
import struct

from modules.Console import console
from modules.Files import ReadFile
from modules.Memory import GetSaveBlock, mGBA


item_list = json.loads(ReadFile('./modules/data/items.json'))

def GetItems() -> dict:
    """
    Get all items and their quantities from the PC, Items pocket, Key Items pocket, Poké Balls pocket, TMs & HMs pocket,
    Berries pocket.

    :return: trainer's items (dict)
    """
    try:
        items = {}
        pockets = ['PC', 'Items', 'Key Items', 'Poké Balls', 'TMs & HMs', 'Berries']
        for pocket in pockets:
            items[pocket] = {}

        b_Items = GetSaveBlock(1, mGBA.item_offsets[0][0], mGBA.item_offsets[4][0] + mGBA.item_offsets[4][1])

        for i in range(6):
            p = mGBA.item_offsets[i][0] - mGBA.item_offsets[0][0]
            for j in range(0, int(mGBA.item_offsets[i][1] / 4)):
                q = struct.unpack('<H', b_Items[p+(j*4+2):p+(j*4+4)])[0]
                quantity = int(q ^ mGBA.item_key) if i != 0 else q
                item = {
                    'name': item_list[int(struct.unpack('<H', b_Items[p+(j*4):p+(j*4+2)])[0])],
                    'quantity': quantity
                }
                items[pockets[i]][j] = item
        return items
    except:
        console.print_exception(show_locals=True)
