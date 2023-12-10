import random
from enum import Enum, auto
from pathlib import Path

from modules.context import context
from modules.data.map import MapFRLG
from modules.encounter import encounter_pokemon
from modules.files import get_rng_state_history, save_rng_state_history
from modules.gui.multi_select_window import Selection, MultiSelector, MultiSelectWindow
from modules.memory import (
    read_symbol,
    get_game_state,
    GameState,
    write_symbol,
    unpack_uint32,
    pack_uint32,
    get_event_flag,
)
from modules.player import get_player_avatar
from modules.pokemon import get_opponent
from modules.tasks import task_is_active

config = context.config


class ModeLegendaryBirdsStates(Enum):
    RESET = auto()
    TITLE = auto()
    OVERWORLD = auto()
    INJECT_RNG = auto()
    RNG_CHECK = auto()
    BATTLE = auto()
    OPPONENT_CRY_START = auto()
    OPPONENT_CRY_END = auto()
    LOG_BIRD = auto()


class ModeLegendaryBirds:
    def __init__(self) -> None:
        if not context.selected_pokemon:
            player_avatar = get_player_avatar()
            sprites = Path(__file__).parent.parent.parent / "sprites" / "pokemon" / "normal"
            conditions = {
                "Articuno": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and not get_event_flag("FLAG_FOUGHT_ARTICUNO")
                        and player_avatar.map_group_and_number == MapFRLG.SEAFOAM_ISLANDS_D.value
                        and (
                            (player_avatar.local_coordinates == (9, 3) and player_avatar.facing_direction == "Up")
                            or (player_avatar.local_coordinates == (8, 2) and player_avatar.facing_direction == "Right")
                            or (player_avatar.local_coordinates == (9, 1) and player_avatar.facing_direction == "Down")
                            or (player_avatar.local_coordinates == (10, 2) and player_avatar.facing_direction == "Left")
                        )
                    )
                ),
                "Zapdos": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and not get_event_flag("FLAG_FOUGHT_ZAPDOS")
                        and player_avatar.map_group_and_number == MapFRLG.POWER_PLANT.value
                        and (
                            (player_avatar.local_coordinates == (5, 12) and player_avatar.facing_direction == "Up")
                            or (player_avatar.local_coordinates == (4, 11) and player_avatar.facing_direction == "Right")
                            or (player_avatar.local_coordinates == (5, 10) and player_avatar.facing_direction == "Down")
                            or (player_avatar.local_coordinates == (6, 11) and player_avatar.facing_direction == "Left")
                        )
                    )
                ),
                "Moltres": bool(
                    (
                        context.rom.game_title in ["POKEMON FIRE", "POKEMON LEAF"]
                        and not get_event_flag("FLAG_FOUGHT_MOLTRES")
                        and player_avatar.map_group_and_number == MapFRLG.MT_EMBER_E.value
                        and (
                            (player_avatar.local_coordinates == (9, 7) and player_avatar.facing_direction == "Up")
                            or (player_avatar.local_coordinates == (8, 6) and player_avatar.facing_direction == "Right")
                            or (player_avatar.local_coordinates == (9, 5) and player_avatar.facing_direction == "Down")
                            or (player_avatar.local_coordinates == (10, 6) and player_avatar.facing_direction == "Left")
                        )
                    )
                ),
            }

            selections = [
                Selection(
                    button_label="Articuno",
                    button_enable=conditions["Articuno"],
                    button_tooltip="Select Articuno"
                    if conditions["Articuno"]
                    else "Invalid location:\nPlace the player and save, facing Articuno in Seafoam Islands",
                    sprite=sprites / "Articuno.png",
                ),
                Selection(
                    button_label="Zapdos",
                    button_enable=conditions["Zapdos"],
                    button_tooltip="Select Zapdos"
                    if conditions["Zapdos"]
                    else "Invalid location:\nPlace the player and save, facing Zapdos in the Power Plant",
                    sprite=sprites / "Zapdos.png",
                ),
                Selection(
                    button_label="Moltres",
                    button_enable=conditions["Moltres"],
                    button_tooltip="Select Moltres"
                    if conditions["Moltres"]
                    else "Invalid location:\nPlace the player and save, facing Moltres at the top of Mt. Ember",
                    sprite=sprites / "Moltres.png",
                ),
            ]

            options = MultiSelector("Select a legendary bird...", selections)
            MultiSelectWindow(context.gui.window, options)

        if context.selected_pokemon not in ["Articuno", "Zapdos", "Moltres"]:
            return

        if not config.cheats.random_soft_reset_rng:
            self.rng_history: list = get_rng_state_history(context.selected_pokemon)

        self.state: ModeLegendaryBirdsStates = ModeLegendaryBirdsStates.RESET

    def update_state(self, state: ModeLegendaryBirdsStates):
        self.state: ModeLegendaryBirdsStates = state

    def step(self):
        while True:
            match self.state:
                case ModeLegendaryBirdsStates.RESET:
                    context.emulator.reset()
                    self.update_state(ModeLegendaryBirdsStates.TITLE)

                case ModeLegendaryBirdsStates.TITLE:
                    match get_game_state():
                        case GameState.TITLE_SCREEN:
                            context.emulator.press_button(random.choice(["A", "Start", "Left", "Right", "Up"]))
                        case GameState.MAIN_MENU:
                            if task_is_active("Task_HandleMenuInput"):
                                context.message = "Waiting for a unique frame before continuing..."
                                self.update_state(ModeLegendaryBirdsStates.RNG_CHECK)
                                continue

                case ModeLegendaryBirdsStates.RNG_CHECK:
                    if config.cheats.random_soft_reset_rng:
                        self.update_state(ModeLegendaryBirdsStates.OVERWORLD)
                    else:
                        rng = unpack_uint32(read_symbol("gRngValue"))
                        if rng in self.rng_history:
                            pass
                        else:
                            self.rng_history.append(rng)
                            save_rng_state_history(context.selected_pokemon, self.rng_history)
                            self.update_state(ModeLegendaryBirdsStates.OVERWORLD)
                            continue

                case ModeLegendaryBirdsStates.OVERWORLD:
                    if not task_is_active("Task_DrawFieldMessageBox"):
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeLegendaryBirdsStates.INJECT_RNG)
                        continue

                case ModeLegendaryBirdsStates.INJECT_RNG:
                    if config.cheats.random_soft_reset_rng:
                        write_symbol("gRngValue", pack_uint32(random.randint(0, 2**32 - 1)))
                    self.update_state(ModeLegendaryBirdsStates.BATTLE)

                case ModeLegendaryBirdsStates.BATTLE:
                    if get_game_state() != GameState.BATTLE:
                        context.emulator.press_button("A")
                    else:
                        self.update_state(ModeLegendaryBirdsStates.OPPONENT_CRY_START)
                        continue

                case ModeLegendaryBirdsStates.OPPONENT_CRY_START:
                    if not task_is_active("Task_DuckBGMForPokemonCry"):
                        context.emulator.press_button("B")
                    else:
                        self.update_state(ModeLegendaryBirdsStates.OPPONENT_CRY_END)
                        continue

                case ModeLegendaryBirdsStates.OPPONENT_CRY_END:  # Ensures starter sprite is fully visible before resetting
                    if task_is_active("Task_DuckBGMForPokemonCry"):
                        pass
                    else:
                        self.update_state(ModeLegendaryBirdsStates.LOG_BIRD)
                        continue

                case ModeLegendaryBirdsStates.LOG_BIRD:
                    encounter_pokemon(get_opponent())
                    return

            yield
