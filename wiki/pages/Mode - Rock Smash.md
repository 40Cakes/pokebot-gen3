🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🪨 Rock Smash Mode

Rock smash mode will continuously farm Rock Smash encounters in Granite Cave (Nosepass) and Safari Zone (Shuckle).

## Granite Cave
![](../../modules/web/static/sprites/pokemon/shiny/Nosepass.png)

You can use this mode either with or without Repel.  
If using Repel, the bot will use up any Repel items in your inventory and then reset once it ran out.

Using Repel on its own give a minor boost to encounter rates (around +5%), but there are two ways to
boost encounter rates significantly (that both require Repel to be used):

1. If you have a **White Flute** in your inventory, the bot will use that as well and in combination
   that can boost encounters by **up to 40%**.
2. If you have a Pokémon with the ability **Vital Spirit** or **Pressure** as the first Pokémon in
   your party, that can give you **another 35% boost** to Nosepass encounters.

A good candidate for a Pokémon with such an ability would be Vigoroth -- which you can get by catching
a Slakoth in Petalburg Woods and evolving it at level 18. Because that level would be too high for the
Repel strategy, you should _make it faint_ (its ability will still work) and put it in the first slot
of your party, and then put a non-fainted level-13 Pokémon in the second slot (because Repel works with
the level of the first _non-fainted_ Pokémon.)

If you have any Repel items in your inventory, the game will offer you this choice:

![](../images/rock_smash_repel_prompt.png)

### Without Repel

- Go to the bottom floor of Granite Cave (B2F)
- Start mode

### With Repel

- Make sure you have some Repel in your inventory (Max Repel works best, but Super Repel or Repel will do.)  
  While the bot can work with as few as 1 Repel, having a few dozen will improve rates by spending less time resetting.
- Optional, but highly recommended: Get the White Flute.
- Optional, but highly recommended: Get a Pokémon with the ability Vital Spirit or Pressure as the first Pokémon.
- Make sure the first non-fainted Pokémon in your party has level 13. The bot will accept Pokémon up to level 16, but
  13 gives you the best rates.
- Go to the bottom floor of Granite Cave (B2F)
- **Save the game**
- Start mode and select 'Use Repel'

![image](../images/granite_cave.png)


## Safari Zone
![](../../modules/web/static/sprites/pokemon/shiny/Shuckle.png)

(This area only exists in Emerald.)

The mode will continuously try to enter the Safari Zone, so make sure you have some cash. The bot will use up to ₽25,000 and then soft reset to start over. If you have less cash than that, it will soft-reset when money runs out.

- Go to the _entrance_ of the Safari Zone (see image below)
- Make sure you have some cash on you
- (Optional) Register the Mach Bike to the Select button (this is not required, but it will be a bit faster.)
- Save the game (**in-game, not a save state**)
- Start mode

![image](../images/safari_zone.png)


## Game Support
|          | 🟥 Ruby | 🔷 Sapphire | 🟢 Emerald |
|:---------|:-------:|:-----------:|:----------:|
| English  |    ✅    |      ✅      |     ✅      |
| Japanese |    ❌    |      ❌      |     ✅      |
| German   |    ✅    |      ❌      |     ✅      |
| Spanish  |    ✅    |      ❌      |     ✅      |
| French   |    ✅    |      ❌      |     ✅      |
| Italian  |    ✅    |      ❌      |     ✅      |

✅ Tested, working

🟨 Untested, may not work

❌ Untested, not working
