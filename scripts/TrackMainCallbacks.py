# Parse the function pointer in gMain.callback1 and gMain.callback2 to the functionnames from the game symbols 
import struct
from modules.Console import console
from modules.Memory import ReadSymbol,mGBA

with console.status('', refresh_per_second=100) as status:
    previous1 = b''
    previous2 = b''
    while True:
        callback1 = ReadSymbol('gMain',0,4)#gMain.callback1
        callback2 = ReadSymbol('gMain',4,4)#gMain.callback2
        if callback1 != previous1:
            addr = hex(int(struct.unpack('<I', callback1)[0])-1)
            if(addr != '-0x1'):
                console.print('callback1: ' + mGBA.addressymbolmap[addr]['name'])
            previous1 = callback1
        if callback2 != previous2:
            addr = hex(int(struct.unpack('<I', callback2)[0])-1)
            if(addr != '-0x1'):
                console.print('callback2: ' + mGBA.addressymbolmap[addr]['name'])
            previous2 = callback2
