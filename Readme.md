# PokéBot Gen3 for mGBA

Re-write of [pokebot-bizhawk](https://github.com/40Cakes/pokebot-bizhawk) to work in mGBA using direct memory reads (no more image detection dependencies).

This is a *VERY early* release of this bot so minimal support will be provided in Discord, if you do encounter any issues, use the channel [#bot-support-mgba🧪](https://discord.com/channels/1057088810950860850/1139190426834833528)

⚠ Use this bot at your own risk! The bot directly writes to mGBA memory, there is a good chance mGBA may crash while using this version.

There are some Windows only dependencies at the moment (specifically Pymem), so only Windows and mGBA 0.10.2 (64-bit) will be supported for now, support for Mac and Linux may be added later.

The bot is hard-coded to `spin` on the spot and exit once a shiny is encountered. You must ensure you are able to escape battle 100% of the time, otherwise the bot will get stuck. There is currently no UI, auto-catching, encounter logging etc. It is as bare-bones as it gets, these features will be added in due time.

# How to run

1. Run `requirements.py` to install required modules.
2. Run `bot.py`, then click on an mGBA instance to attach the bot to it.

# Supported Games and Language

- ✅ Supported (tested)
- 🟨 Supported (not tested)
- ❌ Not supported

## Bot Modes
### `Spin`
Start the bot anywhere you want, and it will mash random directions to spin on the tile (this mode is useful for Safari Zone and [repel tricking](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) as it doesn't use up steps!)

<details>
<summary>Click for support information</summary>

|              | Ruby | Sapphire | Emerald | FireRed | LeafGreen | 
|:-------------|:----:|:--------:|:-------:|:-------:|:---------:|
| English  |  -   |    -     |    -    |    -    |     -     |
| Japanese |  -   |    -     |    -    |    -    |     -     |
| German   |  -   |    -     |    -    |    -    |     -     |
| Spanish  |  -   |    -     |    -    |    -    |     -     |
| French   |  -   |    -     |    -    |    -    |     -     |
| Italian  |  -   |    -     |    -    |    -    |     -     |
</details>

# Attributions ❤

This project would not be possible without the symbols tables from the Pokémon decompilation projects:

- [Pokémon Emerald](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))