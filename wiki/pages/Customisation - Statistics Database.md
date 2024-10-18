🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 📊 Statistics Database

The bot stores its statistics in an sqlite3 database. This file can be found in the
profile directory, at `profiles/<profile name>/stats.db`.

This contains 4 main tables:

- **encounters** contains information about encountered Pokémon. If `log_encounters` is
  enabled (see [the Wiki page on logging](Console,%20Logging%20and%20Image%20Config.md)),
  this will contain _all_ encountered Pokémon. Otherwise it just contains shinies,
  roaming Pokémon as well as Pokémon that matched a custom catch filter.
- **shiny_phases** contains information about Shiny Phases, etc. the time periods between
  two shiny encounters.
- **encounter_summaries** contains information for each species (and in case of Unown, for
  each single letter) the bot has encountered in this profile and so can answer questions
  like 'How many Seedot have we encountered in total?' By summing all those individual
  species entries you get the total stats.
- **pickup_items** contains a list of items that have been acquired using the Pickup ability,
  and how many of them have been picked up so far.
