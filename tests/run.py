import sys
import unittest
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent))

from modules.config import Config, Logging
from modules.config.schemas_v1 import LoggingSavePK3
from modules.fishing import FishingAttempt
from modules.game import set_rom
from modules.libmgba import LibmgbaEmulator
from modules.modes import BotMode, get_bot_listeners, FrameInfo
from modules.modes.util import *
from modules.profiles import Profile
from modules.save_import import guess_rom_from_save_state
from modules.stats import StatsDatabase, Encounter
from modules.tasks import get_global_script_context, get_tasks

if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome
    from modules.encounter import EncounterInfo
    from modules.pokemon import Pokemon


class MockStatsDatabase(StatsDatabase):
    def __init__(self):
        self.last_fishing_attempt: FishingAttempt | None = None
        self.last_encounter: Encounter | None = None
        self.encounter_rate = 0
        self.encounter_rate_at_1x = 0
        self.logged_encounters: list[Encounter] = []

    def log_encounter(self, encounter_info: "EncounterInfo") -> Encounter:
        self.last_encounter = Encounter(
            1,
            1,
            encounter_info.catch_filters_result,
            datetime.now(),
            encounter_info.map,
            encounter_info.coordinates,
            "Automated Test",
            encounter_info.type,
            None,
            encounter_info.pokemon,
        )
        self.logged_encounters.append(self.last_encounter)
        return self.last_encounter

    def log_end_of_battle(self, battle_outcome: "BattleOutcome", encounter_info: "EncounterInfo"):
        if self.last_encounter:
            self.last_encounter.outcome = battle_outcome
            self.logged_encounters[-1].outcome = battle_outcome

    def log_fishing_attempt(self, attempt: FishingAttempt):
        self.last_fishing_attempt = attempt

    def log_pickup_items(self, picked_up_items: list["Item"]) -> None:
        pass

    def reset_shiny_phase(self, encounter: Encounter):
        pass


