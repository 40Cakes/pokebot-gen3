🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🔄️ Level Grind Mode

This mode will continuously fight battles in order to level up your Pokémon.

When starting the mode, you have a choice between only levelling up your current lead
Pokémon, or levelling your entire team. In the latter case, the mode will always use
the lowest-level Pokémon to battle and rotate them as necessary.

![image](../images/level_grind_prompt.png)

When the active Pokémon is defeated or gets low on HP, it will heal at the nearest
Pokémon Center automatically. Likewise, if your entire party gets defeated it will
just return to the Tall Grass spot you've picked. So this mode should be pretty much
hands-off.

Should this mode encounter a Shiny or a Pokémon that matches your custom catch filters,
it will **not** battle it but instead either catch it automatically (if auto-catching is
enabled in your configuration) or put the bot back into manual mode. So you don't have to
worry about missing out on a Shiny.


## Instructions

Start this mode while standing somewhere in tall grass that has a _direct_ overworld
connection to a Pokémon Center (i.e. it must be possible to walk to the PC without
going through any buildings.)

If the mode is not available for selection, that means that this route is not supported.
Try another route that has an easy overland path to a Pokémon Center.

## FireRed and LeafGreen

### Supported Routes
- **Routes 1–4**: Route 1, Route 2, Route 3, Route 4
- **Routes 6–11**: Route 6, Route 7, Route 9, Route 10, Route 11
- **Routes 18–24**: Route 18, Route 19, Route 20, Route 21 (North and South), Route 22, Route 24

---

## Emerald

### Supported Routes
- **Routes 101–109**: Route 101, Route 102, Route 103, Route 104, Route 105, Route 106, Route 107, Route 108, Route 109
- **Routes 110–119**: Route 110, Route 111, Route 112, Route 113, Route 114, Route 115, Route 116, Route 117, Route 118, Route 119
- **Routes 120–134**: Route 120, Route 121, Route 122, Route 123, Route 124, Route 125, Route 126, Route 127, Route 128, Route 129, Route 130, Route 131, Route 132, Route 133, Route 134


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
