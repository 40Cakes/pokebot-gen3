from typing import Generator

from rich.table import Table

from modules.context import context
from modules.map import get_map_data_for_current_position, get_effective_encounter_rates_for_current_map
from modules.map_data import get_map_enum
from modules.modes import BattleAction
from modules.player import get_player_avatar
from modules.pokemon import get_opponent, StatusCondition, StatsValues, Pokemon
from modules.pokemon_party import get_party
from ._interface import BotMode, BotModeError
from .util import navigate_to, heal_in_pokemon_center, spin
from .util.map import map_has_pokemon_center_nearby, find_closest_pokemon_center
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy, DefaultBattleStrategy
from ..console import console
from ..encounter import handle_encounter, EncounterInfo
from ..gui.ev_selection_window import ask_for_ev_targets

_list_of_stats = ("hp", "attack", "defence", "special_attack", "special_defence", "speed")


def _is_target_reached(pokemon: Pokemon, target_evs: StatsValues) -> bool:
    return all([pokemon.evs[stat] >= target_evs[stat] for stat in _list_of_stats])


def _current_encounter_table_helps_with_target(pokemon: Pokemon, target_evs: StatsValues) -> bool:
    for encounter in get_effective_encounter_rates_for_current_map().land_encounters:
        useful_encounter = False
        for stat in _list_of_stats:
            if encounter.species.ev_yield[stat] > 0:
                if (
                    pokemon.evs[stat] < target_evs[stat]
                    and pokemon.evs[stat] + encounter.species.ev_yield[stat] <= target_evs[stat]
                ):
                    return True
                else:
                    useful_encounter = False
                    break
        if useful_encounter:
            return True
    return False


def _assert_that_running_makes_sense(pokemon: Pokemon, target_evs: StatsValues) -> None:
    if _is_target_reached(pokemon, target_evs):
        raise BotModeError("The target EVs have been reached.")

    if not _current_encounter_table_helps_with_target(pokemon, target_evs):
        raise BotModeError(
            "There are no land encounters on this map that yield EVs we want. Choose a different map to train on."
        )


def _print_target_table(pokemon: Pokemon, target_evs: StatsValues) -> None:
    def format_stat(stat: str) -> str:
        if target_evs[stat] == 0 or target_evs[stat] < pokemon.evs[stat]:
            return str(pokemon.evs[stat])
        elif target_evs[stat] == pokemon.evs[stat]:
            return f"[green]{pokemon.evs[stat]}/{target_evs[stat]}[/green]"
        else:
            return f"[yellow]{pokemon.evs[stat]}/{target_evs[stat]}[/yellow]"

    ev_table = Table(title=f"{pokemon.species.name} EVs/Target")
    ev_table.add_column("HP", justify="center")
    ev_table.add_column("ATK", justify="center")
    ev_table.add_column("DEF", justify="center")
    ev_table.add_column("SPATK", justify="center")
    ev_table.add_column("SPDEF", justify="center")
    ev_table.add_column("SPD", justify="center")
    ev_table.add_column("Total", justify="right")
    ev_table.add_row(
        *[format_stat(stat) for stat in _list_of_stats],
        str(pokemon.evs.sum()),
    )
    console.print(ev_table)


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

        return current_location.has_encounters and map_has_pokemon_center_nearby(current_location.map_group_and_number)

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

        # Ugly table to keep track of progress
        _print_target_table(lead_pokemon, self._ev_targets)

        if outcome == BattleOutcome.RanAway:
            context.message = "EVs not needed, skipping"
        if outcome == BattleOutcome.Won:
            context.message = (
                f"{'/'.join([str(get_opponent().species.ev_yield[stat]) for stat in _list_of_stats])} EVs gained"
            )

        _assert_that_running_makes_sense(lead_pokemon, self._ev_targets)

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
        pokemon_center = find_closest_pokemon_center(training_spot)

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

        _assert_that_running_makes_sense(target_pokemon, self._ev_targets)

        while True:
            if self._leave_pokemon_center:
                yield from navigate_to(get_player_avatar().map_group_and_number, (7, 8))
            elif self._go_healing:
                yield from heal_in_pokemon_center(pokemon_center)

            self._leave_pokemon_center = False
            self._go_healing = False

            yield from navigate_to(training_spot_map, training_spot_coordinates)
            yield from spin(stop_condition=lambda: self._go_healing or self._leave_pokemon_center)
