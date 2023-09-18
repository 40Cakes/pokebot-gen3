# Move this script to the root directory to ensure all imports work correctly
from modules.Memory import DecodeString, EncodeString

print(DecodeString(b'\xe8\xd9\xe7\xe8'))
print(EncodeString('test'))
