🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🥅 Custom Catch Filters Config

[`profiles/customcatchfilters.py`](../../profiles/customcatchfilters.py)

All Pokémon encounters are checked by custom catch filters, use this file if you are after Pokémon that match very specific criteria, some examples are provided (most are disabled by default).

These filters are checked *after* the catch block list, so if Wurmple is on your [catch block list](Configuration%20-%20Catch%20Block%20List.md), the Wurmple evolution example below will still be checked.

If you are not familiar with Python, it is highly recommended to use an IDE such as [PyCharm](https://www.jetbrains.com/products/compare/?product=pycharm&product=pycharm-ce) (Community Edition) to edit this file as any syntax errors will be highlighted, and the `pokemon` object will auto-complete and show available parameters for you to filter on.

If you are familiar with Python, a comprehensive list of `pokemon` properties can be found [here](../../modules/pokemon.py).

- `return "any message"` (string) - will command the bot to catch the current encounter, the string returned will be added to the Discord webhook if `custom_filter_pokemon_encounter` is enabled in [Discord config](Configuration%20-%20Discord%20Integration.md)
- `pass` - will skip the check, and continue to check other criteria further down the file
- `save_pk3(pokemon)` instead of `return "any message"` will [dump a .pk3 file](Configuration%20-%20Logging%20and%20Console%20Output.md) and continue without pausing the bot until auto-catch is ready

The following example will catch any shiny Wurmple that will evolve into Silcoon/Beautifly, and ignore any that would evolve into Cascoon/Dustox:

```py
# Shiny Wurmple evolving based on evolution
if pokemon.is_shiny and pokemon.species.name == "Wurmple":
    if pokemon.wurmple_evolution == "silcoon":
        return "Shiny Wurmple evolving into Silcoon/Beautifly"
    if pokemon.wurmple_evolution == "cascoon":
        pass
```

This example will catch any shiny Unown letters, add the Unown letters you need to the list `["A", "B", "C"]`:

```py
if pokemon.is_shiny and pokemon.species.name == "Unown" and pokemon.unown_letter in ["A", "B", "C"]:
    return f"Shiny {pokemon.unown_letter} Unown"
```

The following example will catch any Pokémon with all perfect IVs:
```py
# Pokémon with perfect IVs
if pokemon.ivs.sum() == (6 * 31):
    return "Pokémon with perfect IVs"
```

- **Note**: for technical reasons, you **must** restart the bot after editing this file for changes to take effect! Reloading config with `Ctrl + C` will not work for `py` files.
- 