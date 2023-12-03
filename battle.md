Temp file - move this data to a dedicated wiki page

# Battle
## `battle.yml` - Battle settings and config
<details>
<summary>Click to expand</summary>

### Battle
`battle` - Set this to true to have the bot automatically battle Pokémon that don't meet catch criteria, if possible. If set to false, the bot will instead run away from encounters that don't meet catch criteria.

`batle_method` - Placeholder for future functionality for a more intelligent battle engine.

`pickup` - Set this to true to enable pickup farming. With pickup farming on, the bot will attempt to take advantage of the mechanics of the ability Pickup by taking items from pokemon who have picked up items.

`pickup_threshold` - This is the number of pickup pokemon in the party that should have an item before the bot tries to take items from them. If you have fewer pokemon with Pickup in your party than this number, the bot will use that number instead. I.e. if this is set to 3, but you only have 1 zigzagoon with pickup in your party, it'll use the number 1 instead.

`pickup_check_frequency` - This is how many encounters to get before checking for pickup items. 
- If `pickup` is enabled in `cheats.yml`, this is ignored. 
- Otherwise, the bot will open the party menu to look at the party icons for items every X encounters, as denoted by this value.

`faint_action` - This represents what the bot should do if the lead pokemon faints. 
- If set to `stop`, the bot will go into manual mode. 
- If set to `flee`, the bot will attempt to run from the encounter. 
- If set to `rotate`, the bot will send out the next pokemon in the party that has at least 20% of its health and at least 1 usable move.

`new_move` - This represents what the bot should do if a pokemon attempts to learn a new move. 
- If set to `stop`, the bot will go into manual mode. 
- If set to `cancel`, the bot will stop the pokemon from learning a new move. 
- If set to `learn_best`, the bot will calculate the weakest move from the pokemon's current movepool and, provided the new move is better, replace that move with the new move. If the pokemon knows more than one move of a certain type, the bot will attempt to delete the weakest move with redundant typing in order to maximize coverage.

`stop_evolution` - Set this to true to ensure that the bot will prevent pokemon from evolving.

`replace_lead_battler` - If true, the bot will switch the order of pokemon in the party to replace a lead pokemon that runs out of pp or runs low on hp. Helpful for leveling the whole team.

`switch_strategy` - Placeholder for future functionality for more intelligent switching in battle.

`banned_moves` - List of moves for the battle engine to never select. Moves that are banned will not be selected in combat, and are likely to be forgotten if `new_move` is set to `learn_best`.

</details>


# Cheats
`pickup` - detect through memory when the number of Pokémon with pickup in the party is sufficient to take items. 
- if enabled, the bot won't actively open the party menu to pretend that it's actually checking whether enough pickup Pokémon have items.
- if disabled, every x encounters (specified by `pickup_check_frequency` in `battle.yml`) the bot will open the party menu from the field and "check" whether the requisite number of Pokémon (specified by `pickup_threshold` in `battle.yml`) with pickup as their ability have items.

