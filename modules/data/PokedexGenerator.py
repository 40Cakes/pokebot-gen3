# Run this if pokemon.json or routes-rse.json are modified to regenerate the pokedex data.

import json


def GenerateDex():
    # Read the pokemon.json file
    with open('pokemon.json', encoding="utf-8") as f:
        pokemon_data = json.load(f)

    # Read the routes-rse.json file
    with open('routes-emerald.json', encoding="utf-8") as f:
        routes_data = json.load(f)

    # Initialize the pokedex list
    pokedex = []

    # Iterate over the routes data
    for route in routes_data:
        # Iterate over the encounters in the route
        for encounter in route['encounters']:
            pokedex_id = encounter['pokedex_id']
            for pokemon_name, pokemon in pokemon_data.items():
                if pokedex_id == pokemon['number']:
                    # Create the pokedex entry
                    pokedex_entry = {
                        "pokedex_id": pokedex_id,
                        "name": pokemon_name,
                        "type": pokemon['type'],
                        "encounters": [
                            {
                                "location": route['name'],
                                "levels": encounter['levels'],
                                "rate": encounter['rate'],
                                "encounter_type": encounter['encounter_type']
                            }
                        ]
                    }

                    # Check if the pokedex entry already exists in the pokedex list
                    existing_entry = next((entry for entry in pokedex if entry['pokedex_id'] == pokedex_id), None)
                    if existing_entry:
                        # Append the encounter to the existing entry
                        existing_entry['encounters'].append(pokedex_entry['encounters'][0])
                    else:
                        # Add the new pokedex entry to the pokedex list
                        pokedex.append(pokedex_entry)

    # Add missing Pokémon as entries with empty encounters
    for pokemon_name, pokemon in pokemon_data.items():
        pokedex_id = pokemon['number']
        if not any(entry['pokedex_id'] == pokedex_id for entry in pokedex):
            pokedex_entry = {
                "pokedex_id": pokedex_id,
                "name": pokemon_name,
                "type": pokemon['type'],
                "encounters": []
            }
            pokedex.append(pokedex_entry)

    # Save the pokedex as pokedex.json
    with open('pokedex.json', "w", encoding="utf-8") as f:
        json.dump(pokedex, f, indent=4, ensure_ascii=False)


# Call the function to generate the pokedex
GenerateDex()
