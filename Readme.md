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
- This is still in development, as such, functionality is subject to change without warning - always make sure you back up your `profiles/<profile name>/` folder before updating your bot!
- Reach out in Discord [#bot-support-libmgba❔](https://discord.com/channels/1057088810950860850/1139190426834833528) if you have any issues

The bot is frame perfect and can cheat by reading data from any point in memory. By default it will attempt to perform most actions as if a human were playing to make gameplay as representative as possible, some examples:
- Starter Pokémon are generated just _1 frame_ after confirming the starter selection, the bot will wait until the battle begins, and the starter Pokémon sprite is visible before resetting
- It's possible to peek inside un-hatched eggs to view stats and shininess as soon as they're received from the daycare, the bot will wait until the eggs are fully hatched before checking and logging
- These are intentional design decisions, bot [cheats](#cheatsyml---cheats-config) can be used to bypass them (in most cases)

***

# ⚠ Photosensitivity Warning
- Running mGBA at unbound speeds, will cause **very fast and bright flashing**!
- Any unbounded video examples on this page will be hidden by default, and marked with **⚠ photosensitivity warning**

***

# 🔒 Prerequisites
### Operating Systems

- Windows (**64-bit**)
- Linux (**64-bit**)
  - Note: only tested and confirmed working on **Ubuntu 23.04** and **Debian 12**

### Download the Bot
To download the latest bot from GitHub, go to the top of the page > click the green **Code** button > **Download ZIP**.

Alternatively, if you'd like to be able to easily pull the latest updates without re-downloading the entire ZIP:
- Install [GitHub Desktop](https://desktop.github.com/) (you don't need an account)
- Click **Clone a repository from the Internet...**
- Use repository URL `https://github.com/40Cakes/pokebot-gen3.git` and choose a save location on your PC
- Click **Clone**
- Any time there's a new update, you can pull the latest changes by clicking **Fetch origin**, then **Pull origin**

### Requirements
- [Python 3.12](https://www.python.org/downloads/release/python-3120/) (**64-bit**)
- **Linux** only: Install the following packages with `apt` or appropriate package manager: `sudo apt install python3-tk libmgba0.10 portaudio19-dev`
- **Note**: running the bot will **automatically** install required Python packages and download + extract [libmgba](https://github.com/hanzi/libmgba-py) - if you're using Python for any other projects, consider using a [venv](https://docs.python.org/3/library/venv.html) to isolate these packages from your base environment

### Optional
- [Windows Terminal](https://github.com/microsoft/terminal/releases) - recommended for full 🌈<span style="color:#FF0000">c</span><span style="color:#FF7F00">o</span><span style="color:#FFFF00">l</span><span style="color:#00FF00">o</span><span style="color:#00FFFF">u</span><span style="color:#CF9FFF">r</span>🌈 and  ✨emoji support✨ in the console output
- [Notepad++](https://notepad-plus-plus.org/) - recommended for syntax highlighting while editing `.yml` config files

***

# ❓ How To Run
- Place some **official** Pokémon .gba ROMs into the `roms/` folder
- Double click `pokebot.py` or run `python pokebot.py` in a terminal and follow the on-screen steps to create and/or select a profile

The bot ships with the default mGBA input mapping, see [`profiles/keys.yml`](#keysyml---emulator-input-mapping) to view the default mapping, or customise them to your preference.

The bot will pause once a shiny is encountered. You **must** ensure you are able to escape battle **100% of the time**, otherwise the bot will get stuck. Auto-catching and other features will be added in due time.

***

# 💾 Import a Save
If you have a save from mGBA that you'd like to import and use with the bot, then you will need to import the save state.

- In mGBA, run a game and load into the save file
- **File** > **Save State File...** > **Save**
- Double click `import.py` or run `python import.py` in a terminal to launch the save importer tool
- Open the save state file you just saved
- A new bot profile will be created in the `profiles/` folder and set up all required files
- If the importer tool detects files in the `stats/` or `profiles/` folders from old versions of the bot (from commit `ec5d702`, 7th October, 2023 or earlier), then they will be copied into your new profile

***

#  🌍 Supported Games and Languages
Variations of games, languages and revisions may have different memory offsets, there will be a table of supported/tested variations under each bot mode listed below.

- ✅ Supported (tested)
- 🟨 Supported (not tested)
- ❌ Not supported

ROM hacks will likely not work, and are ❌ **not supported** or planned to be supported!

The ROMs in the `roms/` folder are checked and verified against a list of all known official gen3 game hashes. If you **really** want to test a ROM hack with the bot, you must add the SHA1 hash of the ROM to `modules/Roms.py`.

The SHA1 hash of a ROM can be calculated with any of the following methods:
- [ROM Hasher](https://www.romhacking.net/utilities/1002/)
- Windows Powershell: `Get-FileHash 'rom_name.gba' -Algorithm SHA1`
- Linux: `sha1sum 'rom_name.gba'`

Please do not seek support or complain if you find that your ROM hack does not work with the bot.

***

# 🤖 Bot Modes
- The bot mode can be changed at any time while the bot is running by using the menu on the UI
- `manual` mode is the default mode
- Press `Tab` to toggle between `manual` mode and a previously selected mode

***
## 🔧 `manual`
Manual mode simply disables all bot inputs, allowing you to track encounters and stats on your own shiny hunts as you play the game normally.

## 🔄 `spin`
Spin clockwise on a single tile, useful for Safari Zone and [repel tricking](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) as it doesn't count steps

Start the mode while in the overworld, in any patch of grass/water/cave.

<details>
<summary>🎥 Click here to show a video example</summary>

https://github.com/40Cakes/pokebot-gen3/assets/16377135/32ced886-062b-483b-86c4-11be8ce55943

</details>

<details>
<summary>✅🟨❌ Click here for support information</summary>

|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald | 🔥 FireRed | 🌿 LeafGreen |
|:---------|:----:|:--------:|:-------:|:-------:|:---------:|
| English  |  ✅   |    ✅     |    ✅    |    ✅    |     ✅     |
| Japanese |  🟨   |    🟨     |    🟨    |    🟨    |     🟨     |
| German   |  🟨   |    🟨     |    🟨    |    🟨    |     🟨     |
| Spanish  |  🟨   |    🟨     |    🟨    |    🟨    |     🟨     |
| French   |  🟨   |    🟨     |    🟨    |    🟨    |     🟨     |
| Italian  |  🟨   |    🟨     |    🟨    |    🟨    |     🟨     |
</details>

## 💼 `starters`
Soft reset for starter Pokémon.

<details>
<summary>🎥 Click here to show a video example</summary>

https://github.com/40Cakes/pokebot-gen3/assets/16377135/54f7f774-8cc1-4c6e-a6f7-b8474b66637b

</details>

- For modes that use soft resets such as starters, the bot will track RNG to ensure a unique frame is hit after every reset, this is to prevent repeatedly generating an identical Pokémon, this will cause soft resets to take progressively longer over time
- If resets begin to take too long, it is recommended to start a new save file with a different TID to reset this delay or check out [`profiles/cheats.yml`](#cheatsyml---cheats-config)
- **Note**: Even though you set the trainer to face the desired PokéBall, it is still important to set the correct `starter` in the config! This option is used by the bot to track frames to ensure a unique starter is generated every time
- **Note**: For the time being, Johto starters will automatically enable the `starters` option in [`profiles/cheats.yml`](#cheatsyml---cheats-config), the shininess of the starter is checked via memhacks as start menu navigation is WIP (in future, shininess will be checked via the party summary menu)

### FireRed and LeafGreen (Kanto)
1. Select the `starter` in `profiles/general.yml` - `Bulbasaur`, `Charmander` or `Squirtle`
2. Face the desired PokéBall in Oak's lab, save the game (**in-game, not a save state**)
3. Start the bot

### Emerald (Johto)
1. Select the `starter` in `profiles/general.yml` - `Chikorita`, `Cyndaquil` or `Totodile`
2. Face the desired PokéBall in Birch's lab, save the game (**in-game, not a save state**)
3. Start the bot

### Ruby, Sapphire and Emerald (Hoenn)
1. Select the `starter` in `profiles/general.yml` - `Treecko`, `Torchic` or `Mudkip`
2. Face the starters bag, and save the game (**in-game, not a save state**)
3. Start the bot

<details>
<summary>✅🟨❌ Click here for support information</summary>

|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald | 🔥 FireRed | 🌿 LeafGreen |
|:---------|:-------:|:-----------:|:----------:|:----------:|:------------:|
| English  |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| Japanese |    -    |      -      |     -      |     -      |      -       |
| German   |    -    |      -      |     -      |     -      |      -       |
| Spanish  |    -    |      -      |     -      |     -      |      -       |
| French   |    -    |      -      |     -      |     -      |      -       |
| Italian  |    -    |      -      |     -      |     -      |      -       |
</details>

## 🎣 `fishing`
Start the mode while facing the water, with any fishing rod registered.
<details>
<summary>🎥 Click here to show a video example</summary>

https://github.com/40Cakes/pokebot-gen3/assets/16377135/4317ba99-8854-4ce5-b054-d6bf652c7b28

</details>

<details>
<summary>✅🟨❌ Click here for support information</summary>

|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald | 🔥 FireRed | 🌿 LeafGreen |
|:---------|:----:|:--------:|:-------:|:-------:|:---------:|
| English  |  ✅   |    ✅     |    ✅    |    ✅    |     ✅     |
| Japanese |  -   |    -     |    -    |    -    |     -     |
| German   |  -   |    -     |    -    |    -    |     -     |
| Spanish  |  -   |    -     |    -    |    -    |     -     |
| French   |  -   |    -     |    -    |    -    |     -     |
| Italian  |  -   |    -     |    -    |    -    |     -     |
</details>

## 🚲 `bunny_hop`
Bunny hop on the spot with the [Acro Bike](https://bulbapedia.bulbagarden.net/wiki/Acro_Bike), useful for Safari Zone and [repel tricking](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) as it doesn't count steps.

Start the mode while in the overworld, in any patch of grass/cave, with the Acro Bike registered.
- **Note**: `bunny_hop` is ~10% slower encounters/h on average than `spin` mode

<details>
<summary>🎥 Click here to show a video example</summary>
  
https://github.com/40Cakes/pokebot-gen3/assets/16377135/bedbd712-c57c-4d26-923b-ee3fd314afe3

</details>

<details>
<summary>✅🟨❌ Click here for support information</summary>

|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald |
|:---------|:----:|:--------:|:-------:|
| English  |  ✅   |    ✅     |    ✅    |
| Japanese |  -   |    -     |    -    |
| German   |  -   |    -     |    -    |
| Spanish  |  -   |    -     |    -    |
| French   |  -   |    -     |    -    |
| Italian  |  -   |    -     |    -    |
</details>

***

# 🛠 Configuration
Configuration files are loaded and validated against a schema, once at bot launch. Any changes made while the bot is running will not take effect until the bot is stopped and restarted.

## 🚧 Work in progress 🚧
A lot of the config in `.yml` files is placeholder for future/planned features.

## Multi-instance botting
The bot stores all profile information, such as save games, screenshots, statistics, etc. in the profile `profiles/<profile name>/`) folder, which is automatically created once you create a new profile in the GUI.

Running multiple instances of the bot is as easy as starting the bot multiple times and loading a different profile each time. You should **not** run multiple instances of the bot with the same profile simultaneously!

Statistics are saved into a subfolder of your profile `profiles/<profile name>/stats/`.

The bot will first attempt to load individual config files from your profile folder (`profiles/<profile name>/`), if that folder does not exist or any of the configuration files are missing, it will load the default config file in the `profiles/` folder. This allows you to selectively override specific config files on a per-profile basis.

Example:
```
├── /profiles
    │
    ├── /emerald-profile
    │     current_save.sav
    │     current_state.ss1
    │     discord.yml          <-- config loaded for 'emerald-profile'
    │     general.yml          <-- config loaded for 'emerald-profile'
    │
    ├── /firered-profile
    │     current_save.sav
    │     current_state.ss1
    │     general.yml          <-- config loaded for 'firered-profile'
    │
    │   catch_block.yml        <-- config loaded for all profiles
    │   cheats.yml             <-- config loaded for all profiles
    │   customcatchfilters.py  <-- config loaded for all profiles
    │   customhooks.py         <-- config loaded for all profiles
    │   discord.yml            <-- config loaded for all profiles except 'emerald-profile'
    │   general.yml            <-- config loaded for all profiles except 'emerald-profile' and 'firered-profile'
    │   logging.yml            <-- config loaded for all profiles
    │   obs.yml                <-- config loaded for all profiles
```

## `keys.yml` - Emulator input mapping
This file controls keyboard to GBA button mappings.

- For a full list of available key codes, see [here](https://www.tcl.tk/man/tcl8.4/TkCmd/keysyms.html) or [here](https://anzeljg.github.io/rin2/book2/2405/docs/tkinter/key-names.html) (column `.keysym`)

### Default Input Mapping
- A button: `X`
- B button: `Z`
- D-Pad: Arrow keys (`Up`, `Down`, `Left`, `Right`)
- Start button: `Enter`
- Select button: `Backspace`
- Toggle manual bot mode on/off: `Tab`
- Toggle video output on/off: `V`
- Toggle audio output on/off: `B`
- Zoom window scaling in/out: `+`, `-`
- Create save state: `Ctrl + S`
- Load save state menu: `Ctrl + L`
- Reset emulator/reboot game: `Ctrl + R`
- Exit the bot and emulator: `Ctrl + Q`
- Emulator speed:
  - 1x speed: `1`
  - 2x speed: `2`
  - 3x speed: `3`
  - 4x speed: `4`
  - Unbound: `0` - **⚠ Photosensitivity warning**: this will run the emulator as fast as possible!

## `general.yml` - General config
<details>
<summary>Click to expand</summary>

### General
`bot_mode` - set the bot to automatically launch into a specific mode (see [🤖 Bot Modes](#-bot-modes))

`starter` - used when `bot_mode` set to `starters` (see [💼 starters](#-starters))

</details>

## `logging.yml` - Logging and console output config
<details>
<summary>Click to expand</summary>

### Logging
`log_encounters` - log all encounters to .csv (`stats/encounters/` folder), each phase is logged to a separate file

### Console output
The following `console` options will control how much data is displayed in the Python terminal/console, valid options are `verbose`, `basic` or `disable`
- `encounter_data`
- `encounter_ivs`
- `encounter_moves`
- `statistics`

</details>

## `discord.yml` - Discord integration config

<details>
<summary>Click to expand</summary>

### Discord
For privacy reasons, rich presence and webhooks are **disabled** by default.

### Discord rich presence
`rich_presence` - Rich presence will display information on your Discord profile such as game, route, total encounters, total shinies and encounter rate.

![Discord_tC7ni4A9L4](https://github.com/40Cakes/pokebot-gen3/assets/16377135/ece7cc12-b97a-45cc-a06e-afd679860ce1)

### Discord webhooks
`global_webhook_url` - global Discord webhook URL, default webhook for all Discord webhooks unless specified otherwise
- ⚠ **Warning**: this webhook is considered sensitive! If you leak your webhook, anyone will be able to post in your channel
- **Edit Channel** > **Integrations** > **Webhooks** > **New Webhook** > **Copy Webhook URL** to generate a new webhook

`iv_format` - changes IV formatting displayed in messages, set to `basic` or `formatted`
- `basic`: <br>`HP: 31 | ATK: 31 | DEF: 31  | SPA: 31  | SPD: 31  | SPE: 31`

- `formatted`:
  ```
  ╔═══╤═══╤═══╤═══╤═══╤═══╗
  ║HP │ATK│DEF│SPA│SPD│SPE║
  ╠═══╪═══╪═══╪═══╪═══╪═══╣
  ║31 │31 │31 │31 │31 │31 ║
  ╚═══╧═══╧═══╧═══╧═══╧═══╝
  ```

`bot_id` - set to any string you want, this string is added to the footer of all Discord messages, it can be useful to identify bots if multiple are set to post in the same channel

#### Webhook parameters
`enable` - toggle the webhook on/off

`webhook_url` - set to post specific message types to different channels, defaults to `global_webhook_url` if not set
- Commented out in config file by default, remove the leading `#` to uncomment

Each webhook type also supports pinging @users or @roles.

`ping_mode` - set to `user` or `role`
- Leave blank to disable pings

`ping_id` - set to user/role ID
- **Settings** > **Advanced** > Enable **Developer Mode** to enable Discord developer mode
- Right click **user/role** > **Copy ID**

#### Webhook types
`shiny_pokemon_encounter` - Shiny Pokémon encounters

![Discord_c0jrjiKGRE](https://github.com/40Cakes/pokebot-gen3/assets/16377135/e1706b41-5f89-40b4-918d-30d6e8fa92c2)

`pokemon_encounter_milestones` - Pokémon encounter milestones messages every `interval` encounters

![Discord_ObO28tVrPk](https://github.com/40Cakes/pokebot-gen3/assets/16377135/5c4698f0-07cf-4289-aa4e-6398f56422e0)

`shiny_pokemon_encounter_milestones` - Shiny Pokémon encounter milestones every `interval` encounters

![Discord_w7UfnPxlJZ](https://github.com/40Cakes/pokebot-gen3/assets/16377135/6d6e9b85-c8b4-4c15-8970-eb86e3b712ab)

`total_encounter_milestones` - Total encounter milestones every `interval` encounters

![Discord_ual6ZrsLNm](https://github.com/40Cakes/pokebot-gen3/assets/16377135/f6a82866-fbb3-4192-a771-f0b298bc12ec)

`phase_summary` - Phase summary, first summary at `first_interval`, then every `consequent_interval` after that

![Discord_plUyXtjnQt](https://github.com/40Cakes/pokebot-gen3/assets/16377135/573a638b-fe4e-4f16-95dd-31f0f750a517)

`anti_shiny_pokemon_encounter` - Anti-shiny Pokémon encounters
- Anti-shinies are just a bit of fun, they are mathematically, the complete opposite of a shiny
- An [SV](https://bulbapedia.bulbagarden.net/wiki/Personality_value#Shininess) of `65,528 - 65,535` is considered anti-shiny

![Discord_G2hvTZG21a](https://github.com/40Cakes/pokebot-gen3/assets/16377135/3f04d1cf-4040-4163-80d2-13cac84eed1f)

</details>

## `catch_block.yml` - Catch block config
<details>
<summary>Click to expand</summary>

### Block list
A list of shinies to skip catching, useful if you don't want to fill up your PC with very common encounters.

`block_list` - list of Pokémon to skip catching, example:
```
block_list:
  - Poochyena
  - Pidgey
  - Rattata
```

- **Note**: phase stats will still be reset after encountering a shiny on the block list.
- The block list is reloaded by the bot after every shiny encounter, so you can modify this file while the bot is running!

</details>

## `cheats.yml` - Cheats config
<details>
<summary>Click to expand</summary>

### Cheats
Perform actions not possible by a human, such as peeking into eggs to check shininess, knowing instantly which route a roamer is on, instantly locate Feebas tiles etc.

RNG manipulation options may be added to the bot in the future, all cheats are disabled by default.

`starters` - soft reset as soon as possible after receiving the starter Pokémon, this will bypass slow battle/menu animations, saving time

`starters_rng` - inject a random value into `gRngValue` before selecting a starter Pokémon
- Removes all delays before selecting a starter Pokémon, preventing resets from progressively slowing down over time as the bot waits for unique frames
- Gen3 Pokémon games use predictable methods to seed RNG, this can cause the bot to find identical PID Pokémon repeatedly after every reset (which is why RNG manipulation is possible), see [here](https://blisy.net/g3/frlg-starter.html) and [here](https://www.smogon.com/forums/threads/rng-manipulation-in-firered-leafgreen-wild-pok%C3%A9mon-supported-in-rng-reporter-9-93.62357/) for more technical information
- Uses Python's built-in [`random`](https://docs.python.org/3/library/random.html) library to generate and inject a 'more random' (still pseudo-random) 32-bit integer into the `gRngValue` memory address, essentially re-seeding the game's RNG

</details>

## `obs.yml` - OBS config

<details>
<summary>Click to expand</summary>

### OBS
#### OBS WebSocket Server Settings
The `obs_websocket` config will allow the bot to send commands to OBS via WebSockets,
see [here](https://github.com/obsproject/obs-websocket) for more information on OBS WebSockets.

Enable WebSockets in **OBS** > **Tools** > **Websocket Server Settings** > **Enable WebSocket Server**

`host` - hostname/IP address OBS WebSockets is listening on

`port` - TCP port OBS WebSockets is listening on

`password` - password to authenticate to WebSocket server (**required**)

#### OBS WebSocket Parameters
`shiny_delay` - delay catching a shiny encounter by `n` frames, useful to give you viewers some time to react before saving a replay

`discord_delay` - delay Discord webhooks by `n` seconds, prevent spoilers if there is a stream delay

`screenshot` - take OBS screenshot of shiny encounter
- **Note**: **OBS** > **Settings** > **Hotkeys** > **Screenshot Output** must be set to **Ctrl + F11**
- The bot does **not** emulate keystrokes, it simply sends a `TriggerHotkeyByKeySequence` (**Ctrl + F11**) WebSocket command
- Screenshot is taken after `shiny_delay` to allow stream overlays to update

`replay_buffer` - save OBS replay buffer after `replay_buffer_delay`
- **Note**: **OBS** > **Settings** > **Hotkeys** > **Replay Buffer** > **Save Replay** must set to **Ctrl + F12**
- The bot does **not** emulate keystrokes, it simply sends a `TriggerHotkeyByKeySequence` (**Ctrl + F12**) WebSocket command

`replay_buffer_delay` - delay saving OBS replay buffer by `n` seconds
- Runs in a separate thread and will not pause main bot thread
- If the replay buffer is long enough, it will also capture some encounters after the shiny encounter

`discord_webhook_url` - Discord webhook URL to post OBS `screenshot`, after a shiny encounter

`replay_dir` - OBS screenshot/replay buffer folder
- **OBS** > **Settings** > **Output** > **Recording** > **Recording Path**
- Relative folder to `pokebot.py`, this is used to post stream `screenshot` to Discord if `discord_webhook_url` is set

### Web server
The `http_server` config will enable a Flask HTTP server, which can be used to retrieve data and drive stream overlays.

`enable` - toggle web server on/off

`ip` - IP address for server to listen on

`port` - TCP port for server to listen on
- Port must be unique for each bot instance

#### HTTP Endpoints
All HTTP responses are in JSON format.

`GET /trainer` - returns trainer information such as name, TID, SID, map bank, map ID, X/Y coordinates etc.

`GET /items` - returns all a list of all items in the bag and PC, and their quantities

`GET /party` - returns a detailed list of all Pokémon in the party

`GET /encounter_log` returns a detailed list of the recent 10 Pokémon encounters

`GET /shiny_log` returns a detailed list of all shiny Pokémon encounters (`shiny_log.json`)

`GET /encounter_rate` returns the current encounter rate (encounters per hour)

`GET /stats` returns the phase and total statistics (`totals.json`)

</details>

***

# ⏩ Tips/Tricks
## Optimal game settings

- Set **TEXT SPEED** to **FAST**
- Set **BATTLE SCENE** to **OFF**
- Utilise [repel tricks](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) to boost encounter rates of target Pokémon
- Using `bot_mode` `spin` or `bunny_hop` and repels will become effectively infinite + steps won't be counted in Safari Zone
- Use a lead Pokémon with encounter rate boosting [abilities](https://bulbapedia.bulbagarden.net/wiki/Category:Abilities_that_affect_appearance_of_wild_Pok%C3%A9mon), such as **[Illuminate](https://bulbapedia.bulbagarden.net/wiki/Illuminate_(Ability))**
- Use a lead Pokémon with a [short cry](https://docs.google.com/spreadsheets/d/1rmtNdlIXiif1Sz20i-9mfhFdoqb1VnAOIntlr3tnPeU)
- Use a lead Pokémon with a single character nickname
- Don't use a shiny lead Pokémon (shiny animation takes a few frames at the start of every battle)

***

# 🐛 Debugging

The bot supports auto-starting a profile and can also be launched into a 'debug' mode which can aid bot development.

```
python pokebot.py my-profile          starts the 'my-profile' profile
python pokebot.py my-profile --debug  starts the 'my-profile' profile in debug mode
python pokebot.py --debug             starts the profile selection screen in debug mode
```

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
