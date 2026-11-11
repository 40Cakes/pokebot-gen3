import os
import random
import sys
import tempfile
import unittest
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Generator, Iterable, Optional, TypeAlias
from unittest import mock

from rich.console import Console

from modules.state_cache import StateCache

sys.path.append(str(Path(__file__).parent.parent))

from modules.modes._interface import BotMode
from modules.context import context

if TYPE_CHECKING:
    from modules.battle_state import BattleOutcome, EncounterType
    from modules.encounter import EncounterInfo
    from modules.fishing import FishingAttempt
    from modules.items import Item
    from modules.modes import FrameInfo, BattleAction
    from modules.pokemon import Pokemon
    from modules.profiles import Profile
    from modules.roms import ROM, ROMLanguage
    from modules.stats import Encounter

# For `assert_encounters()`, as None is a value to check there
NOT_CHECKED = object()


class MockStatsDatabase:
    def __init__(self):
        self.last_fishing_attempt: "FishingAttempt | None" = None
        self.last_encounter: "Encounter | None" = None
        self.encounter_rate = 0
        self.encounter_rate_at_1x = 0
        self.logged_encounters: list["Encounter"] = []
        self.is_first_encounter = False

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

    def log_pokenav_call(self) -> None:
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

    def forward_hooks_to(self, bot_mode: BotMode) -> None:
        """
        Passes all event hooks (`on_battle_started()` etc.) to a real bot mode, as some modes
        rely on them.
        """
        self._on_battle_started = bot_mode.on_battle_started
        self._on_battle_ended = bot_mode.on_battle_ended
        self._on_pokemon_evolving_after_battle = bot_mode.on_pokemon_evolving_after_battle
        self._on_pickup_threshold_reached = bot_mode.on_pickup_threshold_reached
        self._on_spotted_by_trainer = bot_mode.on_spotted_by_trainer
        self._on_pokenav_call = bot_mode.on_pokenav_call
        self._on_repel_effect_ended = bot_mode.on_repel_effect_ended
        self._on_pokemon_fainted_due_to_poison = bot_mode.on_pokemon_fainted_due_to_poison
        self._on_whiteout = bot_mode.on_whiteout
        self._on_safari_zone_timeout = bot_mode.on_safari_zone_timeout
        self._on_egg_hatched = bot_mode.on_egg_hatched

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
    # Don't use the local `profiles/customcatchfilters.py`
    context.custom_catch_filters = lambda pokemon: False
    set_rom(profile.rom)

    def do_nothing():
        pass

    context.emulator = LibmgbaEmulator(context.profile, do_nothing, is_test_run=True)
    context.stats = MockStatsDatabase()
    context.state_cache = StateCache()
    context.bot_listeners = get_bot_listeners(context.rom)
    context.frame = 0
    context.controller_stack.clear()
    context.emulator.set_audio_enabled(False)
    context.emulator.set_video_enabled(False)
    context.emulator.set_throttle(False)
    # Manual mode sets the speed to 1x, keep tests unthrottled
    context.emulator.set_throttle = lambda is_throttled: None


_profile_directory: tempfile.TemporaryDirectory | None = None


def _load_test_state(state_file: Path) -> None:

    from modules.profiles import Profile
    from modules.save_import import guess_rom_from_save_state

    with open(state_file, "rb") as handle:
        rom, state_data, save_data = guess_rom_from_save_state(handle, None)
    # Each state gets an empty profile directory, as some modes write files there
    global _profile_directory
    _profile_directory = tempfile.TemporaryDirectory(prefix="pokebot-test-", ignore_cleanup_errors=True)
    context.profile = Profile(rom, Path(_profile_directory.name), datetime.now())
    _set_up_test_emulator(context.profile)
    if save_data is not None:
        context.emulator.load_save_game(save_data)
    context.emulator.load_save_state(state_data)


def _test_language() -> "ROMLanguage | None":
    """The language set in `POKEBOT_TEST_LANGUAGE` (D, F, I, J, S), to run the English states in."""
    from modules.roms import ROMLanguage

    value = os.environ.get("POKEBOT_TEST_LANGUAGE", "").upper()
    if value in ("", "E"):
        return None
    return ROMLanguage(value)


