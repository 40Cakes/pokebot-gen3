"""
This needs to be run inside the pret decomp project, in the `include/constants/` directory.
Something like:
```
    cd /path/to/pokefire/include/constants
    python /path/to/pokebot-gen3/modules/data/event_vars/compile_pret_vars.py > \
        /path/to/pokebot-gen3/modules/data/event_vars/pret_frlg.txt
```
Since it's invoking `gcc`, this will probably only work on Linux or in WSL.
"""

import os
import re

with open("vars.c", "w") as outfile:
    outfile.write("#include <stdio.h>\n")
    outfile.write('#include "constants/vars.h"\n')
    outfile.write("int main() {\n")
    with open("vars.h", "r") as file:
        for line in file.readlines():
            if not line.startswith("#define") or line.strip() == "#define GUARD_CONSTANTS_VARS_H":
                continue
            match = re.match(r"^#define\s+(\S+)\s+(.*)$", line.strip())
            if match is None:
                continue
            name, value = match.groups()

            if name.startswith("NUM_") or name.endswith("_START") or name.endswith("_END") or name == "VARS_COUNT":
                continue

            if name.startswith("VAR_"):
                short_name = name[4:]
            else:
                short_name = name

            outfile.write(
                "    if (" + name + ' < 0x8000) printf("%d %s\\n", ' + name + ' - 0x4000, "' + short_name + '");\n'
            )
    outfile.write("    return 0;\n")
    outfile.write("}\n")

os.system("gcc -I../ vars.c -o vars.bin")
os.system("./vars.bin")
os.remove("vars.c")
os.remove("vars.bin")
