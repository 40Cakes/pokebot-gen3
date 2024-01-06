"""
This needs to be run inside the pret decomp project, in the `include/constants/` directory.
Something like:
```
    cd /path/to/pokefire/include/constants
    python /path/to/pokebot-gen3/modules/data/event_flags/compile_pret_flags.py > \
        /path/to/pokebot-gen3/modules/data/event_flags/pret_frlg.txt
```
Since it's invoking `gcc`, this will probably only work on Linux or in WSL.
"""

import os
import re

with open("flags.c", "w") as outfile:
    outfile.write("#include <stdio.h>\n")
    outfile.write('#include "constants/flags.h"\n')
    outfile.write("int main() {\n")
    with open("flags.h", "r") as file:
        for line in file.readlines():
            if not line.startswith("#define") or line.strip() == "#define GUARD_CONSTANTS_FLAGS_H":
                continue
            match = re.match(r"^#define\s+(\S+)\s+(.*)$", line.strip())
            name, value = match.groups()

            if (
                name.startswith("NUM_")
                or (name.endswith("_START") and name != "FLAG_SYS_TV_START")
                or name.endswith("_END")
                or name.endswith("_COUNT")
                or re.match(r"^FLAG_0x[0-9A-Fa-f]+$", name)
                or re.match(r"^FLAG_UNUSED_0x[0-9A-Fa-f]+$", name)
            ):
                continue

            if name.startswith("FLAG_"):
                short_name = name[5:]
            else:
                short_name = name

            outfile.write('    printf("%d %s\\n", ' + name + ', "' + short_name + '");\n')
    outfile.write("    return 0;\n")
    outfile.write("}\n")

os.system("gcc -I../ flags.c -o flags.bin")
os.system("./flags.bin")
os.remove("flags.c")
os.remove("flags.bin")
