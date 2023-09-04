# `return True` to command the bot to catch the Pokémon
# Note: you must restart the bot after editing this file for changes to take effect!
# TODO add list of available fields to filter on
# TODO add option for a Discord webhook when a custom is caught

from modules.Console import console

def CustomCatchFilters(pokemon: dict) -> bool:
    """
    Catch the current encounter if it matches any of the following criteria
    :param pokemon: Pokémon object of the current encounter
    """
    try:
        ivs = [pokemon['IVs']['hp'],
               pokemon['IVs']['attack'],
               pokemon['IVs']['defense'],
               pokemon['IVs']['speed'],
               pokemon['IVs']['spAttack'],
               pokemon['IVs']['spDefense']]

        ### Edit below this line ###

        # Catch perfect IV Pokémon
        if pokemon['IVSum'] == 186:
            return True

        # Catch zero IV Pokémon
        if pokemon['IVSum'] == 0:
            return True

        # Catch Pokémon with 6 identical IVs of any value
        if all(v == ivs[0] for v in ivs):
            return True

        # Catch Pokémon with 4 or more max IVs in any stat
        #max_ivs = sum(1 for v in ivs if v == 31)
        #if max_ivs > 4:
        #    return True

        # Catch Pokémon with a good IV sum of greater than or equal to 170
        #if pokemon['IVSum'] >= 170:
        #    return True

        # Catch uncaught Pokémon, not yet registered in the dex
        #if pokemon['hasSpecies'] == 0:
        #    return True

        # Catch all Poochyena with a Pecha Berry
        #if pokemon['name'] == 'Poochyena' and pokemon['itemName'] == 'Pecha Berry':
        #    return True

        # Catch any Pokémon with perfect Atk, SpAtk and Speed
        #if pokemon['attackIV'] == 31 and pokemon['spAttackIV'] == 31 and pokemon['speedIV'] == 31:
        #    return True

        ### Edit above this line ###

        return False
    except:
        console.print_exception(show_locals=True)
        console.print('[red bold]Failed to check Pokemon, potentially due to invalid custom catch filter...')
        return False
