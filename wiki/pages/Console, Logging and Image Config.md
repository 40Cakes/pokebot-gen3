🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 📄 Console, Logging and Image Config

[`profiles/logging.yml`](../../profiles/logging.yml.dist)

This file allows you to enable or disable features of the bot that may generate data or images, such as .csv data logging, .pk3 dumping or shiny GIFs.

## Logging
### Options
`log_encounters` - log all encounters to .csv (`./profile/<profile_name>/stats/encounters/` folder), each phase is logged to a separate file

`desktop_notifications` - Show a desktop notification if a shiny, roamer, or Pokémon matching your
Custom Catch Filters is encountered, or the bot is switched to manual mode.

### Console output
Console options will control how much data is displayed in the Python terminal/console, valid options are `verbose`, `basic` or `disable`.

`console`:
- `encounter_data`
- `encounter_ivs`
- `encounter_moves`
- `statistics`

## Save raw Pokémon data (.pk3)
The bot can dump individual Pokémon files (.pk3 format) to be managed/transferred in the [PKHeX save editor](https://github.com/kwsch/PKHeX).

The Pokémon are dumped to the `./profile/<profile_name>/stats/pokemon/` folder, in the following format:

`273 ★ - SEEDOT - Modest [180] - C88CF14B19C6.pk3` (`<nat_dex_num> <shiny ★> - <mon_name> - <nature> [<IV sum>] - <pid>.pk3`)

### Options
`save_pk3`:
- `all` - dump all encounters
- `shiny` - dump shiny encounters
- `custom` - dump custom catch filter encounters
- `roamer` - dump (non-shiny) roamers (Latias, Latios, Entei, Suicune, Raikou) -- this will only be done
  if the Pokémon is not yet marked as 'seen' in the Pokédex

Feel free to share any rare/interesting .pk3 files in [#pkhexchange💱](https://discord.com/channels/1057088810950860850/1123523909745135616)!

## Shiny GIFs
Capture and save a GIF of shiny encounters, example GIF below. If shiny [Discord webhooks](Configuration%20-%20Discord%20Integration.md) are enabled, the GIF will also be added to the webhook!

Shiny GIFs are saved to the `./profile/<profile_name>/screenshots/gif/` folder.

### Options
`shiny_gifs` - capture and save a GIF of shiny encounters

![image](../images/shiny.gif)

## TCG Cards
Creates fun (fake) TCG cards for all shiny encounters and shiny evolutions, example card below.

TCG cards are saved to the `./profile/<profile_name>/screenshots/cards/` folder.

- The card theme is based on the encounter's primary type
- Shinies are denoted by the shiny stars (top right)
- Origin game is denoted by the coloured shape (top right):
  - Blue square: Sapphire
  - Red square: Ruby
  - Green square: Emerald
  - Orange circle: FireRed
  - Green circle: LeafGreen
- National dex number (`004 / 386`) is bottom right of portrait
- The cyan exp bar is based on the encounter's % of max IV sum (186)

### Options
`tcg_cards` - Create TCG cards for shiny encounters

![image](../images/tcg_example.png)
