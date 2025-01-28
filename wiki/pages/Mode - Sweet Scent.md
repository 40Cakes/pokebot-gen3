🍂 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🔄 Sweet Scent Mode

Sweet Scent will make a wild Pokémon automatically appear.

Make sure you have a Pokémon that knows **[Sweet Scent](<https://bulbapedia.bulbagarden.net/wiki/Sweet_Scent_(move)>)** in your party.

Start the mode while in the overworld, in any patch of grass/water/cave with encounters.

## Safari Zone

### Ruby / Sapphire / Emerald
The `auto_catch` Safari strategy for `Ruby` / `Sapphire` / `Emerald` is designed using an in-depth
[study](https://www.docdroid.net/oiHhrwd/hoenn-safari-zone-research-pdf), which calculate the most effective Pokéblock and Safari ball sequence for catching a Pokémon based on the Pokémon encountered.
The bot will use your Pokéblock case if you have some available to perform the strategy, or throw balls until the target is captured.

### Fire Red / Leaf Green

The `auto_catch` Safari strategy for `Fire Red` and `Leaf Green` is designed using an in-depth
[study](https://www.docdroid.net/Tx5NbeU/safari-zone-research-pdf),
which calculate the most effective sequence for catching a Pokémon based on both the Pokémon encountered and
the number of Safari Balls remaining at the start of the encounter.
The bot will use the best possible bait / ball strategy until the target is captured.

The bot uses optimal catch patterns, which are available in these
[lookup tables](https://www.docdroid.net/g3I5Qtl/frlg-lookup-tables-pdf), to maximize catch rates for each Pokémon.

## Game Support

|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald | 🔥 FireRed | 🌿 LeafGreen |
|:---------|:-------:|:-----------:|:----------:|:----------:|:------------:|
| English  |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| Japanese |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| German   |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| Spanish  |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| French   |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |
| Italian  |    ✅    |      ✅      |     ✅      |     ✅      |      ✅       |

✅ Tested, working

🟨 Untested, may not work

❌ Untested, not working
