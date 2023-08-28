# PokéBot Gen3 for mGBA

Re-write of [pokebot-bizhawk](https://github.com/40Cakes/pokebot-bizhawk) to work in mGBA using direct memory reads (no more image detection dependencies).

This is a *VERY early* release of this bot so minimal support will be provided in Discord, if you do encounter any issues, use the channel [#mgba-testing🧪](https://discord.com/channels/1057088810950860850/1139190426834833528)

⚠ Use this bot at your own risk! The bot directly writes to mGBA memory, there is a good chance mGBA may crash while using this version.

There are some Windows only dependencies at the moment (specifically Pymem), so only Windows and **mGBA 0.10.2 (64-bit)** will be supported for now, support for Mac and Linux may be added later.

The bot will pause once a shiny is encountered. You must ensure you are able to escape battle 100% of the time, otherwise the bot will get stuck. Auto-catching and other features will be added in due time.

# How to run

1. Run `requirements.py` to install required modules.
2. Run `bot.py`, then click on an mGBA instance to attach the bot to it.

# Supported Games and Language

- ✅ Supported (tested)
- 🟨 Supported (not tested)
- ❌ Not supported

## Bot Modes
***
### `spin`
Start the bot anywhere you want, and it will mash random directions to spin on the tile (this mode is useful for Safari Zone and [repel tricking](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) as it doesn't use up steps!)

<details>
<summary>Click for support information</summary>

|              | Ruby | Sapphire | Emerald | FireRed | LeafGreen | 
|:-------------|:----:|:--------:|:-------:|:-------:|:---------:|
| English  |  ✅   |    ✅     |    ✅    |    ✅    |     ✅     |
| Japanese |  -   |    -     |    -    |    -    |     -     |
| German   |  -   |    -     |    -    |    -    |     -     |
| Spanish  |  -   |    -     |    -    |    -    |     -     |
| French   |  -   |    -     |    -    |    -    |     -     |
| Italian  |  -   |    -     |    -    |    -    |     -     |
</details>

***

### `starters`
#### Ruby/Sapphire
🚧 Coming soon.

#### Emerald
1. Edit the starter you want to choose in the config file: `starter`
2. Face the starters bag, and save the game (**in-game, not a save state**)
3. Start the bot

#### Emerald (Johto)
🚧 Coming soon.

**Note**: Emerald does not seed RNG correctly. For encounters that use soft resets such as starters, the bot will wait more frames after every reset to reduce the odds of getting identical Pokémon. This choice causes reset encounters on the same save file to take progressively longer, so it's recommended to occasionally start a new save file to reset this delay.
#### Fire Red/Leaf Green
1. Face the desired Pokéball in Oak's lab (Bulbasaur/Charmander/Squirtle)
2. Save the game (**in-game, not a save state**)
3. Start the bot

<details>
<summary>Click for support information</summary>

#### Starters
|              | Ruby | Sapphire | Emerald | FireRed | LeafGreen | 
|:-------------|:----:|:--------:|:-------:|:-------:|:---------:|
| English  |  -   |    -     |    ✅    |    ✅    |     ✅     |
| Japanese |  -   |    -     |    -    |    -    |     -     |
| German   |  -   |    -     |    -    |    -    |     -     |
| Spanish  |  -   |    -     |    -    |    -    |     -     |
| French   |  -   |    -     |    -    |    -    |     -     |
| Italian  |  -   |    -     |    -    |    -    |     -     |
</details>

***

# Attributions ❤

This project would not be possible without the symbols tables from the Pokémon decompilation projects:

- [Pokémon Emerald](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))