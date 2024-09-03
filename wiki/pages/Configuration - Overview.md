🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🛠 Configuration Overview

The bot stores all profile information, such as save games, screenshots, statistics, etc. in the profile `./profiles/<profile name>/`) folder, which is automatically created once you create a new profile.

Encounter statistics are saved into a sub-folder of your profile as `./profiles/<profile name>/stats/totals.json`.

Default configurations can be overridden by creating a copy of config files inside a profile folder.

Most configuration files are in `yml` format and are loaded and validated against a schema at bot launch. Changes made while the bot is running must be reloaded (default mapping is `Ctrl + C`.

The wiki page for each configuration file will describe all options that are available, examples and defaults will also be shown.

Example:
```
├── /profiles
    │
    ├── /emerald-profile
    │     current_save.sav
    │     current_state.ss1
    │     discord.yml          <-- config loaded for 'emerald-profile'
    │     logging.yml          <-- config loaded for 'emerald-profile'
    │
    ├── /firered-profile
    │     current_save.sav
    │     current_state.ss1
    │     logging.yml          <-- config loaded for 'firered-profile'
    │
    │ catch_block.yml          <-- config loaded for all profiles
    │ cheats.yml               <-- config loaded for all profiles
    │ customcatchfilters.py    <-- config loaded for all profiles
    │ customhooks.py           <-- config loaded for all profiles
    │ discord.yml              <-- config loaded for all profiles except 'emerald-profile'
    │ logging.yml              <-- config loaded for all profiles except 'emerald-profile' and 'firered-profile'
    │ http.yml                  <-- config loaded for all profiles
```
