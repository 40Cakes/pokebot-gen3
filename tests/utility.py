import sys
import unittest
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Generator, Optional, TypeAlias
from unittest import mock

from rich.console import Console

sys.path.append(str(Path(__file__).parent.parent))

from modules.modes._interface import BotMode
from modules.context import context

if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome
    from modules.encounter import EncounterInfo
    from modules.fishing import FishingAttempt
    from modules.items import Item
    from modules.modes import FrameInfo, BattleAction
    from modules.pokemon import Pokemon
    from modules.profiles import Profile
    from modules.roms import ROM
    from modules.stats import Encounter


class MockStatsDatabase:
    def __init__(self):
        self.last_fishing_attempt: "FishingAttempt | None" = None
        self.last_encounter: "Encounter | None" = None
        self.encounter_rate = 0
        self.encounter_rate_at_1x = 0
        self.logged_encounters: list["Encounter"] = []

    def log_encounter(self, encounter_info: "EncounterInfo") -> "Encounter":
        from modules.stats import Encounter

        self.last_encounter = Encounter(
            1,
            1,
            encounter_info.catch_filters_result,
            datetime.now(),
            encounter_info.map,
            encounter_info.coordinates,
            AutomatedTestBotMode.name(),
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

    def log_fishing_attempt(self, attempt: "FishingAttempt"):
        self.last_fishing_attempt = attempt

    def log_pickup_items(self, picked_up_items: list["Item"]) -> None:
        pass

    def reset_shiny_phase(self, encounter: "Encounter"):
        pass


OnBattleStartedType: TypeAlias = Callable[["EncounterInfo | None"], "BattleAction | BattleOutcome | None"]
OnBattleEndedType: TypeAlias = Callable[["BattleOutcome"], None]
OnPokemonEvolvingAfterBattleType: TypeAlias = Callable[["Pokemon", int], bool]
OnPickupThresholdReachedType: TypeAlias = Callable[[], bool]
OnSpottedByTrainerType: TypeAlias = Callable[[], None]
OnPokenavCallType: TypeAlias = Callable[[], None]
OnRepelEffectEndedType: TypeAlias = Callable[[], None]
OnPokemonFaintedDueToPoisonType: TypeAlias = Callable[["Pokemon", int], None]
OnWhiteoutType: TypeAlias = Callable[[], bool]
OnSafariZoneTimeoutType: TypeAlias = Callable[[], bool]
OnEggHatchedType: TypeAlias = Callable[["EncounterInfo", int], None]


class AutomatedTestBotMode(BotMode):
    def __init__(
        self,
        run: Generator,
        on_battle_started: Optional[OnBattleStartedType] = None,
        on_battle_ended: Optional[OnBattleEndedType] = None,
        on_pokemon_evolving_after_battle: Optional[OnPokemonEvolvingAfterBattleType] = None,
        on_pickup_threshold_reached: Optional[OnPickupThresholdReachedType] = None,
        on_spotted_by_trainer: Optional[OnSpottedByTrainerType] = None,
        on_pokenav_call: Optional[OnPokenavCallType] = None,
        on_repel_effect_ended: Optional[OnRepelEffectEndedType] = None,
        on_pokemon_fainted_due_to_poison: Optional[OnPokemonFaintedDueToPoisonType] = None,
        on_whiteout: Optional[OnWhiteoutType] = None,
        on_safari_zone_timeout: Optional[OnSafariZoneTimeoutType] = None,
        on_egg_hatched: Optional[OnEggHatchedType] = None,
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

    def set_on_battle_started(self, callback: Optional[OnBattleStartedType]) -> None:
        self._on_battle_started = callback

    def on_battle_started(self, encounter: "EncounterInfo | None") -> "BattleAction | BattleStrategy | None":
        if self._on_battle_started is not None:
            return self._on_battle_started(encounter)
        else:
            return super().on_battle_started(encounter)

    def set_on_battle_ended(self, callback: Optional[OnBattleEndedType]) -> None:
        self._on_battle_ended = callback

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if self._on_battle_ended is not None:
            return self._on_battle_ended(outcome)
        else:
            return super().on_battle_ended(outcome)

    def set_on_pokemon_evolving_after_battle(self, callback: Optional[OnPokemonEvolvingAfterBattleType]) -> None:
        self._on_pokemon_evolving_after_battle = callback

    def on_pokemon_evolving_after_battle(self, pokemon: "Pokemon", party_index: int) -> bool:
        if self._on_pokemon_evolving_after_battle is not None:
            return self._on_pokemon_evolving_after_battle(pokemon, party_index)
        else:
            return super().on_pokemon_evolving_after_battle(pokemon, party_index)

    def set_on_pickup_threshold_reached(self, callback: Optional[OnPickupThresholdReachedType]) -> None:
        self._on_pickup_threshold_reached = callback

    def on_pickup_threshold_reached(self) -> bool:
        if self._on_pickup_threshold_reached is not None:
            return self._on_pickup_threshold_reached()
        else:
            return super().on_pickup_threshold_reached()

    def set_on_spotted_by_trainer(self, callback: Optional[OnSpottedByTrainerType]) -> None:
        self._on_spotted_by_trainer = callback

    def on_spotted_by_trainer(self) -> None:
        if self._on_spotted_by_trainer is not None:
            return self._on_spotted_by_trainer()
        else:
            return super().on_spotted_by_trainer()

    def set_on_pokenav_call(self, callback: Optional[OnPokenavCallType]) -> None:
        self._on_pokenav_call = callback

    def on_pokenav_call(self) -> None:
        if self._on_pokenav_call is not None:
            return self._on_pokenav_call()
        else:
            return super().on_pokenav_call()

    def set_on_repel_effect_ended(self, callback: Optional[OnRepelEffectEndedType]) -> None:
        self._on_repel_effect_ended = callback

    def on_repel_effect_ended(self) -> None:
        if self._on_repel_effect_ended is not None:
            return self._on_repel_effect_ended()
        else:
            return super().on_repel_effect_ended()

    def set_on_pokemon_fainted_due_to_poison(self, callback: Optional[OnPokemonFaintedDueToPoisonType]) -> None:
        self._on_pokemon_fainted_due_to_poison = callback

    def on_pokemon_fainted_due_to_poison(self, pokemon: "Pokemon", party_index: int) -> None:
        if self._on_pokemon_fainted_due_to_poison is not None:
            return self._on_pokemon_fainted_due_to_poison(pokemon, party_index)
        else:
            return super().on_pokemon_fainted_due_to_poison(pokemon, party_index)

    def set_on_whiteout(self, callback: Optional[OnWhiteoutType]) -> None:
        self._on_whiteout = callback

    def on_whiteout(self) -> bool:
        if self._on_whiteout is not None:
            return self._on_whiteout()
        else:
            return super().on_whiteout()

    def set_on_safari_zone_timeout(self, callback: Optional[OnSafariZoneTimeoutType]) -> None:
        self._on_safari_zone_timeout = callback

    def on_safari_zone_timeout(self) -> bool:
        if self._on_safari_zone_timeout is not None:
            return self._on_safari_zone_timeout()
        else:
            return super().on_safari_zone_timeout()

    def set_on_egg_hatched(self, callback: Optional[OnEggHatchedType]) -> None:
        self._on_egg_hatched = callback

    def on_egg_hatched(self, encounter: "EncounterInfo", party_index: int) -> None:
        if self._on_egg_hatched is not None:
            return self._on_egg_hatched(encounter, party_index)
        else:
            return super().on_egg_hatched(encounter, party_index)

    def run(self) -> Generator:

        yield from self._run
        if context.bot_mode == "Manual" and not self.allow_ending_on_manual_mode:
            raise AssertionError("Bot switched to Manual mode.")


def _set_up_test_emulator(profile: "Profile"):
    from modules.config import Config
    from modules.config.schemas_v1 import Logging, LoggingSavePK3

    from modules.game import set_rom
    from modules.libmgba import LibmgbaEmulator
    from modules.modes import get_bot_listeners

    context.testing = True
    context.config = Config(Path(__file__).parent.parent / "modules" / "config" / "templates")
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

    from modules.profiles import Profile
    from modules.save_import import guess_rom_from_save_state

    with open(state_file, "rb") as handle:
        rom, state_data, save_data = guess_rom_from_save_state(handle, None)
    context.profile = Profile(rom, Path(__file__).parent, datetime.now())
    _set_up_test_emulator(context.profile)
    if save_data is not None:
        context.emulator.load_save_game(save_data)
    context.emulator.load_save_state(state_data)


def _run_test(test_generator: Generator) -> None:

    from modules.memory import get_game_state
    from modules.modes import get_bot_listeners, FrameInfo
    from modules.tasks import get_global_script_context, get_tasks

    previous_frame_info: "FrameInfo | None" = None
    bot_mode = AutomatedTestBotMode(test_generator)
    context.controller_stack.append(bot_mode.run())
    context.bot_mode_instance = bot_mode
    context.stats.logged_encounters.clear()
    context.stats.last_encounter = None
    context._current_bot_mode = AutomatedTestBotMode.name()

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
            controller_stack=[controller.__qualname__ for controller in context.controller_stack],
            previous_frame=previous_frame_info,
        )

        # Reset all bot listeners if the emulator has been reset.
        if previous_frame_info is not None and previous_frame_info.frame_count > frame_info.frame_count:
            context.bot_listeners = get_bot_listeners(context.rom)

        for listener in context.bot_listeners.copy():
            listener.handle_frame(bot_mode, frame_info)
        if len(context.controller_stack) > 0:
            while len(context.controller_stack) > 1 and context.bot_mode == "Manual":
                context.controller_stack.pop()
            try:
                next(context.controller_stack[-1])
            except (StopIteration, GeneratorExit):
                context.controller_stack.pop()
        else:
            break

        context.emulator.run_single_frame()
        previous_frame_info = frame_info
        previous_frame_info.previous_frame = None


def with_save_state(state_file_names: str | list[str]):
    if isinstance(state_file_names, str):
        state_file_names = [state_file_names]

    def decorator(generator_function):
        @wraps(generator_function)
        def wrapper_function(self: BotTestCase, *args, **kwargs):
            for state_file_name in state_file_names:
                with self.subTest(state_file_name=state_file_name):
                    try:
                        state_path = Path(__file__).parent / "states" / state_file_name
                        _load_test_state(state_path)
                        set_next_rng_seed(0xFFFF_FFFF)
                        _run_test(generator_function(self, *args, **kwargs))
                    except BaseException as e:
                        e.add_note(f"State File: {state_file_name}")
                        if context.rom is not None:
                            e.add_note(f"Game: {context.rom.short_game_name}")
                        raise
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
                    screenshot_path = Path(__file__).parent / "last_frame_timeout.png"
                    with open(screenshot_path, "wb") as file:
                        screenshot.save(file, format="PNG")
                    raise AssertionError(f"A timeout of {timeout_in_frames} frames has been reached.")

        return wrapper_function

    return decorator


ask_for_choice_patcher = mock.patch("modules.gui.multi_select_window.ask_for_choice")
mocked_ask_for_choice = ask_for_choice_patcher.start()

wait_for_unique_rng_value_patcher = mock.patch("modules.modes.util.wait_for_unique_rng_value")
mocked_wait_for_unique_rng_value = wait_for_unique_rng_value_patcher.start()

console_patcher = mock.patch("modules.console.console", new=Console(quiet=True))
console_patcher.start()


def set_next_rng_seed(rng_seed: int) -> None:
    from modules.memory import write_symbol, pack_uint32

    rng_value = rng_seed
    write_symbol("gRngValue", pack_uint32(rng_value))

    def simulate_rng():
        nonlocal rng_value
        yield
        write_symbol("gRngValue", pack_uint32(rng_value))
        rng_value = (1103515245 * rng_value + 24691) & 0xFFFF_FFFF

    mocked_wait_for_unique_rng_value.side_effect = simulate_rng


def set_next_choice(next_choice: str) -> None:
    mocked_ask_for_choice.return_value = next_choice


class BotTestCase(unittest.TestCase):
    @property
    def bot_mode(self) -> AutomatedTestBotMode:
        from modules.context import context

        if context.bot_mode == AutomatedTestBotMode.name():
            return context.bot_mode_instance
        else:
            raise RuntimeError(
                f"The bot is currently running in '{context.bot_mode}' mode and not '{AutomatedTestBotMode.name()}'."
            )

    @property
    def stats(self) -> MockStatsDatabase:
        from modules.context import context

        return context.stats

    @property
    def rom(self) -> "ROM":
        from modules.context import context

        return context.rom

    def assertIsInManualMode(self) -> None:
        from modules.context import context

        self.assertEqual(
            "Manual", context.bot_mode, f"Expected bot to be in Manual mode, but it is in {context.bot_mode} mode."
        )

    def assertIsNotInManualMode(self) -> None:
        from modules.context import context

        self.assertEqual(
            context.bot_mode,
            AutomatedTestBotMode.name(),
            f"Expected bot to be in {AutomatedTestBotMode.name()} mode, but it is in {context.bot_mode} mode.",
        )

        self.assertIsInstance(
            context.bot_mode_instance,
            AutomatedTestBotMode,
            f"Bot mode is not an instance of AutomatedTestBotMode but {context.bot_mode_instance.__class__.__name__} instead.",
        )
