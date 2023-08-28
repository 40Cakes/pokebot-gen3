# Find symbols that contain a specific string
# Move this script to the root directory to ensure all imports work correctly
from modules.Memory import mGBA, EncodeString, ReadSymbol

string = 'there'
encoded = EncodeString(string)
for symbol in mGBA.symbols:
    b = ReadSymbol(symbol)
    if encoded in b:
        print('Found string `{}` in `{}`!'.format(
            string,
            symbol))
