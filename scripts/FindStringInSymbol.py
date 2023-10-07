# Find symbols that contain a specific string
# Move this script to the root directory to ensure all imports work correctly
from modules.Game import EncodeString, _symbols
from modules.Memory import ReadSymbol

string = 'there'
encoded = EncodeString(string)
for symbol in _symbols:
    b = ReadSymbol(symbol)
    if encoded in b:
        print('Found string `{}` in `{}`!'.format(
            string,
            symbol))
