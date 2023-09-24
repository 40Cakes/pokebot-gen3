# PokéBot Gen3 for mGBA

**PokéBot Gen3 for mGBA** is a Python script, written to automatically shiny hunt in Pokémon Ruby, Sapphire, Emerald, FireRed and LeafGreen.

Initially created to complete a Prof. Oak and Living ✨Shiny✨ Dex Challenge in Pokémon Emerald, a 🔴24/7 livestream of the challenge can be found ongoing [here](https://www.youtube.com/watch?v=W6OOnrx8g58).

[![🔴24/7✨Shiny✨Hunting Bot](https://img.youtube.com/vi/W6OOnrx8g58/0.jpg)](https://www.youtube.com/watch?v=W6OOnrx8g58)

https://github.com/40Cakes/pokebot-gen3/assets/16377135/a3eed994-e960-4181-9f76-3b36bc9f0619

# 📖 Preamble

Although the bot is essentially frame perfect, (by default) it will attempt to perform most actions, as if a human were playing to make shiny hunts as representative as possible, some examples:
- Starter Pokémon are generated just _1 frame_ after confirming the starter selection, the bot will wait until the battle begins, and the starter Pokémon sprite is visible
- It's possible to peek inside un-hatched eggs to view stats and shininess as soon as they're received from the daycare, the bot will wait until the eggs are fully hatched before checking and logging
- These are intentional design decisions, bot [cheats](#cheatsyml---cheats-config) can be used to bypass them (in most cases)

This project is the result of a bored holiday, I am by no means a professional Python developer, so I apologise for the very scuffed code you have just stumbled upon. This was a huge learning experience, and it goes without saying that this code comes with no warranty™.

***
# ⚠ Photosensitivity Warning
- Running mGBA at unbounded speeds, will cause **very fast and bright flashing**!
- mGBA can run well over 3,000 FPS on fast enough PCs
- Any unbounded video examples on this page will be hidden by default, and marked with **⚠ photosensetivity warning ⚠**

***

# 🔒 Requirements
- Windows (support for Mac and Linux **_may_** be added later)
- [Python 3.11](https://www.python.org/downloads/)
- Double click `requirements.py` or run `python -m pip install -r requirements.txt` in a terminal to install required Python modules
- [mGBA 0.10.2 (64-bit)](https://mgba.io/downloads.html)
  - **Windows (*64-bit*, installer .exe)** or **Windows (*64-bit*, portable .7z archive)**
- [Windows Terminal](https://github.com/microsoft/terminal/releases) (not **required**, but highly recommended for full 16-million <span style="color:#FF0000">c</span><span style="color:#FF7F00">o</span><span style="color:#FFFF00">l</span><span style="color:#00FF00">o</span><span style="color:#00FFFF">u</span><span style="color:#CF9FFF">r</span> console output)

***

# ❓ How To Run
⚠ **Warning**: The bot will write directly to the running `mGBA.exe` process' memory, so there is a good chance that mGBA may crash, be sure to save regularly and run at your own risk!

- Set the desired `bot_mode` in config file `config/general.yml`
- Load a ROM and place the trainer where it needs to be for the `bot_mode` you've configured
- Double click `pokebot.py` or run `python .\pokebot.py` in a terminal, then click on any mGBA process to attach the bot

At the moment, the bot will pause once a shiny is encountered. You **must** ensure you are able to escape battle **100% of the time**, otherwise the bot will get stuck. Auto-catching and other features will be added in due time.

- This is still in *early* development, as such, stats/config format and general functionality will be subject to change, without warning - make sure you back up your `stats/` and `config/` before updating your bot local version!
- Reach out in Discord [#mgba-testing🧪](https://discord.com/channels/1057088810950860850/1139190426834833528) if you have any issues

***

#  🌍 Supported Games and Languages

Variations of games, languages and revisions may have different memory offsets, there will be a table of supported/tested variations under each bot mode listed below.

- ✅ Supported (tested)
- 🟨 Supported (not tested)
- ❌ Not supported

ROM hacks will not work, and are ❌ **not supported** or planned to be supported!

***

# 🤖 Bot Modes
Modify the `bot_mode` paramater in `config/general.yml` to any of the following modes.
***
## 🔧 `manual`
Manual mode simply disables all bot inputs, allowing you to track encounters and stats on your own shiny hunts as you play the game normally.

## 🔄 `spin`
Start the bot while in the overworld, in any patch of grass/water/cave.
The bot will mash random directions to spin on a single tile.
- `spin` mode is useful for Safari Zone and [repel tricking](https://bulbapedia.bulbagarden.net/wiki/Appendix:Repel_trick) as it doesn't count steps!

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

## 💼 `starters`
Soft reset for starter Pokémon.

For modes that use soft resets such as starters, the bot attempts to hit a unique frames to reduce the amount of repeated, identical Pokémon, this may cause soft resets to take progressively longer.

- If resets begin to take too long, it is recommended to start a new save file with a different TID to reset this delay
- If you notice too many dupes or resets taking too long, consider enabling `starters_rng` in [`config/cheats.yml`](#cheatsyml---cheats-config)

### R/S/E
1. Select the `starter` in `config/general.yml` - `treecko`, `torchic` or `mudkip`
2. Face the starters bag, and save the game (**in-game, not a save state**)
3. Start the bot

### FR/LG
1. Select the `starter` in `config/general.yml` - `bulbasaur`, `charmander` or `squirtle`
2. Face the desired PokéBall in Oak's lab, save the game (**in-game, not a save state**)
3. Start the bot

- **Note**: Even though you set the trainer to face the desired PokéBall, it is still important to set `starter` in the config! This option is used by the bot to track frames to ensure a unique starter is generated every time

### Johto (Emerald)
1. Select the `starter` in `config/general.yml` - `chikorita`, `cyndaquil` or `totodile`
2. Face the desired PokéBall in Birch's lab, save the game (**in-game, not a save state**)
3. Start the bot

- **Note**: Even though you set the trainer to face the desired PokéBall, it is still important to set `starter` in the config! This option is used by the bot to track frames to ensure a unique starter is generated every time
- **Note**: For the time being, Johto starters will automatically enable the `starters` option in [`config/cheats.yml`](#cheatsyml---cheats-config), the shininess of the starter is checked via memhacks as start menu navigation is WIP (in future, shininess will be checked via the party summary menu)

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
Start the bot facing the water, with any fishing rod registered.

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

***

# 🛠 Configuration
Configuration files are loaded and validated against a schema, once at bot launch. Any changes made while the bot is running will not take effect until the bot is stopped and restarted.

## 🚧 Work in progress 🚧

A lot of the config in `.yml` files is is placeholder for future/planned features.

## Multi-instance botting
Statistics are saved into subdirectories, per-game and trainer ID (`stats/<game_code>/<trainer_id>-<trainer_name>/`) so you can run as many instances as you want, from a single folder!

The bot will first attempt to load config files from `config/<game_code>/<trainer_id>-<trainer_name>/` (automatically created), otherwise it will default to the config files in the root `config/` folder; this allows you to run separate bot instances with different config.

Example:
```
├── /config
    │   battle.yml             <-- loaded for all saves
    │   catch_block.yml        <-- loaded for all saves
    │   cheats.yml             <-- loaded for all saves
    │   CustomCatchFilters.py  <-- loaded for all saves
    │   CustomHooks.py         <-- loaded for all saves
    │   discord.yml            <-- loaded for all saves except Emerald (TID 52963)
    │   general.yml            <-- loaded for all saves except Emerald (TID 52963) and FireRed (TID 39167)
    │   logging.yml            <-- loaded for all saves
    │   obs.yml                <-- loaded for all saves
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
## `general.yml` - General config

<details>
<summary>Click to expand</summary>

### General
`bot_mode` - set to desired mode (see [🤖 Bot Modes](#-bot-modes))

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

### Backups
`backup_stats` - zips up and backup `stats/` folder every `n` total encounters
- Files in `stats/` are known to get corrupted during power outages
- Backups are stored in `backups/`
- Make sure you regularly delete old backups (especially if your stats folder is large!)
- Set to `0` to disable

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

`discord_delay` - delay Discord webhooks by `n` frames, prevent spoilers if there is a stream delay

`screenshot` - take OBS screenshot of shiny encounter
- **Note**: **OBS** > **Settings** > **Hotkeys** > **Screenshot Output** must be set to **Ctrl + F11**
- The bot does **not** emulate keystrokes, it simply sends a `TriggerHotkeyByKeySequence` (**Ctrl + F11**) WebSocket command 
- Screenshot is taken after `shiny_delay` to allow stream overlays to update

`replay_buffer` - save OBS replay buffer after `replay_buffer_delay`
- **Note**: **OBS** > **Settings** > **Hotkeys** > **Replay Buffer** > **Save Replay** must set to **Ctrl + F12**
- The bot does **not** emulate keystrokes, it simply sends a `TriggerHotkeyByKeySequence` (**Ctrl + F12**) WebSocket command 

`replay_buffer_delay` - delay saving OBS replay buffer by `n` frames
- Runs in a separate thread and will not pause main bot thread
- If the replay buffer is long enough, it will also capture some encounters after the shiny encounter

`discord_webhook_url` - Discord webhook URL to post OBS `screenshot`, after a shiny encounter

`replay_dir` - OBS screenshot/replay buffer directory
- **OBS** > **Settings** > **Output** > **Recording** > **Recording Path**
- Relative directory to `pokebot.py`, this is used to post stream `screenshot` to Discord if `discord_webhook_url` is set

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

`GET /encounter_log` returns a detailed list of the recent 250 Pokémon encounters (`encounter_log.json`)

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
- Use a lead Pokémon with a short cry
- Use a lead Pokémon with a single character nickname
- Use a non-shiny lead Pokémon (shiny animation takes a few frames)


## Optimal mGBA settings

- **Settings** > **Emulation** > **Idle loops** > **Detect and remove**
  - **Massively** increases unbounded frame rate
  - Decreases emulation accuracy (if you care about that)
  - ⚠ **Warning**: don't use this for `starters` mode (unless you are using the [cheat config](#cheatsyml---cheats-config) `starters_rng`) or any other mode that uses soft resets, you may get many repeated, identical PIDs!


- **Settings** > **Emulation** > **Rewind history** > Untick **Enable rewind**
  - Slightly increases unbounded frame rate


- **Settings** > **Emulation** > Tick **Preload entire ROM into memory**
  - Mostly only relevant if you have a hard drive and not an SSD, not a hugely relevant option for most


- **Audio/Video** > **Mute**
- **Audio/Video** > **Audio channels** > **Disable all**
  - Slightly increases unbound frame rate


- **Audio/Video** > **Video layers** > **Disable all**
  - Slightly increases unbound frame rate (at the cost of not being able to see anything!)

***
# ❤ Attributions

This project would not be possible without the symbols tables from the Pokémon decompilation projects:

- [Pokémon Emerald](https://github.com/pret/pokeemerald) ([symbols](https://github.com/pret/pokeemerald/tree/symbols))
- [Pokémon Ruby and Sapphire](https://github.com/pret/pokeruby) ([symbols](https://github.com/pret/pokeruby/tree/symbols))
- [Pokémon FireRed and LeafGreen](https://github.com/pret/pokefirered) ([symbols](https://github.com/pret/pokefirered/tree/symbols))
