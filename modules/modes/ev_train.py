from typing import Generator

from rich.table import Table

from modules.context import context
from modules.map import get_map_data_for_current_position, get_map_data
from modules.map_data import MapFRLG, MapRSE, PokemonCenter, get_map_enum
from modules.map_path import calculate_path, PathFindingError
from modules.modes import BattleAction
from modules.player import get_player_avatar
from modules.pokemon import get_opponent, StatusCondition, StatsValues
from modules.pokemon_party import get_party
from ._interface import BotMode, BotModeError
from .util import navigate_to, heal_in_pokemon_center, spin
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy, DefaultBattleStrategy
from ..console import console
from ..encounter import handle_encounter, EncounterInfo
from ..gui.ev_selection_window import ask_for_ev_targets

closest_pokemon_centers: dict[MapFRLG | MapRSE, list[PokemonCenter]] = {
    # Hoenn
    MapRSE.ROUTE101: [PokemonCenter.OldaleTown],
    MapRSE.ROUTE102: [PokemonCenter.OldaleTown, PokemonCenter.PetalburgCity],
    MapRSE.ROUTE103: [PokemonCenter.OldaleTown],
    MapRSE.ROUTE104: [PokemonCenter.PetalburgCity, PokemonCenter.RustboroCity],
    MapRSE.ROUTE105: [PokemonCenter.PetalburgCity, PokemonCenter.DewfordTown],
    MapRSE.ROUTE106: [PokemonCenter.DewfordTown],
    MapRSE.ROUTE107: [PokemonCenter.DewfordTown],
    MapRSE.ROUTE108: [PokemonCenter.DewfordTown],
    MapRSE.ROUTE109: [PokemonCenter.SlateportCity],
    MapRSE.ROUTE110: [PokemonCenter.SlateportCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE111: [PokemonCenter.MauvilleCity, PokemonCenter.MauvilleCity, PokemonCenter.FallarborTown],
    MapRSE.ROUTE112: [PokemonCenter.LavaridgeTown, PokemonCenter.MauvilleCity, PokemonCenter.FallarborTown],
    MapRSE.ROUTE113: [PokemonCenter.FallarborTown],
    MapRSE.ROUTE114: [PokemonCenter.FallarborTown],
    MapRSE.ROUTE115: [PokemonCenter.RustboroCity],
    MapRSE.ROUTE116: [PokemonCenter.RustboroCity],
    MapRSE.ROUTE117: [PokemonCenter.MauvilleCity, PokemonCenter.VerdanturfTown],
    MapRSE.ROUTE118: [PokemonCenter.MauvilleCity],
    MapRSE.ROUTE119: [PokemonCenter.FortreeCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE120: [PokemonCenter.FortreeCity],
    MapRSE.ROUTE121: [PokemonCenter.LilycoveCity],
    MapRSE.ROUTE122: [PokemonCenter.LilycoveCity],
    MapRSE.ROUTE123: [PokemonCenter.LilycoveCity, PokemonCenter.MauvilleCity],
    MapRSE.ROUTE124: [PokemonCenter.LilycoveCity, PokemonCenter.MossdeepCity],
    MapRSE.ROUTE125: [PokemonCenter.MossdeepCity],
    MapRSE.ROUTE126: [PokemonCenter.MossdeepCity],
    MapRSE.ROUTE127: [PokemonCenter.MossdeepCity],
    MapRSE.ROUTE128: [PokemonCenter.EvergrandeCity],
    MapRSE.ROUTE129: [PokemonCenter.EvergrandeCity],
    MapRSE.ROUTE130: [PokemonCenter.PacifidlogTown],
    MapRSE.ROUTE131: [PokemonCenter.PacifidlogTown],
    MapRSE.ROUTE132: [PokemonCenter.PacifidlogTown],
    MapRSE.ROUTE133: [PokemonCenter.PacifidlogTown, PokemonCenter.SlateportCity],
    MapRSE.ROUTE134: [PokemonCenter.SlateportCity],
    MapRSE.PETALBURG_CITY: [PokemonCenter.PetalburgCity],
    MapRSE.SLATEPORT_CITY: [PokemonCenter.SlateportCity],
    MapRSE.MAUVILLE_CITY: [PokemonCenter.MauvilleCity],
    MapRSE.RUSTBORO_CITY: [PokemonCenter.RustboroCity],
    MapRSE.FORTREE_CITY: [PokemonCenter.FortreeCity],
    MapRSE.LILYCOVE_CITY: [PokemonCenter.LilycoveCity],
    MapRSE.MOSSDEEP_CITY: [PokemonCenter.MossdeepCity],
    MapRSE.EVER_GRANDE_CITY: [PokemonCenter.EvergrandeCity],
    MapRSE.OLDALE_TOWN: [PokemonCenter.OldaleTown],
    MapRSE.DEWFORD_TOWN: [PokemonCenter.DewfordTown],
    MapRSE.LAVARIDGE_TOWN: [PokemonCenter.LavaridgeTown],
    MapRSE.FALLARBOR_TOWN: [PokemonCenter.FallarborTown],
    MapRSE.VERDANTURF_TOWN: [PokemonCenter.VerdanturfTown],
    MapRSE.PACIFIDLOG_TOWN: [PokemonCenter.PacifidlogTown],
    # Kanto
    MapFRLG.ROUTE1: [PokemonCenter.ViridianCity],
    MapFRLG.ROUTE2: [PokemonCenter.ViridianCity, PokemonCenter.PewterCity],
    MapFRLG.ROUTE3: [PokemonCenter.PewterCity, PokemonCenter.Route4],
    MapFRLG.ROUTE4: [PokemonCenter.Route4, PokemonCenter.CeruleanCity],
    MapFRLG.ROUTE6: [PokemonCenter.VermilionCity],
    MapFRLG.ROUTE7: [PokemonCenter.CeladonCity],
    MapFRLG.ROUTE9: [PokemonCenter.Route10],
    MapFRLG.ROUTE10: [PokemonCenter.Route10],
    MapFRLG.ROUTE11: [PokemonCenter.VermilionCity],
    MapFRLG.ROUTE18: [PokemonCenter.FuchsiaCity],
    MapFRLG.ROUTE19: [PokemonCenter.FuchsiaCity],
    MapFRLG.ROUTE20: [PokemonCenter.CinnabarIsland, PokemonCenter.FuchsiaCity],
    MapFRLG.ROUTE21_NORTH: [PokemonCenter.CinnabarIsland],
    MapFRLG.ROUTE21_SOUTH: [PokemonCenter.CinnabarIsland],
    MapFRLG.ROUTE22: [PokemonCenter.ViridianCity],
    MapFRLG.ROUTE24: [PokemonCenter.CeruleanCity],
    MapFRLG.VIRIDIAN_CITY: [PokemonCenter.ViridianCity],
    MapFRLG.PEWTER_CITY: [PokemonCenter.PewterCity],
    MapFRLG.CERULEAN_CITY: [PokemonCenter.CeruleanCity],
    MapFRLG.LAVENDER_TOWN: [PokemonCenter.LavenderTown],
    MapFRLG.VERMILION_CITY: [PokemonCenter.VermilionCity],
    MapFRLG.CELADON_CITY: [PokemonCenter.CeladonCity],
    MapFRLG.FUCHSIA_CITY: [PokemonCenter.FuchsiaCity],
    MapFRLG.CINNABAR_ISLAND: [PokemonCenter.CinnabarIsland],
    MapFRLG.SAFFRON_CITY: [PokemonCenter.SaffronCity],
}

_list_of_stats = ("hp", "attack", "defence", "special_attack", "special_defence", "speed")


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

        return current_location.has_encounters and current_location.map_group_and_number in closest_pokemon_centers

    def __init__(self):
        super().__init__()
        self._leave_pokemon_center = False
        self._go_healing = True
        self._level_balance = False
        self._ev_targets: StatsValues | None = None

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        action = handle_encounter(encounter, enable_auto_battle=True)
        lead_pokemon = get_party()[0]
        # EV yield doubled with Macho Brace and Pokerus (this effect stacks)
        ev_multiplier = 1
        if lead_pokemon.held_item is not None and lead_pokemon.held_item.name == "Macho Brace":
            ev_multiplier *= 2
        if lead_pokemon.pokerus_status.days_remaining > 0:
            ev_multiplier *= 2

        # Checks if opponent evs are desired
        good_yield = all(
            get_opponent().species.ev_yield[stat] * ev_multiplier + lead_pokemon.evs[stat] <= self._ev_targets[stat]
            for stat in _list_of_stats
        )
        # Fights if evs are desired and oppenent is not shiny meets a custom catch filter
        if good_yield and action is BattleAction.Fight:
            return NoRotateLeadDefaultBattleStrategy()
        elif action is BattleAction.Fight:
            return BattleAction.RunAway
        else:
            return action

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        lead_pokemon = get_party()[0]
        if (
            not DefaultBattleStrategy().pokemon_can_battle(lead_pokemon)
            or lead_pokemon.status_condition is not StatusCondition.Healthy
        ):
            self._go_healing = True

        ev_multiplier = 1
        if lead_pokemon.held_item is not None and lead_pokemon.held_item.name == "Macho Brace":
            ev_multiplier *= 2
        if lead_pokemon.pokerus_status.days_remaining > 0:
            ev_multiplier *= 2

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
            *[f"{str(lead_pokemon.evs[stat])}/{str(self._ev_targets[stat])}" for stat in _list_of_stats],
            str(lead_pokemon.evs.sum()),
        )
        console.print(ev_table)

        if outcome == BattleOutcome.RanAway:
            context.message = "EVs not needed, skipping"
        if outcome == BattleOutcome.Won:
            context.message = (
                f"{'/'.join([str(get_opponent().species.ev_yield[stat]) for stat in _list_of_stats])} EVs gained"
            )

    def on_whiteout(self) -> bool:
        self._leave_pokemon_center = True
        return True

    def run(self) -> Generator:
        training_spot = get_map_data_for_current_position()
        if not training_spot.has_encounters:
            raise BotModeError("There are no encounters on this tile.")

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
        target_pokemon = get_party()[0]
        self._ev_targets = ask_for_ev_targets(target_pokemon)
        if self._ev_targets is None:
            # If the user just closed the window without answering
            context.set_manual_mode()
            return

        # Checks for EV target sensibility
        if self._ev_targets.sum() > 510:
            raise BotModeError("Total EVs must be 510 or below.")

        for stat in _list_of_stats:
            if self._ev_targets[stat] < 0 or self._ev_targets[stat] > 255:
                raise BotModeError(
                    f"Selected EV target for {stat} ('{self._ev_targets[stat]}') is invalid (must be between 0 and 255.)"
                )
            if target_pokemon.evs[stat] > self._ev_targets[stat]:
                raise BotModeError(
                    f"Selected EV target for {stat} ('{self._ev_targets[stat]}') must be equal to or larger than the current EV number ({target_pokemon.evs[stat]}.)"
                )

        while True:
            if self._leave_pokemon_center:
                yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
            elif self._go_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._go_healing = False

            yield from navigate_to(training_spot_map, training_spot_coordinates)
            yield from spin(stop_condition=lambda: self._go_healing or self._leave_pokemon_center)
