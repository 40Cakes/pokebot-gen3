[`pokebot-gen3` Wiki Home](../Readme.md)

# Daycare Soft Resets Mode

Daycare Soft Resets repeatedly collects a ready Daycare egg, checks whether the egg is shiny, and soft resets if it is not.

Unlike regular [Daycare](Mode%20-%20Daycare.md) mode, this mode does not collect batches of eggs, hatch non-shiny eggs, or release them at the PC. It is designed for a save file positioned in front of the Daycare man while he already has an egg ready.

When a shiny egg is found, the bot logs the encounter, notifies you, walks until the egg hatches, opens the hatched Pokemon summary, and then switches to Manual mode.

## Requirements

- A compatible breeding couple in the Daycare.
- At least one empty party slot in the saved game.
- The Daycare man must already have an egg ready.
- Save the game in front of the Daycare man, facing him.
- Use an in-game save, not a save state.

## Optional, but recommended

- In Emerald, having a Pokemon with Flame Body or Magma Armor in the party halves the number of steps needed to hatch eggs.
- Register the Mach Bike in R/S/E or Bicycle in FR/LG to `Select` for faster hatching.

## Instructions

1. Put the breeding pair in the Daycare.
2. Wait until the Daycare man has an egg ready.
3. Stand directly in front of the Daycare man and face him.
4. Save the game.
5. Start `Daycare Soft Resets`.

The mode automatically sets emulation speed to max/unthrottled when it starts.

If the mode starts and a shiny egg is already in your party, it will hatch that egg instead of soft resetting. This helps recover safely after being notified about a shiny egg.

## Supported locations

- Ruby/Sapphire/Emerald: Route 117 Daycare.
- FireRed/LeafGreen: Four Island Daycare.

## Notes

For modes that use soft resets, the bot tracks RNG to ensure a unique frame after every reset. This prevents repeatedly generating the same Pokemon, but resets can take progressively longer over time.

If resets become too slow, check [Cheats](Configuration%20-%20Cheats.md) and the `random_soft_reset_rng` option.
