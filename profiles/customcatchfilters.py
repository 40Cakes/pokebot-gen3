# TODO add list of available fields to filter on
from enum import StrEnum
from modules.console import console
from modules.files import save_pk3
from modules.pokemon import Pokemon


class CustomFilterMatched(StrEnum):
    """
    Enum class to get which custom filter was matched
    Add your custom filters down below
    """
    NONE = "No filter matched"
    UNKNOWN = "Unknown filter matched"
    SHINY_SILCOON_OR_BEAUTIFLY = "Shiny Wurmple evolving into Silcoon/Beautifly"
    SHINY_CASCOON_OR_DUSTOX = "Shiny Wurmple evolving into Cascoon/Dustox"
    PERFECT_IVS = "Pokémon with perfect ivs"
    ZERO_IVS = "Pokémon with all IVs to 0"
    SIX_IDENTICAL_IVS = "Pokémon with 6 identical IVs of any value"
    FOUR_OR_MORE_MAX_IVS = "Pokémon with 4 or more max IVs in any stat"
    IVS_GREATER_EQUAL_170 = "Pokémon with IVs sum greater or equal to 170"
    POOCHYENA_PECHA_BERRY = "Poochyena holding a pecha berry"
    PERFECT_ATK_SPATK_SPD = "Pokémon with perfect attack, spAttack and speed"


def custom_catch_filters(pokemon: Pokemon) -> CustomFilterMatched:
    """
    Check the current encounter, catch if it matches any of the following criteria.
    Some examples are provided (most are disabled by default).
    These filters are checked *after* catch block list, so if Wurmple is on your catch block list, the Wurmple evolution
    examples below will still be checked.

    This function returns a CustomFilterMatched, a string enum giving details on the filter that matched.
    If you do not want to give detail on the filter that matched, you can use `return CustomFilterMatched.UNKNOWN`
    - `return CustomFilterMatched.XXXX` will command the bot to catch the current encounter (Where XXXX is an enum case from CustomFilterMatched not equal CustomFilterMatched.NONE)
    - `pass` - will skip the check, and continue to check other criteria further down this file
    - `save_pk3(pokemon)` instead of `return CustomFilterMatched.XXXX` will dump a .pk3 file and continue without pausing the bot until
    auto-catch is ready

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
            # Catch shiny Wurmple based on evolution
            if pokemon.is_shiny and pokemon.species.name == "Wurmple":
                evolution = "Silcoon/Beautifly" if pokemon.wurmple_evolution == "silcoon" else "Cascoon/Dustox"
                if evolution == "Silcoon/Beautifly":
                    pass  # ❌ disabled
                    # return CustomFilterMatched.SHINY_SILCOON_OR_BEAUTIFLY
                if evolution == "Cascoon/Dustox":
                    pass  # ❌ disabled
                    # return CustomFilterMatched.SHINY_CASCOON_OR_DUSTOX

            # Catch perfect IV Pokémon
            if pokemon.ivs.sum() == (6 * 31):
                return CustomFilterMatched.PERFECT_IVS  # ✅ enabled

            # Catch zero IV Pokémon
            if pokemon.ivs.sum() == 0:
                return CustomFilterMatched.ZERO_IVS # ✅ enabled

            # Catch Pokémon with 6 identical IVs of any value
            if all(v == ivs[0] for v in ivs):
                return CustomFilterMatched.SIX_IDENTICAL_IVS # ✅ enabled

            # Catch Pokémon with 4 or more max IVs in any stat
            max_ivs = sum(1 for v in ivs if v == 31)
            if max_ivs > 4:
                pass  # ❌ disabled
                # return CustomFilterMatched.FOUR_OR_MORE_MAX_IVS

            # Catch Pokémon with a good IV sum of greater than or equal to 170
            if pokemon.ivs.sum() >= 170:
                pass  # ❌ disabled
                # return CustomFilterMatched.IVS_GREATER_EQUAL_170

            # Catch all Poochyena with a Pecha Berry
            if pokemon.species.name == "Poochyena" and pokemon.held_item and pokemon.held_item.name == "Pecha Berry":
                pass  # ❌ disable
                # return CustomFilterMatched.POOCHYENA_PECHA_BERRY

            # Catch any Pokémon with perfect attack, spAttack and speed
            if pokemon.ivs.attack == 31 and pokemon.ivs.special_attack == 31 and pokemon.ivs.speed == 31:
                pass  # ❌ disable
                # return CustomFilterMatched.PERFECT_ATK_SPATK_SPD

        ### Edit above this line ###

        return CustomFilterMatched.NONE
    except:
        console.print_exception(show_locals=True)
        console.print("[red bold]Failed to check Pokemon, potentially due to invalid custom catch filter...")
        return CustomFilterMatched.NONE
