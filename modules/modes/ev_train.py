from typing import Generator
from rich.table import Table


from modules.context import context
from modules.map import get_map_data_for_current_position, get_map_data
from modules.map_data import MapFRLG, MapRSE, PokemonCenter, get_map_enum
from modules.map_path import calculate_path, PathFindingError
from modules.modes import BattleAction
from modules.player import get_player_avatar
from modules.pokemon import get_party, get_opponent, StatusCondition
from ._interface import BotMode, BotModeError
from .util import navigate_to, heal_in_pokemon_center, change_lead_party_pokemon, spin
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy, DefaultBattleStrategy
from ..encounter import handle_encounter, EncounterInfo
from ..gui.ev_selection_window import get_ev_targets

closest_pokemon_centers: dict[MapFRLG | MapRSE, list[PokemonCenter]] = {
    # Hoenn
    MapRSE.ROUTE101: [PokemonCenter.OldaleTown],
    MapRSE.ROUTE102: [PokemonCenter.OldaleTown, PokemonCenter.PetalburgCity],
    MapRSE.ROUTE103: [PokemonCenter.OldaleTown],
    MapRSE.ROUTE104: [PokemonCenter.PetalburgCity, PokemonCenter.RustboroCity],
    MapRSE.ROUTE116: [PokemonCenter.RustboroCity],
    MapRSE.ROUTE110: [PokemonCenter.SlateportCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE117: [PokemonCenter.MauvilleCity, PokemonCenter.VerdanturfTown],
    MapRSE.ROUTE113: [PokemonCenter.FallarborTown],
    MapRSE.ROUTE114: [PokemonCenter.FallarborTown],
    MapRSE.ROUTE119: [PokemonCenter.FortreeCity],
    MapRSE.ROUTE120: [PokemonCenter.FortreeCity],
    MapRSE.ROUTE121: [PokemonCenter.LilycoveCity],
    # Kanto
    MapFRLG.ROUTE1: [PokemonCenter.ViridianCity],
    MapFRLG.ROUTE22: [PokemonCenter.ViridianCity],
    MapFRLG.ROUTE2: [PokemonCenter.ViridianCity, PokemonCenter.PewterCity],
    MapFRLG.ROUTE3: [PokemonCenter.PewterCity, PokemonCenter.Route4],
    MapFRLG.ROUTE4: [PokemonCenter.Route4, PokemonCenter.CeruleanCity],
    MapFRLG.ROUTE24: [PokemonCenter.CeruleanCity],
    MapFRLG.ROUTE6: [PokemonCenter.VermilionCity],
    MapFRLG.ROUTE11: [PokemonCenter.VermilionCity],
    MapFRLG.ROUTE9: [PokemonCenter.Route10],
    MapFRLG.ROUTE10: [PokemonCenter.Route10],
    MapFRLG.ROUTE7: [PokemonCenter.CeladonCity],
    MapFRLG.ROUTE18: [PokemonCenter.FuchsiaCity],
}

class NoRotateLeadDefaultBattleStrategy(DefaultBattleStrategy):
    def choose_new_lead_after_battle(self) -> int | None:
        return None

class EVTrainMode(BotMode):
    @staticmethod
    def name() -> str:
        return "EV Train"

    @staticmethod
    def is_selectable() -> bool:
        current_location = get_map_data_for_current_position()
        if current_location is None:
            return False

        return (
            current_location.has_encounters
            and not current_location.is_surfable
            and current_location.map_group_and_number in closest_pokemon_centers
        )

    def __init__(self):
        super().__init__()
        self._leave_pokemon_center = False
        self._go_healing = True
        self._level_balance = False

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        action = handle_encounter(encounter, enable_auto_battle=True)
        lead_pokemon = get_party()[0]
        # EV yield doubled with Macho Brace and Pokerus (this effect stacks)
        ev_multiplier = int
        if (lead_pokemon.held_item is None or 
            (lead_pokemon.held_item is not None and lead_pokemon.held_item.name != "Macho Brace")) and lead_pokemon.pokerus_status.days_remaining <= 0:
            ev_multiplier = 1
        elif lead_pokemon.held_item is not None and lead_pokemon.held_item.name == "Macho Brace" and lead_pokemon.pokerus_status.days_remaining > 0:
            ev_multiplier = 4
        else: ev_multiplier = 2

        base_yield = [
            int(get_opponent().species.ev_yield.hp),
            int(get_opponent().species.ev_yield.attack), 
            int(get_opponent().species.ev_yield.defence),
            int(get_opponent().species.ev_yield.special_attack), 
            int(get_opponent().species.ev_yield.special_defence), 
            int(get_opponent().species.ev_yield.speed)
                    ] 
        
        ev_yield = [i * ev_multiplier for i in base_yield]

        party_evs = [
            int(lead_pokemon.evs.hp), 
            int(lead_pokemon.evs.attack),
            int(lead_pokemon.evs.defence),
            int(lead_pokemon.evs.special_attack),
            int(lead_pokemon.evs.special_defence),
            int(lead_pokemon.evs.speed)
            ]

        # Checks if opponent evs are desired
        good_yield = all(ev_yield[i] + party_evs[i] <= self._ev_targets[i] for i in range(6)) 
        # Fights if evs are desired and oppenent is not shiny meets a custom catch filter
        if good_yield and action is BattleAction.Fight:
                return NoRotateLeadDefaultBattleStrategy()
        else:
            return BattleAction.RunAway

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        lead_pokemon = get_party()[0]
        if (
            not DefaultBattleStrategy().pokemon_can_battle(lead_pokemon)
            or lead_pokemon.status_condition is not StatusCondition.Healthy
        ):
            self._go_healing = True
        ev_multiplier = int
        if (lead_pokemon.held_item is None or 
            (lead_pokemon.held_item is not None and lead_pokemon.held_item.name != "Macho Brace")) and lead_pokemon.pokerus_status.days_remaining <= 0:
            ev_multiplier = 1
        elif lead_pokemon.held_item is not None and lead_pokemon.held_item.name == "Macho Brace" and lead_pokemon.pokerus_status.days_remaining > 0:
            ev_multiplier = 4
        else: ev_multiplier = 2

        base_yield = [
            int(get_opponent().species.ev_yield.hp),
            int(get_opponent().species.ev_yield.attack), 
            int(get_opponent().species.ev_yield.defence),
            int(get_opponent().species.ev_yield.special_attack), 
            int(get_opponent().species.ev_yield.special_defence), 
            int(get_opponent().species.ev_yield.speed)
                    ] 
        
        ev_yield = [i * ev_multiplier for i in base_yield]
        
        party_evs = [
            int(lead_pokemon.evs.hp), 
            int(lead_pokemon.evs.attack),
            int(lead_pokemon.evs.defence),
            int(lead_pokemon.evs.special_attack),
            int(lead_pokemon.evs.special_defence),
            int(lead_pokemon.evs.speed)
            ]
        
        # Ugly table to keep track of progress
        ev_table = Table(title=f"{lead_pokemon.species.name} EVs/Target")
        ev_table.add_column("HP", justify="center")
        ev_table.add_column("ATK", justify="center")
        ev_table.add_column("DEF", justify="center")
        ev_table.add_column("SPA", justify="center")
        ev_table.add_column("SPD", justify="center")
        ev_table.add_column("SPE", justify="center")
        ev_table.add_column("Total", justify="right")
        ev_table.add_row(
            f"{str(party_evs[0])}/{str(self._ev_targets[0])}",
            f"{str(party_evs[1])}/{str(self._ev_targets[1])}",
            f"{str(party_evs[2])}/{str(self._ev_targets[2])}",
            f"{str(party_evs[3])}/{str(self._ev_targets[3])}",
            f"{str(party_evs[4])}/{str(self._ev_targets[4])}",
            f"{str(party_evs[5])}/{str(self._ev_targets[5])}",
        )
        print(f"HP: {str(party_evs[0])}/{str(self._ev_targets[0])} ATK: {str(party_evs[1])}/{str(self._ev_targets[1])} DEF: {str(party_evs[2])}/{str(self._ev_targets[2])} SPA: {str(party_evs[3])}/{str(self._ev_targets[3])} SPD: {str(party_evs[4])}/{str(self._ev_targets[4])} SPE: {str(party_evs[5])}/{str(self._ev_targets[5])}")

        if outcome == BattleOutcome.RanAway:
            context.message = "EVs not needed, skipping"
        if outcome == BattleOutcome.Won:
            context.message = f"{str(ev_yield)} EVs gained"

    def on_whiteout(self) -> bool:
        self._leave_pokemon_center = True
        return True

    def run(self) -> Generator:
        training_spot = get_map_data_for_current_position()
        if not training_spot.has_encounters:
            raise BotModeError("There are no encounters on this tile.")
        if training_spot.is_surfable:
            raise BotModeError("This mode does not work when surfing.")

        training_spot_map = get_map_enum(training_spot)
        training_spot_coordinates = training_spot.local_position

        # Find the closest Pokemon Center to the current location
        pokemon_center = None
        path_length_to_pokemon_center = None
        if training_spot_map in closest_pokemon_centers:
            for pokemon_center_candidate in closest_pokemon_centers[training_spot_map]:
                try:
                    pokemon_center_location = get_map_data(
                        pokemon_center_candidate.value[0], pokemon_center_candidate.value[1]
                    )
                    path_to = calculate_path(training_spot, pokemon_center_location)
                    path_from = []
                    path_length = len(path_to) + len(path_from)

                    if path_length_to_pokemon_center is None or path_length_to_pokemon_center > path_length:
                        pokemon_center = pokemon_center_candidate
                        path_length_to_pokemon_center = path_length
                except PathFindingError:
                    pass

        if pokemon_center is None:
            raise BotModeError("Could not find a suitable from here to a Pokemon Center nearby.")

        # Opens EV target selection GUI
        self._ev_targets = get_ev_targets()

        # Checks for EV target sensibility
        if sum(self._ev_targets) > 510:
            raise BotModeError("Total EVs must be 510 or below.")
        
        all_255 = all(ev in range(0, 255) for ev in self._ev_targets) 
        if all_255 == False:
            raise BotModeError("EV target for a given stat must be between 0 and 255.")

        while True:
            if self._leave_pokemon_center:
                yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
            elif self._go_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._go_healing = False

            yield from navigate_to(training_spot_map, training_spot_coordinates)
            yield from spin(stop_condition=lambda: self._go_healing or self._leave_pokemon_center)