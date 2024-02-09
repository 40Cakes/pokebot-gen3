"""
This assumes that pret's `pokeemerald` and `pokefirered` repositories are checked
out in the same directory as Pokebot.

So the directory structure should be something like:

```
/
    /pokebot-gen3
    /pokeemerald
    /pokefirered
```

Then, just run this file and will it write/overwrite `map_data.py`.
"""

import re
from pathlib import Path

this_dir = Path(__file__).parent

with open(this_dir.parent / "map_data.py", "w") as out:
    out.write("from enum import Enum\n\n")
    out.write("from modules.map import MapLocation\n\n")
    out.write(
        """
def _might_be_map_coordinates(value) -> bool:
    return isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], int) and isinstance(value[1], int)\n"""
    )

    for directory, game_code in (("pokefirered", "FRLG"), ("pokeemerald", "RSE")):
        current_map_group_name = ""
        map_group_names: dict[int, str] = {}
        output: list[str] = []
        with open(this_dir.parent.parent.parent / directory / "include" / "constants" / "map_groups.h", "r") as file:
            for line in file.readlines():
                if line.startswith("// gMapGroup_"):
                    output.append("")
                    current_map_group_name = line[13:].strip()
                    output.append(f"    # {current_map_group_name}")

                if not line.startswith("#define") or not line.strip().endswith(" << 8))"):
                    continue

                match = re.match(r"^#define\s+(\S+)\s+\((\d+)\s+\|\s+\((\d+) << 8\)\)$", line.strip())
                map_name, map_number, map_group = match.groups()

                if map_group not in map_group_names:
                    map_group_names[map_group] = current_map_group_name

                output.append(f"    {map_name[4:]} = ({map_group}, {map_number})")

        out.write("\n\n")

        out.write(f"class MapGroup{game_code}(Enum):\n")
        for map_group in map_group_names:
            out.write(f"    {map_group_names[map_group]} = {map_group}\n")
        out.write(
            f"""    def __contains__(self, item):
        if _might_be_map_coordinates(item):
            return self.value == item[0]
        elif isinstance(item, Map{game_code}):
            return self.value == item.value[0]
        else:
            return NotImplemented"""
        )

        out.write("\n\n\n")

        out.write(f"class Map{game_code}(Enum):\n")
        out.write("    " + "\n".join(output).strip() + "\n")
        out.write(
            f"""
    def __eq__(self, other):
        if _might_be_map_coordinates(other):
            return self.value == other
        elif isinstance(other, Map{game_code}):
            return self.value == other.value
        else:
            return NotImplemented

    def __ne__(self, other):
        equals = self.__eq__(other)
        if isinstance(equals, bool):
            return not equals
        else:
            return NotImplemented
            
    def __contains__(self, item):
        if item is None:
            return False
        elif isinstance(item, MapLocation):
            return item.map_group == self.value[0] and item.map_number == self.value[1]
        else:
            return NotImplemented\n"""
        )