def _in_language(language: "ROMLanguage", test: Generator) -> Generator:
    """
    Saves in-game, continues that save game in the same game in another language, then runs the test.
    Save games have the same format in all languages, but for a shorter last section in Japanese FR/LG.
    """
    from modules.modes.util import save_the_game
    from modules.roms import ROMLanguage

    rom = rom_in_language(language)

    # The start menu has no 'Save' option in the Safari Zone. Leave Safari mode while saving and
    # restore it afterwards, with the Safari Balls and steps left, which aren't in the save game.
    safari = _leave_safari_mode()
    yield from _with_frame_limit(save_the_game(), 3000, "Saving the game")
    save_game = context.emulator.read_save_data()
    if context.rom.is_frlg and language is ROMLanguage.Japanese:
        save_game = _shorten_frlg_save_block_1(save_game)
    switch_to_rom(rom)
    context.emulator.load_save_game(save_game)
    yield from _with_frame_limit(_continue_save_game(), 3000, "Continuing the save game")
    if safari is not None:
        _restore_safari_mode(*safari)
    set_next_rng_seed(0xFFFF_FFFF)
    yield from test


def _safari_step_counter_symbol() -> str:
    return "sSafariZoneStepCounter" if context.rom.is_emerald else "gSafariZoneStepCounter"


def _leave_safari_mode() -> tuple[bytes, bytes] | None:
    """Clears the Safari mode flag, and returns the Safari Balls and steps left if it was set."""
    from modules.memory import get_event_flag, read_symbol, set_event_flag

    if not get_event_flag("SYS_SAFARI_MODE"):
        return None
    balls, steps = bytes(read_symbol("gNumSafariBalls")), bytes(read_symbol(_safari_step_counter_symbol()))
    set_event_flag("SYS_SAFARI_MODE", False)
    return balls, steps


def _restore_safari_mode(balls: bytes, steps: bytes) -> None:
    from modules.memory import set_event_flag, write_symbol

    set_event_flag("SYS_SAFARI_MODE", True)
    write_symbol("gNumSafariBalls", balls)
    write_symbol(_safari_step_counter_symbol(), steps)


def rom_in_language(language: "ROMLanguage") -> "ROM":
    """The ROM of the current game in another language (the latest revision), or skips the test."""
    from modules.roms import list_available_roms

    game_code = context.rom.game_code[:3]
    roms = [rom for rom in list_available_roms() if rom.game_code[:3] == game_code and rom.language is language]
    if len(roms) == 0:
        raise unittest.SkipTest(f"No {context.rom.game_name} ROM in {language.name} in roms/.")
    return max(roms, key=lambda rom: rom.revision)


def switch_to_rom(rom: "ROM") -> None:
    """Starts an emulator with another ROM, from power on. Can be called while a test runs."""
    from modules.profiles import Profile

    # Setting up an emulator clears the controller stack, which holds the running test
    controller_stack = list(context.controller_stack)
    _set_up_test_emulator(Profile(rom, context.profile.path, datetime.now()))
    context.controller_stack.extend(controller_stack)


def _shorten_frlg_save_block_1(save_game: bytes) -> bytes:
    """
    The last section of Save Block 1 holds 0xEC0 bytes in Japanese FR/LG instead of 0xEE8, so the game
    rejects an English save game. The bytes that don't fit are at the very end (Trainer Tower and
    such), which the tests don't use: cut them and fix the section's checksum.
    """
    from modules.memory import pack_uint16, unpack_uint16, unpack_uint32

    japanese_size = 0xEC0
    save_game = bytearray(save_game)
    for sector_start in range(0, min(len(save_game), 28 * 0x1000), 0x1000):
        if unpack_uint16(save_game[sector_start + 0xFF4 : sector_start + 0xFF6]) != 4:
            continue
        save_game[sector_start + japanese_size : sector_start + 0xF80] = bytes(0xF80 - japanese_size)
        checksum = 0
        for offset in range(sector_start, sector_start + japanese_size, 4):
            checksum = (checksum + unpack_uint32(save_game[offset : offset + 4])) & 0xFFFF_FFFF
        save_game[sector_start + 0xFF6 : sector_start + 0xFF8] = pack_uint16(((checksum >> 16) + checksum) & 0xFFFF)
    return bytes(save_game)