class AutomatedTestBotMode(BotMode):
    def __init__(
        self,
        run: Generator,
        on_battle_started: Callable[["EncounterInfo | None"], "BattleAction | BattleOutcome | None"] | None = None,
        on_battle_ended: Callable[["BattleOutcome"], None] | None = None,
        on_pokemon_evolving_after_battle: Callable[["Pokemon", int], bool] | None = None,
        on_pickup_threshold_reached: Callable[[], bool] | None = None,
        on_spotted_by_trainer: Callable[[], None] | None = None,
        on_pokenav_call: Callable[[], None] | None = None,
        on_repel_effect_ended: Callable[[], None] | None = None,
        on_pokemon_fainted_due_to_poison: Callable[["Pokemon", int], None] | None = None,
        on_whiteout: Callable[[], bool] | None = None,
        on_safari_zone_timeout: Callable[[], bool] | None = None,
        on_egg_hatched: Callable[["EncounterInfo", int], None] | None = None,
    ):
        super().__init__()
        self.allow_ending_on_manual_mode = False
        self._run = run
        self._on_battle_started = on_battle_started
        self._on_battle_ended = on_battle_ended
        self._on_pokemon_evolving_after_battle = on_pokemon_evolving_after_battle
        self._on_pickup_threshold_reached = on_pickup_threshold_reached
        self._on_spotted_by_trainer = on_spotted_by_trainer
        self._on_pokenav_call = on_pokenav_call
        self._on_repel_effect_ended = on_repel_effect_ended
        self._on_pokemon_fainted_due_to_poison = on_pokemon_fainted_due_to_poison
        self._on_whiteout = on_whiteout
        self._on_safari_zone_timeout = on_safari_zone_timeout
        self._on_egg_hatched = on_egg_hatched

    @staticmethod
    def name() -> str:
        return "Automated Test"

    def on_battle_started(self, encounter: "EncounterInfo | None") -> "BattleAction | BattleStrategy | None":
        if self._on_battle_started is not None:
            return self._on_battle_started(encounter)
        else:
            return super().on_battle_started(encounter)

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if self._on_battle_ended is not None:
            return self._on_battle_ended(outcome)
        else:
            return super().on_battle_ended(outcome)

    def on_pokemon_evolving_after_battle(self, pokemon: "Pokemon", party_index: int) -> bool:
        if self._on_pokemon_evolving_after_battle is not None:
            return self._on_pokemon_evolving_after_battle(pokemon, party_index)
        else:
            return super().on_pokemon_evolving_after_battle(pokemon, party_index)

    def on_pickup_threshold_reached(self) -> bool:
        if self._on_pickup_threshold_reached is not None:
            return self._on_pickup_threshold_reached()
        else:
            return super().on_pickup_threshold_reached()

    def on_spotted_by_trainer(self) -> None:
        if self._on_spotted_by_trainer is not None:
            return self._on_spotted_by_trainer()
        else:
            return super().on_spotted_by_trainer()

    def on_pokenav_call(self) -> None:
        if self._on_pokenav_call is not None:
            return self._on_pokenav_call()
        else:
            return super().on_pokenav_call()

    def on_repel_effect_ended(self) -> None:
        if self._on_repel_effect_ended is not None:
            return self._on_repel_effect_ended()
        else:
            return super().on_repel_effect_ended()

    def on_pokemon_fainted_due_to_poison(self, pokemon: "Pokemon", party_index: int) -> None:
        if self._on_pokemon_fainted_due_to_poison is not None:
            return self._on_pokemon_fainted_due_to_poison(pokemon, party_index)
        else:
            return super().on_pokemon_fainted_due_to_poison(pokemon, party_index)

    def on_whiteout(self) -> bool:
        if self._on_whiteout is not None:
            return self._on_whiteout()
        else:
            return super().on_whiteout()

    def on_safari_zone_timeout(self) -> bool:
        if self._on_safari_zone_timeout is not None:
            return self._on_safari_zone_timeout()
        else:
            return super().on_safari_zone_timeout()

    def on_egg_hatched(self, encounter: "EncounterInfo", party_index: int) -> None:
        if self._on_egg_hatched is not None:
            return self._on_egg_hatched(encounter, party_index)
        else:
            return super().on_egg_hatched(encounter, party_index)

    def run(self) -> Generator:
        yield from self._run
        if context.bot_mode == "Manual" and not self.allow_ending_on_manual_mode:
            raise AssertionError("Bot switched to Manual mode.")


def _set_up_test_emulator(profile: Profile):
    context.testing = True
    context.config = Config()
    context.config.logging = Logging(
        save_pk3=LoggingSavePK3(shiny=False, custom=False, roamer=False),
        log_encounters=True,
        log_encounters_to_console=False,
        desktop_notifications=False,
        shiny_gifs=False,
        tcg_cards=False,
    )
    context.profile = profile
    set_rom(profile.rom)

    def do_nothing():
        pass

    context.emulator = LibmgbaEmulator(context.profile, do_nothing, is_test_run=True)
    context.stats = MockStatsDatabase()
    context.bot_listeners = get_bot_listeners(context.rom)
    context.frame = 0
    context.controller_stack.clear()
    context.emulator.set_audio_enabled(False)
    context.emulator.set_video_enabled(False)
    context.emulator.set_throttle(False)


def _load_test_state(state_file: Path) -> None:
    with open(state_file, "rb") as handle:
        rom, state_data, save_data = guess_rom_from_save_state(handle, None)
    context.profile = Profile(rom, Path(__file__).parent, datetime.now())
    _set_up_test_emulator(context.profile)
    if save_data is not None:
        context.emulator.load_save_game(save_data)
    context.emulator.load_save_state(state_data)


