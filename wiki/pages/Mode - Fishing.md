🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🎣 Fishing Mode

![](../../modules/web/static/sprites/pokemon/shiny/Tentacool.png)
![](../../modules/web/static/sprites/pokemon/shiny/Corsola.png)
![](../../modules/web/static/sprites/pokemon/shiny/Relicanth.png)

Fishing is a way to use a fishing rod to catch wild Pokémon in the water. Some Pokémon can only be caught by using a fishing rod.

- (Recommended) The first Pokémon in the party (can be fainted) should have the ability [Sticky Hold](https://bulbapedia.bulbagarden.net/wiki/Sticky_Hold_(Ability)) or [Suction Cups](https://bulbapedia.bulbagarden.net/wiki/Suction_Cups_(Ability)) to increase the bite rate while fishing
- Register any fishing rod and start the mode while facing water

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

### Note
Since a high number of Safari Balls is essential for shiny hunting, the bot will automatically switch to manual mode
if your Safari Ball count drops below `15`.

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