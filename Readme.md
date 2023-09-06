# PokéBot Gen3 for mGBA

Re-write of [pokebot-bizhawk](https://github.com/40Cakes/pokebot-bizhawk) to work in mGBA using direct memory reads (no more image detection dependencies).

This is a *VERY early* release of this bot so minimal support will be provided in Discord, if you do encounter any issues, use the channel [#mgba-testing🧪](https://discord.com/channels/1057088810950860850/1139190426834833528)

⚠ Use this bot at your own risk! The bot directly writes to mGBA memory, there is a good chance mGBA may crash while using this bot.

The bot will pause once a shiny is encountered. You must ensure you are able to escape battle 100% of the time, otherwise the bot will get stuck. Auto-catching and other features will be added in due time.
# Requirements
- Windows (support for Mac and Linux **_may_** be added later)
- [Python 3.11](https://www.python.org/downloads/)
- [mGBA 0.10.2 (64-bit)](https://mgba.io/downloads.html)
  - **Windows (*64-bit*, installer .exe)** or **Windows (*64-bit*, portable .7z archive)**
- [Windows Terminal](https://github.com/microsoft/terminal/releases) (not **required**, but highly recommended for full 16-million <span style="color:#FF0000">c</span><span style="color:#FF7F00">o</span><span style="color:#FFFF00">l</span><span style="color:#00FF00">o</span><span style="color:#00FFFF">u</span><span style="color:#CF9FFF">r</span> console output)

# How to run
1. Run `requirements.py` to install required modules
2. Run `bot.py`, then click on an mGBA instance to attach the bot to it

# Supported Games and Language
- ✅ Supported (tested)
- 🟨 Supported (not tested)
- ❌ Not supported

## Bot Modes
Modify the `bot_mode` paramater in `config/general.yml` to any of the following modes.
***
### `manual`
Manual mode simply disables all bot inputs, allowing you to track encounters and stats on your own shiny hunts as you play the game normally.

***

### `spin`
Start the bot anywhere you want, and it will mash random directions to spin on the tile (this mode is useful for Safari Zone and [repel tricking](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) as it doesn't use up steps!)

<details>
<summary>✅🟨❌ Click here for support information</summary>

|          | Ruby | Sapphire | Emerald | FireRed | LeafGreen | 
|:---------|:----:|:--------:|:-------:|:-------:|:---------:|
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
1. Edit the starter you want to choose in the file `config/general.yml`: `starter`
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
<summary>✅🟨❌ Click here for support information</summary>

#### Starters
|          | Ruby | Sapphire | Emerald | FireRed | LeafGreen | 
|:---------|:----:|:--------:|:-------:|:-------:|:---------:|
| English  |  -   |    -     |    ✅    |    ✅    |     ✅     |
| Japanese |  -   |    -     |    -    |    -    |     -     |
| German   |  -   |    -     |    -    |    -    |     -     |
| Spanish  |  -   |    -     |    -    |    -    |     -     |
| French   |  -   |    -     |    -    |    -    |     -     |
| Italian  |  -   |    -     |    -    |    -    |     -     |
</details>

***

## Other Features

### Multi-Instance Botting
Statistics are saved into subdirectories, per-game and trainer ID (`stats/<game_code>/<trainer_id>-<trainer_name>/`) so you can safely run as many instances as your PC can handle, from a single bot folder!

The bot will first attempt to load independent `.yml` and `.py` config files from `config/<game_code>/<trainer_id>-<trainer_name>/` (automatically created), otherwise it will default to the files in the root `config/` folder; this allows you to run separate instances with unique config.

Example:
```
├── /config
    │   battle.yml             <-- loaded for saves
    │   cheats.yml             <-- loaded for saves
    │   CustomCatchFilters.py  <-- loaded for saves
    │   CustomHooks.py         <-- loaded for saves
    │   discord.yml            <-- loaded for saves except Emerald (TID 52963)
    │   general.yml            <-- loaded for saves except Emerald (TID 52963) and FireRed (TID 39167)
    │   logging.yml            <-- loaded for saves
    │   obs.yml                <-- loaded for saves
    │
    ├── /BPEE
    │   └───/52963-MAY
    |           discord.yml    <-- loaded for Emerald (TID 52963)
    │           general.yml    <-- loaded for Emerald (TID 52963)
    │
    ├── /BPRE
        └───/39167-RED
                general.yml    <-- loaded for FireRed (TID 39167)
```

### Discord Webhooks
TODO Readme

### HTTP Server
TODO Readme

### OBS Webhooks
TODO Readme

### Cheats/MemHacks
TODO Readme
***

# Attributions ❤

This project would not be possible without the symbols tables from the Pokémon decompilation projects:

- [Pokémon Emerald](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))