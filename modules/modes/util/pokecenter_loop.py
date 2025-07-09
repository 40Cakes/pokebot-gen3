from collections.abc import Callable
from typing import Optional, Literal

from modules.battle_strategies import BattleStrategy, DefaultBattleStrategy
from modules.context import context
from modules.debug import debug
from modules.encounter import handle_encounter
from modules.map import get_map_data_for_current_position, get_effective_encounter_rates_for_current_map
from modules.map_data import MapFRLG, get_map_enum
from modules.modes import BotModeError, BattleAction
from modules.modes.util import (
    apply_white_flute_if_available,
    find_closest_pokemon_center,
    navigate_to,
    heal_in_pokemon_center,
    spin,
    fish,
)
from modules.player import get_player_location
from modules.pokemon_party import get_party


class PokecenterLoopController:
    def __init__(self, focus_on_lead_pokemon: bool = False):
        self.battle_strategy = DefaultBattleStrategy
        self._focus_on_lead_pokemon = focus_on_lead_pokemon
        self._needs_healing = False
        self._leave_pokemon_center = False

    def on_battle_started(self, encounter: "EncounterInfo | None") -> BattleAction | BattleStrategy:
        action = handle_encounter(encounter, enable_auto_battle=True)
        return self.battle_strategy() if action is BattleAction.Fight else action

    def on_battle_ended(self) -> None:
        lead_pokemon = get_party().non_eggs[0]
        if not self.battle_strategy().pokemon_can_battle(lead_pokemon):
            # Generally, if the lead Pokémon cannot battle (out of PP or fainted) we want to go and
            # heal, even in Level-balancing mode (because in that case the weakest Pokémon should
            # always be the lead Pokémon.)
            #
            # But there's one exception: If the lead Pokémon is out of PP but does not even know any
            # damaging moves (think Magikarp, Abra, ...) but the party as a whole still has some
            # capable Pokémon, we do NOT want to heal because the strategy is to immediately switch
            # in the strongest Pokémon immediately to allow the weak Pokémon to gain at least some
            # PP.
            lead_knows_damaging_moves = any(
                [learned_move.move.base_power for learned_move in lead_pokemon.moves if learned_move is not None]
            )
            if (
                lead_pokemon.current_hp <= 0
                or lead_knows_damaging_moves
                or not self.battle_strategy().party_can_battle()
            ):
                self._needs_healing = True

    def on_whiteout(self) -> bool:
        self._leave_pokemon_center = True
        return True

    def verify_on_start(self):
        current_location = get_map_data_for_current_position()
        if not current_location.has_encounters:
            raise BotModeError("There are not encounters on this tile.")

        effective_encounters = get_effective_encounter_rates_for_current_map()
        if (not current_location.is_surfable and len(effective_encounters.land_encounters) == 0) or (
            current_location.is_surfable and len(effective_encounters.surf_encounters) == 0
        ):
            raise BotModeError(
                "Currently, no encounters can happen on this map. This might be due to active Repel, or because this map simply doesn't have any."
            )

        # This will check whether there is a valid path to and from a
        # Pokémon Center.
        find_closest_pokemon_center(current_location)

    @debug.track
    def run(self, stop_condition: Optional[Callable[[], bool]] = None, activity: Literal["spin", "fish"] = "spin"):
        encounter_spot = get_map_data_for_current_position()
        pokemon_center = find_closest_pokemon_center(encounter_spot)

        # We need to heal at the start of the battle to make sure that
        # we will respawn at the chosen Pokémon Center in case of a
        # whiteout.
        self._needs_healing = True

        while stop_condition is None or not stop_condition():
            if self._leave_pokemon_center:
                # This will run after a whiteout when the player respawns
                # inside the Pokémon Center.
                if context.rom.is_frlg:
                    current_map = get_player_location()[0]
                    if current_map is MapFRLG.PALLET_TOWN_PLAYERS_HOUSE_1F:
                        door_coordinates = (4, 8)
                    else:
                        door_coordinates = (7, 8)
                    yield from navigate_to(current_map, door_coordinates)
            elif self._needs_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._needs_healing = False

            yield from navigate_to(get_map_enum(encounter_spot), encounter_spot.local_position)

            def activity_stop_condition() -> bool:
                return (
                    self._needs_healing
                    or self._leave_pokemon_center
                    or (stop_condition is not None and stop_condition())
                )

            if activity == "fish":
                yield from fish(stop_condition=activity_stop_condition, loop=True)
            else:
                yield from apply_white_flute_if_available()
                yield from spin(stop_condition=activity_stop_condition)