def _with_frame_limit(generator: Generator, frames: int, what: str) -> Generator:
    for frame, _ in enumerate(generator):
        if frame >= frames:
            raise AssertionError(f"{what} took more than {frames} frames.")
        yield


def _continue_save_game() -> Generator:
    """
    Like `soft_reset()`, but FR/LG may not replay the quest log: a save game made in another
    language doesn't, and `soft_reset()` would wait for it forever.
    """
    from modules.memory import GameState, get_game_state, read_symbol
    from modules.modes.util import wait_for_player_avatar_to_be_controllable
    from modules.tasks import task_is_active

    context.emulator.reset()
    yield
    while True:
        match get_game_state():
            case GameState.TITLE_SCREEN | GameState.MAIN_MENU:
                context.emulator.press_button("A")
            case GameState.QUEST_LOG:
                context.emulator.press_button("B")
            case GameState.OVERWORLD:
                if context.rom.is_frlg and read_symbol("gQuestLogState") != b"\x00":
                    context.emulator.press_button("B")
                elif not (context.rom.is_frlg and task_is_active("Task_EndQuestLog")):
                    yield from wait_for_player_avatar_to_be_controllable()
                    return
        yield


# `with_frame_timeout()` only counts the test's own frames, not the ones where the battle handler or another
# listener runs. This limit counts every frame, so that a bot stuck in one of those fails instead of hanging.
FRAME_LIMIT_FACTOR = 5
DEFAULT_FRAME_LIMIT = 500_000


def _run_test(test_generator: Generator, frame_limit: int = DEFAULT_FRAME_LIMIT) -> None:

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

    frames = 0
    while True:
        context.frame += 1
        frames += 1
        if frames > frame_limit:
            stuck_in = [controller.__qualname__ for controller in context.controller_stack]
            raise AssertionError(f"The test ran for more than {frame_limit} frames in all, stuck in {stuck_in}.")

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


def _report_progress(event: str, value: str, test_name: str) -> None:
    """Prints one line per state to stderr if `POKEBOT_TEST_PROGRESS` is set, for tools that follow test runs."""
    if os.environ.get("POKEBOT_TEST_PROGRESS"):
        print(f"[progress] {event} {test_name} {value}", file=sys.__stderr__, flush=True)


def with_save_state(state_file_names: str | list[str]):
    if isinstance(state_file_names, str):
        state_file_names = [state_file_names]

    def decorator(generator_function):
        # Reported when the test file is imported, so that tools know every test's states from the start
        _report_progress("total", str(len(state_file_names)), generator_function.__name__)

        @wraps(generator_function)
        def wrapper_function(self: BotTestCase, *args, **kwargs):
            for state_file_name in state_file_names:
                with self.subTest(state_file_name=state_file_name):
                    _report_progress("start", state_file_name, generator_function.__name__)
                    result = "fail"
                    try:
                        state_path = Path(__file__).parent / "states" / state_file_name
                        _load_test_state(state_path)
                        set_next_rng_seed(0xFFFF_FFFF)
                        mocked_ask_for_choice.side_effect = None
                        mocked_ask_for_choice_scroll.side_effect = None
                        # Some bot code uses `random`, seed it so that runs are reproducible
                        random.seed("/".join(Path(state_file_name).parts[-4:]))
                        test = generator_function(self, *args, **kwargs)
                        language = _test_language()
                        # Master Tests states (absolute paths) are already in their own language
                        if language is not None and not Path(state_file_name).is_absolute():
                            test = _in_language(language, test)
                        timeout = getattr(generator_function, "frame_timeout", None)
                        _run_test(test, int(timeout * FRAME_LIMIT_FACTOR) if timeout else DEFAULT_FRAME_LIMIT)
                        result = "ok"
                    except unittest.SkipTest:
                        result = "skip"
                        raise
                    except BaseException as e:
                        e.add_note(f"State File: {state_file_name}")
                        if context.rom is not None:
                            e.add_note(f"Game: {context.rom.short_game_name}")
                        raise
                    finally:
                        _report_progress(result, state_file_name, generator_function.__name__)
                        if _profile_directory is not None:
                            _profile_directory.cleanup()
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

        # Read by `with_save_state()`, for the limit on all frames
        wrapper_function.frame_timeout = timeout_in_frames
        return wrapper_function

    return decorator


