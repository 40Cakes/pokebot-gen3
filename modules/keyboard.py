from modules.context import context
from modules.memory import unpack_uint32, read_symbol
from modules.game import decode_string
from modules.tasks import task_is_active

class Keyboard:
    def __init__(self):
        pass
    
    @property
    def enabled(self) -> bool:
        if task_is_active("Task_NamingScreen"):
            return True
        else:
            return False
    
    @property
    def text_buffer(self) -> str:
        try:
            if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
                return decode_string(context.emulator.read_bytes(unpack_uint32(read_symbol("sNamingScreen")) + 0x1800, 16))
            else:
                return decode_string(context.emulator.read_bytes(unpack_uint32(read_symbol("namingScreenDataPtr")) + 0x11, 16))
        except Exception:
            return None
        
    @property
    def cur_page(self) -> int:
        try:
            if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
                return [1,2,0].index(context.emulator.read_bytes(unpack_uint32(read_symbol("sNamingScreen")) + 0x1E22, 1)[0])
            else:
                return [0x3c,0x42,0x3F].index(context.emulator.read_bytes(0x03001858, 1)[0])
        except Exception:
            return None
    
    @property
    def cur_pos(self) -> tuple:
        x_val = None
        y_val = None
        if context.rom.game_title not in ["POKEMON RUBY", "POKEMON SAPP"]:
            x_val = context.emulator.read_bytes(0x03007D98, 1)[0]
            if context.rom.game_title == "POKEMON EMER":
                y_val = int(context.emulator.read_bytes(0x030023A8, 1)[0]/16)-5
            else:
                y_val = int(context.emulator.read_bytes(0x030031D8, 1)[0]/16)-5
        else:
            try:
                if self.cur_page == 2:
                    x_val = [0x1B,0x33,0x4B,0x63,0x7B,0x93,0xBC].index(context.emulator.read_bytes(0x0300185E, 1)[0])
                else:
                    x_val = [0x1B,0x2B,0x3B,0x53,0x63,0x73,0x83,0x9B,0xBC].index(context.emulator.read_bytes(0x0300185E, 1)[0])
            except Exception:
                pass
            y_val = int(context.emulator.read_bytes(0x0300185C, 1)[0]/16)-4
        return (x_val, y_val)

def get_keyboard():
    return Keyboard()