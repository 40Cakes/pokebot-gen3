These tables are sourced from the [pret GitHub](https://github.com/pret).

- [Pokémon Emerald](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))

Symbol tables are loaded and parsed as a dict in the `Emulator` class in `Memory.py`.

The `patches/` directory contains minor adjustments that will override the base symbol table for each game, some symbols have missing data sizes that need to be adjusted without modifying the base table (to allow us to import newer versions of the tables directly from source).

Format of symbol tables:
```
020244ec g 00000258 gPlayerParty
---
020244ec     - memory address
g            - (l,g,,!) local, global, neither, both
00000258     - size in bytes (base 16) (0x258 = 600 bytes)
gPlayerParty - name of the symbol
```

[GBA memory domains](https://corrupt.wiki/consoles/gameboy-advance/bizhawk-memory-domains)
```
0x00000000 - 0x00003FFF - 16 KB System ROM (executable, but not readable)
0x02000000 - 0x02030000 - 256 KB EWRAM (general purpose RAM external to the CPU)
0x03000000 - 0x03007FFF - 32 KB IWRAM (general purpose RAM internal to the CPU)
0x04000000 - 0x040003FF - I/O Registers
0x05000000 - 0x050003FF - 1 KB Colour Palette RAM
0x06000000 - 0x06017FFF - 96 KB VRAM (Video RAM)
0x07000000 - 0x070003FF - 1 KB OAM RAM (Object Attribute Memory — discussed later)
0x08000000 - 0x???????? - Game Pak ROM (0 to 32 MB)
0x0E000000 - 0x???????? - Game Pak RAM
```
The `fetch_symbols.py` script will automatically download the latest symbols tables from [pret GitHub](https://github.com/pret).