ask_for_choice_patcher = mock.patch("modules.gui.multi_select_window.ask_for_choice")
mocked_ask_for_choice = ask_for_choice_patcher.start()

ask_for_choice_scroll_patcher = mock.patch("modules.gui.multi_select_window.ask_for_choice_scroll")
mocked_ask_for_choice_scroll = ask_for_choice_scroll_patcher.start()

ask_for_confirmation_patcher = mock.patch("modules.gui.multi_select_window.ask_for_confirmation", return_value=True)
mocked_ask_for_confirmation = ask_for_confirmation_patcher.start()

wait_for_unique_rng_value_patcher = mock.patch("modules.modes.util.wait_for_unique_rng_value")
mocked_wait_for_unique_rng_value = wait_for_unique_rng_value_patcher.start()

console_patcher = mock.patch("modules.console.console", new=Console(quiet=True))
console_patcher.start()

desktop_notification_patcher = mock.patch("modules.gui.desktop_notification.desktop_notification")
desktop_notification_patcher.start()


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
    mocked_ask_for_choice.side_effect = None
    mocked_ask_for_choice.return_value = next_choice


def choose_option(*preferred_labels: str) -> None:
    """
    Makes choice windows pick the first option starting with one of `preferred_labels`, or else the
    first option. Useful when the options depend on the save game.
    """

    def choose(choices, *args, **kwargs):
        enabled = [choice.button_label for choice in choices if choice.button_enable]
        for preferred_label in preferred_labels:
            for label in enabled:
                if label.startswith(preferred_label):
                    return label
        return enabled[0] if len(enabled) > 0 else None

    mocked_ask_for_choice.side_effect = choose
    mocked_ask_for_choice_scroll.side_effect = choose


def use_unique_rng_values() -> None:
    """
    Makes `wait_for_unique_rng_value()` give each soft reset a new RNG value, otherwise the same
    Pokémon comes back and repeat encounters are not logged. It advances the RNG and waits a frame,
    so that both frame-based and clock-seeded games get a new value.
    """
    from modules.memory import read_symbol, unpack_uint32
    from modules.modes.util.soft_reset import advance_rng_sequence

    rng_history: set[int] = set()

    def wait_for_unique_rng_value():
        rng_value = unpack_uint32(read_symbol("gRngValue"))
        while rng_value in rng_history:
            advance_rng_sequence()
            yield
            rng_value = unpack_uint32(read_symbol("gRngValue"))
        rng_history.add(rng_value)

    mocked_wait_for_unique_rng_value.side_effect = wait_for_unique_rng_value


def give_key_item(item_name: str, instead_of: str | None = None) -> None:
    """
    Adds a key item to the bag (in memory only). With `instead_of`, it replaces that item, like
    swapping bikes at Rydel's.
    """
    from modules.debug_utilities import debug_write_item_bag
    from modules.items import ItemSlot, get_item_bag, get_item_by_name

    bag = get_item_bag()
    item = get_item_by_name(item_name)
    if bag.quantity_of(item) > 0:
        return

    key_items = list(bag.key_items)
    replaced_index = next(
        (index for index, slot in enumerate(key_items) if instead_of is not None and slot.item.name == instead_of),
        None,
    )
    if replaced_index is not None:
        key_items[replaced_index] = ItemSlot(item, 1)
    else:
        key_items.append(ItemSlot(item, 1))
    debug_write_item_bag(bag.items, key_items, bag.poke_balls, bag.tms_hms, bag.berries)
    # The bag is cached for the current frame
    context.state_cache.reset()


def give_poke_balls(quantity: int, ball_name: str = "Poké Ball") -> None:
    """
    Sets how many of a kind of ball are in the bag (in memory only). Catching isn't certain, so a test
    that must catch something shouldn't depend on a lucky throw.
    """
    from modules.debug_utilities import debug_write_item_bag
    from modules.items import ItemSlot, get_item_bag, get_item_by_name

    bag = get_item_bag()
    ball = get_item_by_name(ball_name)
    poke_balls = [slot for slot in bag.poke_balls if slot.item is not ball] + [ItemSlot(ball, quantity)]
    debug_write_item_bag(bag.items, bag.key_items, poke_balls, bag.tms_hms, bag.berries)
    # The bag is cached for the current frame
    context.state_cache.reset()


