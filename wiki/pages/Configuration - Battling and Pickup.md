🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# ⚔ Battling and Pickup Config

[`profiles/battle.yml`](../../modules/config/templates/battle.yml)

The bot can automatically battle Pokémon that don't meet any catch criteria.

## Auto Catching

`auto_catch` - enable automatic catching of encounters-of-interest (shinies and those that match your custom catch filters.)

If your lead Pokémon knows False Swipe, the bot may use that. It will also try to use sleep-inducing or paralysing moves
where it makes sense.

Other than that, it will just throw Poké balls at the opponent. It chooses the most effective ball from the inventory
(but will never use Master balls.)

## Pickup

> **Please be aware that Pickup has only been tested in Emerald, and may not work in other games.**

`pickup` - enable pickup farming, the bot will use [Pickup (ability)](<https://bulbapedia.bulbagarden.net/wiki/Pickup_(Ability)>) to items from Pokémon who have picked up items. See [Pickup items](<https://bulbapedia.bulbagarden.net/wiki/Pickup_(Ability)#Items_received>).

`pickup_threshold` - number of Pokémon in the party that should have an item before the bot tries to take items from them. If you have fewer Pokémon with Pickup in your party than this number, the bot will use that number instead.

`pickup_check_frequency` - wait interval encounters to get before checking for pickup items.

- If `faster_pickup` is enabled in [💎 Cheats](Configuration%20-%20Cheats.md), this threshold is ignored.

## Battling

`hp_threshold` - Minimum HP percentage for a Pokémon to be considered fit for battle.

`lead_cannot_battle_action` - What to do if the lead Pokémon is not fit to fight after a battle (fainted or HP below the threshold)

- `stop` - go into manual mode
- `flee` - run from the encounter
- `rotate` - send out the next Pokémon in the party (must have at least {hp_threshold}% of its health and at least 1 usable move)

`faint_action` - What to do if a Pokémon faints during a battle.

- `stop` - go into manual mode
- `flee` - run from the encounter (will go to manual mode if it's a trainer battle)
- `rotate` - send out the next Pokémon in the party (must have at least {hp_threshold}% of its health and at least 1 usable move)

`new_move` - how to behave if a Pokémon attempts to learn a new move.

- `stop` - go into manual mode
- `cancel` - stop the Pokémon from learning a new move
- `learn_best`- calculate the weakest move from the Pokémon's current move set. If the new move is better, replaces that move with the new move. If the Pokémon knows more than one move of a certain type, the bot will attempt to delete the weakest move with redundant typing in order to maximize coverage

`stop_evolution` - Set to `true` to prevent Pokémon from evolving during/after a battle (evolution will be cancelled by pressing `B`), or `false` to allow it.

`switch_strategy` - Either `first_available` to switch to the next Pokémon in the list or `lowest_level` to try and level up lower Pokémon

`lead_mon_balance_levels` - `false` or `true` - `true` will switch your lead Pokémon out when it levels above another member of your team. Currently only works with Pokécenter Loop mode.

`banned_moves` - list of moves for the battle engine to never select. Moves that are banned will not be selected in combat.

`avoided_pokemon` - list of Pokémon for the battle engine to never fight. Pokémon that are avoided will be fled from.

`targeted_pokemon` - list of Pokémon for the battle engine to fight. Pokémon that are not targeted will be fled from.
