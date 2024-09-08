🏠 [`pokebot-gen3` Wiki Home](../Readme.md)

# 🥅 Custom Catch Filters Config

[`profiles/customcatchfilters.py`](../../modules/config/templates/customcatchfilters.py)

All Pokémon encounters are checked by custom catch filters, use this file if you are after Pokémon that match very specific criteria, some examples are provided.

Most examples are disabled (commented out with a `#` at start of line) to prevent wasting Poké Balls, however exceptionally rare filters are enabled by default such as `Pokémon with perfect IVs`, `Pokémon with all 0 IVs`, `Pokémon with 6 identical IVs of any value`.

These filters are checked _after_ the catch block list, so if Wurmple is on your [catch block list](Configuration%20-%20Catch%20Block%20List.md), the Wurmple evolution example below will still be checked.

- ✅ `return "any message"` (string) - will command the bot to catch the current encounter, the string returned will be added to the Discord webhook if `custom_filter_pokemon_encounter` is enabled in [Discord config](Configuration%20-%20Discord%20Integration.md)
- 💾 `save_pk3(pokemon)` will [dump a .pk3 file](Console,%20Logging%20and%20Image%20Config.md)

If you are not familiar with Python, it is highly recommended to use an IDE such as [PyCharm](https://www.jetbrains.com/products/compare/?product=pycharm&product=pycharm-ce) (Community Edition) to edit this file as any syntax errors will be highlighted, and the `pokemon` object will auto-complete and show available parameters for you to filter on.

If you are familiar with Python, a comprehensive list of `pokemon` properties can be found [here](../../modules/pokemon.py).

The following example will catch any shiny Wurmple that will evolve into Silcoon/Beautifly, and ignore any that would evolve into Cascoon/Dustox:

```py
# Shiny Wurmple that will evolve into Silcoon
if pokemon.is_shiny and pokemon.species.name == "Wurmple":
    if pokemon.wurmple_evolution == "silcoon":
        return "Shiny Wurmple evolving into Silcoon/Beautifly"
```

The following example will catch any Pokémon with all perfect IVs:

```py
# Pokémon with perfect IVs
if pokemon.ivs.sum() == (6 * 31):
    return "Pokémon with perfect IVs"
```

- **Note**: for technical reasons, you **must** restart the bot after editing this file for changes to take effect! Reloading config with `Ctrl + C` will not work for `py` files.
