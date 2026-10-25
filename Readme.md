# PokéBot Gen3 (libmgba)
[![Wiki](wiki/images/badge_wiki.svg)](wiki/Readme.md) [![Python 3.14](wiki/images/badge_python.svg)](https://www.python.org/downloads/release/python-3149/) [![Code Formatting](wiki/images/badge_black.svg)](https://github.com/psf/black)

[![Discord](wiki/images/badge_discord.svg)](https://discord.com/invite/UtxR3cazUa) [![YouTube](wiki/images/badge_youtube.svg)](https://www.youtube.com/@40_Cakes/streams)

**PokéBot Gen3** is a shiny hunting bot, written in Python that runs `libmgba` + mGBA Python bindings under the hood. Pokémon Ruby, Sapphire, Emerald, FireRed and LeafGreen are supported. 

Initially created to complete a Prof. Oak and Living ✨Shiny✨ Dex Challenge in Pokémon Emerald, a 24/7 livestream of the challenge can be found ongoing [here](https://www.youtube.com/watch?v=aQWyyI7JmTk).

[![🔴24/7✨Shiny✨Hunting Bot](https://img.youtube.com/vi/aQWyyI7JmTk/0.jpg)](https://www.youtube.com/watch?v=aQWyyI7JmTk)

# ❓ Getting Started

Visit the [wiki](wiki/Readme.md) for information:
- ❓ [Getting Started](wiki/pages/Getting%20Started.md)
- 🎮 [Emulator Input Mapping](wiki/pages/Configuration%20-%20Key%20Mappings.md)
- 🔎 [Pokémon by Bot Mode](wiki/pages/Pokemon%20By%20Bot%20Mode.md)

# ✨ Preamble

You are welcome to use or stream the bot in any way you want, including streaming your own 24/7 Prof. Oak challenge streams.

The intent of this bot is not to _cheat_ for shinies or complete the game as fast as possible, but instead to transform generation 3 Pokémon games into somewhat of an idle game, stacking up millions of encounters searching for that one encounter, or completing an absurd challenge.

The bot is frame perfect and can _technically_ cheat by reading data from any point in memory and manipulating RNG. By default, it will attempt to perform actions as if a human were playing to make gameplay as representative as possible, some examples:
- Starter Pokémon are generated just _1 frame_ after confirming the starter selection, the bot will wait until the battle begins, and the starter Pokémon sprite is visible before soft resetting
- It's possible to peek inside un-hatched eggs to view stats and shininess as soon as they're received from the daycare, the bot will wait until the eggs are fully hatched before checking and logging
- Feebas tile locations _could_ be instantly located by reading memory, instead, the bot will attempt to locate the tiles by searching each tile individually

# 😎 Showcase

|              Main interface              |              Load save state              |              Debug mode              |
|:----------------------------------------:|:-----------------------------------------:|:------------------------------------:|
| ![image](wiki/images/main_interface.png) | ![image](wiki/images/load_save_state.png) | ![image](wiki/images/debug_mode.png) |

| Shiny encounter GIFs            | 
|---------------------------------|
| ![image](wiki/images/shiny.gif) |

|             Discord shiny notifications              |              Discord phase stats              |              Discord milestones              |
|:----------------------------------------------------:|:---------------------------------------------:|:--------------------------------------------:|
| ![image](wiki/images/discord_shiny_notification.png) | ![image](wiki/images/discord_phase_stats.png) | ![image](wiki/images/discord_milestones.png) |

| Automatically saves PKHeX .pk3 file | HTTP API                           |
|-------------------------------------|------------------------------------|
| ![image](wiki/images/pk3_files.png) | ![image](wiki/images/http_api.png) |

# ❤ Attributions

Core functionality:

- [mGBA](https://github.com/mgba-emu/mgba)
- [libmgba-py](https://github.com/hanzi/libmgba-py/)

Other awesome PokéBot projects:

- [PokéBot NDS](https://github.com/wyanido/pokebot-nds/)

Decompiled symbol tables and other various data from the following projects:

- [Pokémon Emerald decompilation](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire decompilation](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen decompilation](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))

Test save states and bot profiles:

- [Johnnie's PokéBot-Profiles](https://github.com/johnnieb333/Pokebot-Profiles)
