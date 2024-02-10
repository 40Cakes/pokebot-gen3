🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 📄 Logging and Console Output Config

[`profiles/logging.yml`](https://github.com/40Cakes/pokebot-gen3/blob/main/profiles/logging.yml)

This file allows you to control logging certain data to files and the output of the terminal window.

## Logging
### Options
`log_encounters` - log all encounters to .csv (`stats/encounters/` folder), each phase is logged to a separate file

### Console output
Console options will control how much data is displayed in the Python terminal/console, valid options are `verbose`, `basic` or `disable`.

`console`:
- `encounter_data`
- `encounter_ivs`
- `encounter_moves`
- `statistics`

## Save raw Pokémon data (.pk3)
The bot can dump individual Pokémon files (.pk3 format) to be managed/transferred in the [PKHeX save editor](https://github.com/kwsch/PKHeX).

The Pokémon are dumped to the `pokemon/` folder in your profile, in the following format:

`273 ★ - SEEDOT - Modest [180] - C88CF14B19C6.pk3` (`<nat_dex_num> <shiny ★> - <mon_name> - <nature> [<IV sum>] - <pid>.pk3`)

### Options
`save_pk3`:
- `all` - dump all encounters
- `shiny` - dump shiny encounters
- `custom` - dump custom catch filter encounters
- `roamer` - dump (non-shiny) roamers (Latias, Latios, Entei, Suicune, Raikou) -- this will only be done
  if the Pokémon is not yet marked as 'seen' in the Pokédex

Feel free to share any rare/interesting .pk3 files in [#pkhexchange💱](https://discord.com/channels/1057088810950860850/1123523909745135616)!
