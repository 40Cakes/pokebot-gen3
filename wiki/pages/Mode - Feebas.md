🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🐟 Feebas Mode

![](../../sprites/pokemon/normal/Feebas.png)

Feebas mode will search for the illusive fish by navigating to and fishing on all tiles in the current body of water. Once Feebas is found, the bot will stay at the tile and continue to hunt for shiny Feebas.

Notes:
- There are 2 large lakes of water on Route 119, the bot will only hunt on the lake it is started on and will not automatically move to a different lake
- Navigating under the bridges that are over the water is currently an issue, it is not recommended to start the bot north of the bridge
- The bot will not automatically travel up the waterfall

Each tile will be fished on `3` times, meaning if Feebas is not encountered on a particular tile, the tile can be ruled out with `87.5%` confidence.

| Encounters | Confidence |
|------------|------------|
| `1`        | `50%`      |
| `2`        | `75%`      |
| `3`        | `87.5%`    |
| `4`        | `93.75%`   |
| `5`        | `96.875%`  |

- Have any fishing rod (the bot will automatically register one to `Select` button)
- Place the player on any body of water (surf) on Route 119 and face a fishable tile
- Start mode

## Route 119

The lakes marked in red are highly likely to contain a Feebas tile.

| Ruby/Sapphire                          | Emerald                         |
|----------------------------------------|---------------------------------|
| ![](../images/feebas_route_119_rs.png) | ![](../images/feebas_route_119_e.png)  |

# Game Support
|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald |
|:---------|:-------:|:-----------:|:----------:|
| English  |   🟨    |     🟨      |     ✅      |
| Japanese |    ❌    |      ❌      |     ❌      |
| German   |    ❌    |      ❌      |     ❌      |
| Spanish  |    ❌    |      ❌      |     ❌      |
| French   |    ❌    |      ❌      |     ❌      |
| Italian  |    ❌    |      ❌      |     ❌      |

✅ Supported (tested)

🟨 Supported (not tested)

❌ Not supported
