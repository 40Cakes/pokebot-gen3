🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 💼 Starters Mode

Soft resets for starter Pokémon.

- For modes that use soft resets such as starters, the bot will track RNG to ensure a unique frame is hit after every reset, this is to prevent repeatedly generating an identical Pokémon, this will cause soft resets to take progressively longer over time
- If resets begin to take too long, it is recommended to start a new save file with a different TID to reset this delay or check out [💎 Cheats](Configuration%20-%20Cheats.md) (`random_soft_reset_rng`)
- **Note**: For the time being, Johto starters will automatically enable the `starters` option in [💎 Cheats](Configuration%20-%20Cheats.md), the shininess of the starter is checked via memhacks as start menu navigation is WIP (in future, shininess will be checked via the party summary menu)

## FireRed and LeafGreen (Kanto)
![](../../sprites/pokemon/shiny/Bulbasaur.png)
![](../../sprites/pokemon/shiny/Charmander.png)
![](../../sprites/pokemon/shiny/Squirtle.png)

- Face the desired PokéBall in Oak's lab
- Save the game (**in-game, not a save state**)
- Select `Starters` mode
- Select `Bulbasaur`, `Charmander` or `Squirtle` from the selection menu

## Emerald (Johto)
![](../../sprites/pokemon/shiny/Chikorita.png)
![](../../sprites/pokemon/shiny/Cyndaquil.png)
![](../../sprites/pokemon/shiny/Totodile.png)

- Face the desired PokéBall in Birch's lab
- Save the game (**in-game, not a save state**)
- Select `Starters` mode
- Select `Chikorita`, `Cyndaquil` or `Totodile` from the selection menu

## Ruby, Sapphire and Emerald (Hoenn)
![](../../sprites/pokemon/shiny/Treecko.png)
![](../../sprites/pokemon/shiny/Torchic.png)
![](../../sprites/pokemon/shiny/Mudkip.png)

- Face the starters bag on Route 101
- Save the game (**in-game, not a save state**)
- Select `Starters` mode
- Select `Treecko`, `Torchic` or `Mudkip` from the selection menu

## Game Support
|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald | 🔥 FireRed | 🌿 LeafGreen |
|:---------|:-------:|:-----------:|:----------:|:----------:|:------------:|
| English  |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| Japanese |    ❌    |      ❌      |     ✅      |     ❌      |      ❌       |
| German   |    ❌    |      ❌      |     ✅      |     ❌      |      ❌       |
| Spanish  |    ❌    |      ❌      |     ✅      |     ❌      |      ❌       |
| French   |    ❌    |      ❌      |     ✅      |     ❌      |      ❌       |
| Italian  |    ❌    |      ❌      |     ✅      |     ❌      |      ❌       |

✅ Tested, working

🟨 Untested, may not work

❌ Untested, not working