def ensure_save_game() -> Generator:
    """
    Saves in-game unless the state already has a save game made facing the same tile. Modes that
    soft reset need it. The player must be in the overworld.
    """
    from modules.memory import GameState, get_game_state
    from modules.modes import BotModeError
    from modules.modes._asserts import SavedMapLocation, assert_saved_on_map
    from modules.modes.util import save_the_game
    from modules.player import get_player_avatar
    from modules.save_data import get_save_data

    in_overworld = get_game_state() is GameState.OVERWORLD
    if get_save_data() is not None:
        if not in_overworld:
            return
        avatar = get_player_avatar()
        targeted_tile = avatar.map_location_in_front
        if targeted_tile is not None:
            try:
                assert_saved_on_map(
                    SavedMapLocation(avatar.map_group_and_number, targeted_tile.local_position, facing=True), ""
                )
                return
            except BotModeError:
                pass
    elif not in_overworld:
        raise AssertionError(f"This state has no save game and can't be saved from here ({get_game_state().name}).")

    yield from save_the_game()


# Directory of the 'Master Tests' states from https://github.com/johnnieb333/Pokebot-Profiles
# (`Drop-In Profiles/Master Tests`). Tests that use them are skipped if it's not set.
MASTER_TESTS_ENVIRONMENT_VARIABLE = "POKEBOT_MASTER_TESTS"

# Optional, only use the states whose path contains this text (like `FRA` or `JPN/Ruby`)
MASTER_TESTS_FILTER_ENVIRONMENT_VARIABLE = "POKEBOT_MASTER_TESTS_FILTER"


def get_master_tests_path() -> Path | None:
    value = os.environ.get(MASTER_TESTS_ENVIRONMENT_VARIABLE)
    if not value:
        return None
    path = Path(value)
    return path if path.is_dir() else None


# Game directory names in the Master Tests
RSE_GAMES = ("Emerald", "Ruby", "Sapphire")
FRLG_GAMES = ("Fire Red", "Leaf Green")


def master_test_states(
    *file_name_patterns: str, exclude: tuple[str, ...] = (), games: tuple[str, ...] | None = None
) -> list[str]:
    """
    :param file_name_patterns: Glob patterns for state file names (they differ between games and languages)
    :param exclude: Glob patterns for state file names to leave out
    :param games: Only use these games (see `RSE_GAMES` and `FRLG_GAMES`)
    :return: Paths of the matching states
    """
    master_tests_path = get_master_tests_path()
    if master_tests_path is None:
        return []

    states = set()
    for pattern in file_name_patterns:
        states.update(master_tests_path.glob(f"*/*/states/{pattern}"))
    for pattern in exclude:
        states.difference_update(master_tests_path.glob(f"*/*/states/{pattern}"))
    if games is not None:
        states = {state for state in states if state.parent.parent.name in games}
    path_filter = os.environ.get(MASTER_TESTS_FILTER_ENVIRONMENT_VARIABLE)
    if path_filter:
        path_filter = path_filter.replace("\\", "/")
        states = {state for state in states if path_filter in state.relative_to(master_tests_path).as_posix()}
    return [str(state) for state in sorted(states)]


