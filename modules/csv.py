import os
from pathlib import Path
import pandas as pd


def flatten_data(data: dict) -> dict:
    out = {}

    def flatten(x, name=""):
        if type(x) is dict:
            for a in x:
                flatten(x[a], name + a + "_")
        elif type(x) is list:
            i = 0
            for a in x:
                flatten(a, name + str(i) + "_")
                i += 1
        else:
            out[name[:-1]] = x

    flatten(data)
    return out


def log_encounter_to_csv(total_stats: dict, pokemon_dict: dict, stats_dir_path: Path) -> bool:
    try:
        # Log all encounters to a CSV file per phase
        csv_path = stats_dir_path / "encounters"
        os.makedirs(csv_path, exist_ok=True)
        csv_file = csv_path / f"Phase {total_stats['totals'].get('shiny_encounters', 0)} Encounters.csv"
        pd_pokemon = (
            pd.DataFrame.from_dict(flatten_data(pokemon_dict), orient="index")
            .drop(
                [
                    "EVs_attack",
                    "EVs_defence",
                    "EVs_hp",
                    "EVs_spAttack",
                    "EVs_spDefense",
                    "EVs_speed",
                    "markings_circle",
                    "markings_heart",
                    "markings_square",
                    "markings_triangle",
                    "moves_0_effect",
                    "moves_1_effect",
                    "moves_2_effect",
                    "moves_3_effect",
                    "pokerus_days",
                    "pokerus_strain",
                    "status_badPoison",
                    "status_burn",
                    "status_freeze",
                    "status_paralysis",
                    "status_poison",
                    "status_sleep",
                    "condition_beauty",
                    "condition_cool",
                    "condition_cute",
                    "condition_feel",
                    "condition_smart",
                    "condition_tough",
                ],
                errors="ignore",
            )
            .sort_index()
            .transpose()
        )
        header = False if os.path.exists(csv_file) else True
        pd_pokemon.to_csv(csv_file, mode="a", encoding="utf-8", index=False, header=header)
        return True
    except:
        return False
