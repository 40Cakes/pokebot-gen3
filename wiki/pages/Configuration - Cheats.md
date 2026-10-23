🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 💎 Cheats Config

[`profiles/cheats.yml`](../../modules/config/templates/cheats.yml)

> Cheats may be removed in the near future, as they go against the bot philosophy and add unnecessary complexity to many modes.

Cheats will cause the bot to perform actions not possible by a human, such as peeking into eggs to check shininess, knowing instantly which route a roamer is on, instantly locate Feebas tiles etc.

RNG manipulation options may be added to the bot in the future, all cheats are disabled by default.

`random_soft_reset_rng` - advances `gRngValue` to the next unique value while using soft-reset methods
- Removes all delays before selecting the Pokémon, preventing resets from progressively slowing down over time as the bot waits for unique frames
- Gen3 Pokémon games use predictable methods to seed RNG, this can cause the bot to find identical PID Pokémon repeatedly after every reset (which is why RNG manipulation is possible), see [here](https://blisy.net/g3/frlg-starter.html) and [here](https://www.smogon.com/forums/threads/rng-manipulation-in-firered-leafgreen-wild-pok%C3%A9mon-supported-in-rng-reporter-9-93.62357/) for more technical information
- In [Rock Smash mode](Mode%20-%20Rock%20Smash.md) (Emerald), also skips the random waiting time on the 'Would you like to use Rock Smash?' question by advancing the RNG directly

`faster_pickup` - read memory directly instead of manually checking the party menu for pickup items, if pickup mode is enabled
