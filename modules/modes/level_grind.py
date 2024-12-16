from typing import Generator

from modules.context import context
from modules.map import get_map_data_for_current_position, get_map_data
from modules.map_data import MapFRLG, MapRSE, PokemonCenter, get_map_enum
from modules.map_path import calculate_path, PathFindingError
from modules.modes import BattleAction
from modules.player import get_player_avatar
from modules.pokemon import StatusCondition
from modules.pokemon_party import get_party
from ._asserts import assert_party_has_damaging_move
from ._interface import BotMode, BotModeError
from .util import navigate_to, heal_in_pokemon_center, change_lead_party_pokemon, spin
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy, DefaultBattleStrategy
from ..battle_strategies.level_balancing import LevelBalancingBattleStrategy
from ..battle_strategies.level_up import LevelUpLeadBattleStrategy
from ..encounter import handle_encounter, EncounterInfo
from ..gui.multi_select_window import ask_for_choice, Selection, ask_for_confirmation
from ..runtime import get_sprites_path
from ..sprites import get_sprite

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


class LevelGrindMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Level Grind"

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

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        action = handle_encounter(encounter, enable_auto_battle=True)
        if action is BattleAction.Fight:
            if self._level_balance:
                return LevelBalancingBattleStrategy()
            else:
                return LevelUpLeadBattleStrategy()
        else:
            return action

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        lead_pokemon = get_party()[0]

        if self._level_balance:
            if (
                not DefaultBattleStrategy().pokemon_can_battle(lead_pokemon)
                or lead_pokemon.status_condition is not StatusCondition.Healthy
            ):
                self._go_healing = True
        else:
            if lead_pokemon.current_hp_percentage < context.config.battle.hp_threshold:
                self._go_healing = True

            lead_pokemon_has_damaging_moves = False
            lead_pokemon_has_damaging_move_with_pp = False
            for learned_move in lead_pokemon.moves:
                if (
                    learned_move is not None
                    and learned_move.move.base_power > 1
                    and learned_move.move.name not in context.config.battle.banned_moves
                ):
                    lead_pokemon_has_damaging_moves = True
                    if learned_move.pp > 0:
                        lead_pokemon_has_damaging_move_with_pp = True
            if lead_pokemon_has_damaging_moves and not lead_pokemon_has_damaging_move_with_pp:
                self._go_healing = True

            if not LevelUpLeadBattleStrategy().party_can_battle():
                self._go_healing = True

    def on_whiteout(self) -> bool:
        self._leave_pokemon_center = True
        return True

    def run(self) -> Generator:
        # Check training spot first to see if it has encounters to not print multi choices windows for nothing
        training_spot = self._get_training_spot()

        party_lead_pokemon, party_lead_index = self._get_party_lead()
        level_mode_choice = self._ask_for_leveling_mode(party_lead_pokemon)

        if level_mode_choice is None:
            context.set_manual_mode()
            yield
            return

        if level_mode_choice.startswith("Level-balance"):
            self._level_balance = True
        else:
            assert_party_has_damaging_move("No Pokémon in the party has a usable attacking move!")

            if not LevelUpLeadBattleStrategy().pokemon_can_battle(party_lead_pokemon):
                user_confirmed = ask_for_confirmation(
                    "Your party leader has no battle moves. The bot will maybe swap with other Pokémon depending on your bot configuration, causing them to gain XP. Are you sure you want to proceed with this strategy?"
                )

                if not user_confirmed:
                    context.set_manual_mode()
                    yield
                    return

                if context.config.battle.lead_cannot_battle_action == "flee":
                    raise BotModeError(
                        "Cannot level grind because your leader has no battle moves and lead_cannot_battle_action is set to flee!"
                    )

                if user_confirmed:
                    self._level_balance = False
                else:
                    context.set_manual_mode()

        if self._level_balance:
            party_lead_index = LevelBalancingBattleStrategy().choose_new_lead_after_battle()

        if party_lead_index:
            yield from change_lead_party_pokemon(party_lead_index)

        pokemon_center = self._find_closest_pokemon_center(training_spot)

        yield from self._leveling_loop(training_spot, pokemon_center)

    def _get_training_spot(self):
        training_spot = get_map_data_for_current_position()
        if not training_spot.has_encounters:
            raise BotModeError("There are no encounters on this tile.")
        return training_spot

    def _get_party_lead(self):
        for index, pokemon in enumerate(get_party()):
            if not pokemon.is_egg:
                return pokemon, index
        raise BotModeError("No valid Pokémon found in the party.")

    def _ask_for_leveling_mode(self, party_lead_pokemon):
        return ask_for_choice(
            [
                Selection(
                    f"Level only first one\nin party ({party_lead_pokemon.species_name_for_stats})",
                    get_sprite(party_lead_pokemon),
                ),
                Selection("Level-balance all\nparty Pokémon", get_sprites_path() / "items" / "Rare Candy.png"),
            ],
            "What to level?",
        )

    def _find_closest_pokemon_center(self, training_spot):
        training_spot_map = get_map_enum(training_spot)
        pokemon_center = None
        path_length_to_pokemon_center = None

        if training_spot_map in closest_pokemon_centers:
            for pokemon_center_candidate in closest_pokemon_centers[training_spot_map]:
                try:
                    path_length = self._calculate_path_length(training_spot, pokemon_center_candidate)
                    if path_length_to_pokemon_center is None or path_length < path_length_to_pokemon_center:
                        pokemon_center = pokemon_center_candidate
                        path_length_to_pokemon_center = path_length
                except PathFindingError:
                    pass

        if pokemon_center is None:
            raise BotModeError("Could not find a suitable from here to a Pokemon Center nearby.")

        return pokemon_center

    def _calculate_path_length(self, training_spot, pokemon_center_candidate) -> int:
        center_location = get_map_data(*pokemon_center_candidate.value)
        path_to = calculate_path(training_spot, center_location)
        path_from = []
        return len(path_to) + len(path_from)

    def _leveling_loop(self, training_spot, pokemon_center):
        training_spot_map = get_map_enum(training_spot)
        training_spot_coordinates = training_spot.local_position

        while True:
            if self._leave_pokemon_center:
                yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
            elif self._go_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._go_healing = False

            yield from navigate_to(training_spot_map, training_spot_coordinates)
            yield from spin(stop_condition=lambda: self._go_healing or self._leave_pokemon_center)
