# Loops indefinitely while outputting the raw value and decoded text of a specific symbol
# Move this script to the root directory to ensure all imports work correctly
import time
from modules.Memory import DecodeString, ReadSymbol

symbols = ['sChat', 'gStringVar1', 'gStringVar2', 'gStringVar3', 'gStringVar4']
while True:
    for symbol in symbols:
        print('-----------------')
        b_symbol = ReadSymbol(symbol)
        print('`{}`:'.format(symbol))
        print('{}'.format(b_symbol))
        print('{}'.format(DecodeString(b_symbol)))
    time.sleep(1)