🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# ❌ Catch Block List Config

[`profiles/catch_block.yml`](../../profiles/catch_block.yml)

The catch block list is a list of shinies to skip, useful if you don't want to fill up your PC with very common shiny encounters.

- **Note**: phase stats will still be reset after encountering a shiny on the block list.
- The block list is automatically reloaded by the bot during a shiny encounter, so you can modify this file while the bot is running!

`block_list` - list of Pokémon to skip catching (one per line), example:
```
block_list:
  - Poochyena
  - Pidgey
  - Rattata
```
