# PokéBot Gen3 (libmgba)
[![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)](https://www.python.org/) [![Discord](https://img.shields.io/badge/Discord-%235865F2.svg?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/UtxR3cazUa) [![YouTube](https://img.shields.io/badge/YouTube-%23FF0000.svg?style=for-the-badge&logo=YouTube&logoColor=white)](https://www.youtube.com/channel/UCl5dLxULvf6ynUiqRSchrzA) [![Twitter](https://img.shields.io/badge/Twitter-%231DA1F2.svg?style=for-the-badge&logo=Twitter&logoColor=white)](https://twitter.com/40_Cakes)

**PokéBot Gen3 (libmgba)** is a bot, written in Python that automatically shiny hunts in Pokémon Ruby, Sapphire, Emerald, FireRed and LeafGreen.

Initially created to complete a Prof. Oak and Living ✨Shiny✨ Dex Challenge in Pokémon Emerald, a 🔴24/7 livestream of the challenge can be found ongoing [here](https://www.youtube.com/watch?v=W6OOnrx8g58).

[![🔴24/7✨Shiny✨Hunting Bot](https://img.youtube.com/vi/W6OOnrx8g58/0.jpg)](https://www.youtube.com/watch?v=W6OOnrx8g58)

https://github.com/40Cakes/pokebot-gen3/assets/16377135/e6cea062-895e-411a-86fb-fe0e6e22c34d

| Main Interface | Load Save State | Debugger |
|:-:|:-:|:-:|
|![image](https://github.com/40Cakes/pokebot-gen3/assets/16377135/75c88c35-83c4-4a26-b907-429b02fda564)|![image](https://github.com/40Cakes/pokebot-gen3/assets/16377135/52afa39a-c674-47a7-90ed-3e25e82050f5)|![image](https://github.com/40Cakes/pokebot-gen3/assets/16377135/d017651d-96f1-41cc-a03a-5462c96e027a)|
| Shiny Notifications | Phase Stats | Milestones |
|![image](https://github.com/40Cakes/pokebot-gen3/assets/16377135/69230b70-24f2-46b3-bb7e-54241785a932)|![image](https://github.com/40Cakes/pokebot-gen3/assets/16377135/613e73b8-bc20-46aa-92c1-168d566f4e66)|![image](https://github.com/40Cakes/pokebot-gen3/assets/16377135/a8c0f5be-9b81-4be6-8a71-cdf909ef0df0)|

# 📖 Preamble
- This is still in development, as such, functionality is subject to change - always make sure you back up your `profiles` folders before updating your bot!
- Reach out in Discord [#bot-support-libmgba❔](https://discord.com/channels/1057088810950860850/1139190426834833528) if you have any issues

The bot is frame perfect and can _technically_ cheat by reading data from any point in memory. By default it will attempt to perform actions as if a human were playing to make gameplay as representative as possible, some examples:
- Starter Pokémon are generated just _1 frame_ after confirming the starter selection, the bot will wait until the battle begins, and the starter Pokémon sprite is visible before resetting
- It's possible to peek inside un-hatched eggs to view stats and shininess as soon as they're received from the daycare, the bot will wait until the eggs are fully hatched before checking and logging
- These are intentional design decisions, bot [cheats](https://github.com/40Cakes/pokebot-gen3/wiki/%F0%9F%92%8E-Cheats) can be used to bypass them (in most cases)

***

# ❓ Getting Started
Visit the [wiki](https://github.com/40Cakes/pokebot-gen3/wiki) for information on running the bot.

The wiki contains information about the default emulator keybinds/inputs, bot modes, configuration files and more (use the side bar to navigate)!

***

# ⏩ Tips/Tricks
## Optimal game settings

- Set **TEXT SPEED** to **FAST**
- Set **BATTLE SCENE** to **OFF**
- Utilise [repel tricks](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) to boost encounter rates of target Pokémon
- Using modes [Spin](https://github.com/40Cakes/pokebot-gen3/wiki/%F0%9F%94%84-Spin) or [Bunny Hop](https://github.com/40Cakes/pokebot-gen3/wiki/%F0%9F%9A%B2-Bunny-Hop) and repels will become effectively infinite + steps won't be counted in Safari Zone
- Use a lead Pokémon with encounter rate boosting [abilities](https://bulbapedia.bulbagarden.net/wiki/Category:Abilities_that_affect_appearance_of_wild_Pok%C3%A9mon), such as **[Illuminate](https://bulbapedia.bulbagarden.net/wiki/Illuminate_(Ability))**
- Use a lead Pokémon with a [short cry](https://docs.google.com/spreadsheets/d/1rmtNdlIXiif1Sz20i-9mfhFdoqb1VnAOIntlr3tnPeU)
- Use a lead Pokémon with a single character nickname
- Don't use a shiny lead Pokémon (shiny animation takes a few frames at the start of every battle)

***

# 🐛 Debugging

The bot supports auto-starting a profile and can also be launched into a 'debug' mode which can aid bot development.

```
positional arguments:
  profile               Profile to initialize. Otherwise, the profile selection menu will appear.

options:
  -h, --help            show this help message and exit
  -m {Manual,Spin,Starters,Fishing,Bunny Hop, Ancient Legendaries}, --bot-mode {Manual,Spin,Starters,Fishing,Bunny Hop, Ancient Legendaries}
                        Initial bot mode (default: Manual)
  -s {0,1,2,3,4}, --emulation-speed {0,1,2,3,4}
                        Initial emulation speed (0 for unthrottled; default: 1)
  -nv, --no-video       Turn off video output by default
  -na, --no-audio       Turn off audio output by default
  -t, --always-on-top   Keep the bot window always on top of other windows
  -d, --debug           Enable extra debug options and a debug menu
```

***

# ⚠ Photosensitivity Warning
- Running mGBA at unbound speeds, will cause **very fast and bright flashing**!
- Any unbounded video examples on this page will be hidden by default, and marked with **⚠ photosensitivity warning**

***

# ❤ Attributions

- [mGBA](https://github.com/mgba-emu/mgba)
- [libmgba-py](https://github.com/hanzi/libmgba-py/)

Other awesome PokéBot projects:

- [PokéBot NDS](https://github.com/wyanido/pokebot-nds/)

This project would not be possible without the decompiled symbol tables and other various data from the following projects:

- [Pokémon Emerald decompilation](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire decompilation](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen decompilation](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))
- PKHeX Plugin: [MissingEventFlagsCheckerPlugin](https://github.com/fattard/MissingEventFlagsCheckerPlugin) (event flags data)
