from modules.console import console
from modules.files import save_pk3
from modules.pokemon import Pokemon


def custom_catch_filters(pokemon: Pokemon) -> str | bool:
    """
    Check the current encounter, catch if it matches any of the following criteria.
    Some examples are provided (most are disabled by default).
    These filters are checked *after* catch block list, so if Wurmple is on your catch block list, the Wurmple evolution
    examples below will still be checked.
    If you use an IDE such as PyCharm, the pokemon class will auto-complete/show available options to filter on

    - return "any message" - will command the bot to catch the current encounter, the string returned will be added to
    the Discord webhook if `custom_filter_pokemon_encounter` is enabled in discord.yml
    - `pass` - will skip the check, and continue to check other criteria further down this file
    - `save_pk3(pokemon)` instead of `return "any message"` will dump a .pk3 file and continue without pausing the bot
    until auto-catch is ready

    Note: you must restart the bot after editing this file for changes to take effect!

    :param pokemon: Pokémon object of the current encounter
    """
    try:
        ivs = [
            pokemon.ivs.hp,
            pokemon.ivs.attack,
            pokemon.ivs.defence,
            pokemon.ivs.speed,
            pokemon.ivs.special_attack,
            pokemon.ivs.special_defence,
        ]

        ### Edit below this line ###

        # Any 1-time encounter Pokémon (starters/legendaries/gift Pokémon) in this exceptions list will not be checked
        exceptions = [
            "Bulbasaur",
            "Charmander",
            "Squirtle",
            "Chikorita",
            "Cyndaquil",
            "Totodile",
            "Treecko",
            "Torchic",
            "Mudkip",
            "Kyogre",
            "Groudon",
            "Rayquaza",
            "Regirock",
            "Regice",
            "Registeel",
            "Latios",
            "Latias",
            "Mew",
            "Lugia",
            "Ho-Oh",
            "Deoxys",
            "Articuno",
            "Zapdos",
            "Moltres",
            "Mewtwo",
            "Raikou",
            "Entei",
            "Suicine",
            "Castform",
            "Lileep",
            "Anorith",
            "Wynaut",
            "Beldum",
            "Togepi",
            "Eevee",
            "Omanyte",
            "Kabuto",
            "Hitmonlee",
            "Hitmonchan",
        ]

        if pokemon.species.name not in exceptions:
            # Shiny Wurmple evolving based on evolution
            if pokemon.is_shiny and pokemon.species.name == "Wurmple":
                evolution = "Silcoon/Beautifly" if pokemon.wurmple_evolution == "silcoon" else "Cascoon/Dustox"
                if evolution == "Silcoon/Beautifly":
                    # return "Shiny Wurmple evolving into Silcoon/Beautifly"
                    pass
                if evolution == "Cascoon/Dustox":
                    # return "Shiny Wurmple evolving into Cascoon/Dustox"
                    pass

            # Pokémon with perfect IVs
            if pokemon.ivs.sum() == (6 * 31):
                return "Pokémon with perfect IVs"
                #pass

            # Pokémon with all 0 IVs
            if pokemon.ivs.sum() == 0:
                return "Pokémon with all 0 IVs"
                #pass

            # Pokémon with 6 identical IVs of any value
            if all(v == ivs[0] for v in ivs):
                return "Pokémon with 6 identical IVs of any value"
                #pass

            # Pokémon with 4 or more max IVs in any stat
            max_ivs = sum(1 for v in ivs if v == 31)
            if max_ivs > 4:
                # return "Pokémon with 4 or more max IVs in any stat"
                pass

            # Pokémon with IVs sum greater or equal to 170
            if pokemon.ivs.sum() >= 170:
                # return "Pokémon with IVs sum greater or equal to 170"
                pass

            # Poochyena holding a Pecha Berry
            if pokemon.species.name == "Poochyena" and pokemon.held_item and pokemon.held_item.name == "Pecha Berry":
                # return "Poochyena holding a Pecha Berry"
                pass

            # Pokémon with perfect attack, spAttack and speed
            if pokemon.ivs.attack == 31 and pokemon.ivs.special_attack == 31 and pokemon.ivs.speed == 31:
                # return "Pokémon with perfect attack, spAttack and speed"
                pass

        ### Edit above this line ###

        return False
    except:
        console.print_exception(show_locals=True)
        console.print("[red bold]Failed to check Pokemon, potentially due to invalid custom catch filter...")
        return False
