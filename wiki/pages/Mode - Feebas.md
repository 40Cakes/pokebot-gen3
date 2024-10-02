🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🐟 Feebas Mode

![](../../modules/web/static/sprites/pokemon/shiny/Feebas.png)

[Feebas](https://bulbapedia.bulbagarden.net/wiki/Feebas_(Pok%C3%A9mon)) mode will search for the illusive fish by
navigating to and fishing on all tiles in the water on Route 119.

Once found, the bot will stay at that tile and continue to hunt for shiny.

Fishing spots where Feebas can appear are randomly generated in Generation 3.
In Ruby, Sapphire, and Emerald they randomly change whenever the [trend](https://bulbapedia.bulbagarden.net/wiki/Trend)
in [Dewford Town](https://bulbapedia.bulbagarden.net/wiki/Dewford_Town) changes, or after one (real-time!) day passes.

## Requirements

- Go to Route 119 and start surfing on the water.
- Have a fishing rod in your inventory.
- Have the Rain Badge and a Pokémon that knows Waterfall. That way, the bot can also search
  the water tiles above of the waterfall in the north of that route. If you don't have the
  ability to use that HM, these tiles will be skipped.

## Recommendations

- (on Emerald) The first Pokémon in the party should have the ability [Sticky Hold](https://bulbapedia.bulbagarden.net/wiki/Sticky_Hold_(Ability)) or
  [Suction Cups](https://bulbapedia.bulbagarden.net/wiki/Suction_Cups_(Ability)) to increase the bite rate while fishing. This Pokémon can be fainted,
  it just needs to be in the first slot.
- Use the Old Rod (if you own it, the bot will automatically register it to the `Select`
  button.) This rod has the advantage of immediately starting an encounter as soon as you
  get a bite.

## Notes

Each tile will be fished on `3` times, meaning if Feebas is not encountered on a particular
tile, the tile can be ruled out with `87.5%` confidence.

| Encounters | Confidence |
|------------|------------|
| `1`        | `50%`      |
| `2`        | `75%`      |
| `3`        | `87.5%`    |
| `4`        | `93.75%`   |
| `5`        | `96.875%`  |

## Route 119

The lakes marked in red are highly likely to contain a Feebas tile.

| Ruby/Sapphire                          | Emerald                               |
|----------------------------------------|---------------------------------------|
| ![](../images/feebas_route_119_rs.png) | ![](../images/feebas_route_119_e.png) |

## Game Support

|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald |
|:---------|:-------:|:-----------:|:----------:|
| English  |    ✅    |      ✅      |     ✅      |
| Japanese |    ❌    |      ❌      |     🟨      |
| German   |    ❌    |      ❌      |     ✅      |
| Spanish  |    ❌    |      ❌      |     ✅      |
| French   |    ❌    |      ❌      |     ✅      |
| Italian  |    ❌    |      ❌      |     ✅      |

✅ Tested, working

🟨 Untested, may not work

❌ Untested, not working
