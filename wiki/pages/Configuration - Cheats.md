🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 💎 Cheats Config

[`profiles/cheats.yml`](../../modules/config/templates/cheats.yml)

> Cheats may be removed in the near future, as they go against the bot philosophy and add unnecessary complexity to many modes.

Cheats will cause the bot to perform actions not possible by a human, such as peeking into eggs to check shininess, knowing instantly which route a roamer is on, instantly locate Feebas tiles etc.

RNG manipulation options may be added to the bot in the future, all cheats are disabled by default.

`random_soft_reset_rng` - advances `gRngValue` to the next unique value while using soft-reset methods
- Removes all delays before selecting the Pokémon, preventing resets from progressively slowing down over time as the bot waits for unique frames
- Gen3 Pokémon games use predictable methods to seed RNG, this can cause the bot to find identical PID Pokémon repeatedly after every reset (which is why RNG manipulation is possible), see [here](https://blisy.net/g3/frlg-starter.html) and [here](https://www.smogon.com/forums/threads/rng-manipulation-in-firered-leafgreen-wild-pok%C3%A9mon-supported-in-rng-reporter-9-93.62357/) for more technical information

`frlg_starter_rng_manipulation` - FireRed/LeafGreen [Starters](Mode%20-%20Starters.md) mode only: instead of soft resetting until a shiny appears, wait in front of the starter for a frame whose RNG value will produce a shiny, then confirm the selection
- Does not write to memory (`random_soft_reset_rng` is not used while this is enabled), this is the same as a human RNG manipulating with a timer, the resulting Pokémon is legitimate
- Usually finds a shiny within a few minutes of emulation at max speed instead of thousands of resets
- The timing between confirming and the starter being generated can differ between game revisions, languages and text speed settings; the bot re-measures it after every attempt and adjusts automatically
- If no such frame is found after ~10x the expected wait, the bot confirms anyway and soft resets as usual

`frlg_starter_natures` - list of natures to accept when `frlg_starter_rng_manipulation` is enabled, e.g. `[Modest, Timid]`, leave empty (`[]`) to accept any nature

`faster_pickup` - read memory directly instead of manually checking the party menu for pickup items, if pickup mode is enabled