def with_master_test_states(
    *file_name_patterns: str, exclude: tuple[str, ...] = (), games: tuple[str, ...] | None = None
):
    """Like `@with_save_state()` for Master Tests states. Skips the test if there are none."""
    states = master_test_states(*file_name_patterns, exclude=exclude, games=games)
    if len(states) == 0:
        return unittest.skip(
            f"No Master Tests state matches {', '.join(file_name_patterns)} "
            f"(set {MASTER_TESTS_ENVIRONMENT_VARIABLE} to the 'Master Tests' directory)"
        )
    return with_save_state(states)


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

    def run_until_encounters(self, mode_class: type[BotMode], number_of_encounters: int = 3) -> Generator:
        """
        Runs a bot mode until it has logged this many encounters. Like the bot's main loop, it starts
        a new instance when `run()` ends, as some modes do one action per run.
        """
        from modules.context import context
        from modules.pokemon import get_opponent

        frames_since_last_encounter = 0
        while len(self.stats.logged_encounters) < number_of_encounters:
            bot_mode = mode_class()
            self.bot_mode.forward_hooks_to(bot_mode)
            frames_in_this_run = 0
            encounters = len(self.stats.logged_encounters)
            for _ in bot_mode.run():
                if len(self.stats.logged_encounters) != encounters:
                    encounters = len(self.stats.logged_encounters)
                    frames_since_last_encounter = 0
                if encounters >= number_of_encounters or context.bot_mode == "Manual":
                    break
                frames_in_this_run += 1
                frames_since_last_encounter += 1
                yield

            if context.bot_mode == "Manual":
                # Stopping right after a shiny is the expected behaviour. A gift or a static encounter has no
                # battle outcome yet when the bot stops for it, which can be a while after it was logged.
                opponent = get_opponent()
                last_encounter = self.stats.last_encounter
                if (opponent is not None and opponent.is_shiny) or (
                    last_encounter
                    and last_encounter.is_shiny
                    and (last_encounter.outcome is None or frames_since_last_encounter < 600)
                ):
                    context.bot_mode_instance.allow_ending_on_manual_mode = True
                    return
                encounters = len(self.stats.logged_encounters)
                self.fail(f"Switched to Manual mode after {encounters} encounter(s): {context.message!r}")
            if frames_in_this_run == 0 and len(self.stats.logged_encounters) < number_of_encounters:
                self.fail(f"The mode stopped after {len(self.stats.logged_encounters)} encounter(s).")
            yield

    def run_mode(
        self,
        mode_class: type[BotMode],
        number_of_encounters: int = 3,
        choices: Iterable[str] = (),
        save_game: bool = False,
    ) -> Generator:
        """
        Runs a bot mode the way most tests need: fails if the mode can't be selected in this state,
        saves in-game first if `save_game` (for modes that soft reset), and picks `choices` in choice
        windows.
        """
        from modules.map_data import get_map_enum
        from modules.player import get_player_avatar

        if not mode_class.is_selectable():
            # Master Tests states are made for one mode: if it can't be selected there, something is wrong (a missing
            # address, for one), and skipping the state would hide it
            self.fail("The mode can't be selected in this state.")
        if save_game:
            yield from ensure_save_game()
        avatar = get_player_avatar()
        self.start_location = (get_map_enum(avatar.map_group_and_number), avatar.local_coordinates)
        use_unique_rng_values()
        choose_option(*choices)
        yield from self.run_until_encounters(mode_class, number_of_encounters)

    def assert_single_species(self) -> None:
        species = {encounter.species_name for encounter in self.stats.logged_encounters}
        self.assertEqual(1, len(species), f"Got different species: {species}")

    def assert_encounters(
        self,
        encounter_type: "EncounterType | Iterable[EncounterType] | None" = None,
        outcome: "BattleOutcome | None" = NOT_CHECKED,
        species: str | Iterable[str] | None = None,
        maps: Iterable | None = None,
        on_start_tile: bool = False,
    ) -> None:
        """
        Checks every logged encounter. `outcome` is checked even when None (no battle outcome, like
        after a soft reset), except for shinies that stopped the bot.
        """
        encounters = self.stats.logged_encounters
        self.assertGreater(len(encounters), 0, "No encounter was logged.")
        types = (
            (encounter_type,)
            if encounter_type is not None and not isinstance(encounter_type, Iterable)
            else encounter_type
        )
        species = (species,) if isinstance(species, str) else species
        for encounter in encounters:
            where = f"{encounter.species_name} on {encounter.map} {encounter.coordinates}"
            if types is not None:
                self.assertIn(encounter.type, tuple(types), where)
            if outcome is not NOT_CHECKED and not encounter.is_shiny:
                self.assertEqual(outcome, encounter.outcome, where)
            if species is not None:
                self.assertIn(encounter.species_name, tuple(species), where)
            if maps is not None:
                self.assertIn(encounter.map, tuple(maps), where)
            if on_start_tile:
                self.assertEqual(self.start_location, (encounter.map, encounter.coordinates), where)

    def assert_player_on_start_tile(self) -> None:
        from modules.map_data import get_map_enum
        from modules.player import get_player_avatar

        avatar = get_player_avatar()
        self.assertEqual(self.start_location, (get_map_enum(avatar.map_group_and_number), avatar.local_coordinates))

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