def _run_test(test_generator: Generator) -> None:
    previous_frame_info: FrameInfo | None = None
    bot_mode = AutomatedTestBotMode(test_generator)
    context.controller_stack.append(bot_mode.run())
    context.bot_mode_instance = bot_mode
    context.stats.logged_encounters.clear()
    context.stats.last_encounter = None
    context._current_bot_mode = "Automated Test"

    while True:
        context.frame += 1

        game_state = get_game_state()
        script_context = get_global_script_context()
        script_stack = script_context.stack if script_context is not None and script_context.is_active else []
        task_list = get_tasks()
        if task_list is not None:
            active_tasks = [task.symbol.lower() for task in task_list]
        else:
            active_tasks = []

        frame_info = FrameInfo(
            frame_count=context.emulator.get_frame_count(),
            game_state=game_state,
            active_tasks=active_tasks,
            script_stack=script_stack,
            previous_frame=previous_frame_info,
        )

        # Reset all bot listeners if the emulator has been reset.
        if previous_frame_info is not None and previous_frame_info.frame_count > frame_info.frame_count:
            context.bot_listeners = get_bot_listeners(context.rom)

        for listener in context.bot_listeners.copy():
            listener.handle_frame(bot_mode, frame_info)
        if len(context.controller_stack) > 0:
            try:
                next(context.controller_stack[-1])
            except (StopIteration, GeneratorExit):
                context.controller_stack.pop()
        else:
            break

        context.emulator.run_single_frame()
        previous_frame_info = frame_info
        previous_frame_info.previous_frame = None


def with_save_state(state_file_name: str):
    def decorator(generator_function):
        @wraps(generator_function)
        def wrapper_function(*args, **kwargs):
            state_path = Path(__file__).parent / state_file_name
            _load_test_state(state_path)
            _run_test(generator_function(*args, **kwargs))
            return None

        return wrapper_function

    return decorator


def with_frame_timeout(timeout_in_frames: int):
    def decorator(generator_function):
        @wraps(generator_function)
        def wrapper_function(*args, **kwargs):
            frames_remaining = timeout_in_frames
            for _ in generator_function(*args, **kwargs):
                yield
                frames_remaining -= 1
                if frames_remaining <= 0:
                    context.emulator.set_video_enabled(True)
                    yield
                    screenshot = context.emulator.get_screenshot()
                    with open("error.png", "wb") as file:
                        screenshot.save(file, format="PNG")
                    raise AssertionError(f"A timeout of {timeout_in_frames} frames has been reached.")

        return wrapper_function

    return decorator


class MockValues:
    def __init__(self):
        self._choice = ""
        self._rng_seed = 0xFFFF_FFFF

    @property
    def choice(self) -> str:
        return self._choice

    @choice.setter
    def choice(self, choice: str) -> None:
        self._choice = choice

    @property
    def rng_seed(self) -> int:
        seed_to_return = self._rng_seed
        self._rng_seed = (1103515245 * self._rng_seed + 24691) & 0xFFFF_FFFF
        return seed_to_return

    @rng_seed.setter
    def rng_seed(self, rng_seed: int) -> None:
        self._rng_seed = rng_seed

    def mocked_ask_for_choice(self, *args, **kwargs) -> str:
        return self.choice

    def mocked_wait_for_unique_rng_value(self, *args, **kwargs) -> Generator:
        write_symbol("gRngValue", pack_uint32(self.rng_seed))
        yield


mock_values = MockValues()


if __name__ == "__main__":
    from rich.console import Console

    mock_console = Console(quiet=True)

    with patch("modules.gui.multi_select_window.ask_for_choice", new=mock_values.mocked_ask_for_choice):
        with patch("modules.modes.util.wait_for_unique_rng_value", new=mock_values.mocked_wait_for_unique_rng_value):
            with patch("modules.console.console", new=mock_console):
                with patch("tests.run.mock_values", new=mock_values):
                    suite = unittest.defaultTestLoader.discover(str(Path(__file__).parent), "test_*.py")
                    runner = unittest.TextTestRunner()
                    runner.run(suite)
