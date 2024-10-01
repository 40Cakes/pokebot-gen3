from typing import Generator

from modules.battle_strategies import TurnAction
from modules.context import context
from modules.map import get_map_data_for_current_position, get_map_data
from modules.map_data import MapFRLG, MapRSE, PokemonCenter, get_map_enum
from modules.map_path import calculate_path, PathFindingError
from modules.modes import BattleAction
from modules.player import get_player_avatar
from modules.pokemon import get_party, get_opponent, StatusCondition
from ._interface import BotMode, BotModeError
from .util import navigate_to, heal_in_pokemon_center, change_lead_party_pokemon, spin
from ..battle_state import BattleOutcome, BattleState
from ..battle_strategies import BattleStrategy, DefaultBattleStrategy
from ..battle_strategies.level_balancing import LevelBalancingBattleStrategy
from ..encounter import handle_encounter
from ..gui.multi_select_window import ask_for_choice, Selection
from ..runtime import get_sprites_path
from ..sprites import get_sprite

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


class LevelGrindMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Level Grind"

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

    def on_battle_started(self) -> BattleAction | BattleStrategy | None:
        action = handle_encounter(get_opponent(), enable_auto_battle=True)
        if action is BattleAction.Fight:
            if self._level_balance:
                return LevelBalancingBattleStrategy()
            else:
                return DefaultBattleStrategy()
        else:
            return action

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        lead_pokemon = get_party()[0]
        if (
            not DefaultBattleStrategy().pokemon_can_battle(lead_pokemon)
            or lead_pokemon.status_condition is not StatusCondition.Healthy
        ):
            self._go_healing = True

    def on_whiteout(self) -> bool:
        self._leave_pokemon_center = True
        return True

    def run(self) -> Generator:
        training_spot = get_map_data_for_current_position()
        if not training_spot.has_encounters:
            raise BotModeError("There are no encounters on this tile.")
        if training_spot.is_surfable:
            raise BotModeError("This mode does not work when surfing.")

        # The first member of the party might be an egg, in which case we want to use the
        # first available Pokémon as lead instead.
        party_lead_pokemon = None
        party_lead_index = 0
        for index in range(len(get_party())):
            pokemon = get_party()[index]
            if not pokemon.is_egg:
                party_lead_pokemon = pokemon
                party_lead_index = index
                break

        level_mode_choice = ask_for_choice(
            [
                Selection(
                    f"Level only first one\nin party ({party_lead_pokemon.species_name_for_stats})",
                    get_sprite(party_lead_pokemon),
                ),
                Selection("Level-balance all\nparty Pokémon", get_sprites_path() / "items" / "Rare Candy.png"),
            ],
            "What to level?",
        )

        if level_mode_choice is None:
            context.set_manual_mode()
            yield
            return
        elif level_mode_choice.startswith("Level-balance"):
            self._level_balance = True
        else:
            self._level_balance = False

        if self._level_balance:
            party_lead_index = LevelBalancingBattleStrategy().choose_new_lead_after_battle()

        if party_lead_index:
            yield from change_lead_party_pokemon(party_lead_index)

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

        while True:
            if self._leave_pokemon_center:
                yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
            elif self._go_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._go_healing = False

            yield from navigate_to(training_spot_map, training_spot_coordinates)
            yield from spin(stop_condition=lambda: self._go_healing or self._leave_pokemon_center)
