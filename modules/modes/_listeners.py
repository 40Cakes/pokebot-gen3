from types import GeneratorType
from typing import Iterable

from modules.context import context
from modules.debug import debug
from modules.encounter import handle_encounter, EncounterInfo, log_encounter
from modules.map import get_map_objects, get_map_data_for_current_position
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_game_state, get_game_state_symbol, read_symbol, unpack_uint32, unpack_uint16
from modules.menuing import CheckForPickup, MenuWrapper, should_check_for_pickup, RotatePokemon
from modules.player import TileTransitionState, get_player_avatar, player_avatar_is_standing_still
from modules.pokemon import StatusCondition, clear_opponent, get_opponent
from modules.pokemon_party import get_party
from modules.tasks import get_global_script_context, task_is_active, get_task
from ._interface import BattleAction, BotListener, BotMode, FrameInfo
from .util import isolate_inputs, save_the_game
from ..battle_handler import handle_battle
from ..battle_state import (
    get_last_battle_outcome,
    BattleOutcome,
    get_encounter_type,
    EncounterType,
    get_battle_state,
    BattleType,
    get_main_battle_callback,
)
from ..battle_strategies import DefaultBattleStrategy, BattleStrategy
from ..battle_strategies.catch import CatchStrategy
from ..battle_strategies.run_away import RunAwayStrategy
from ..fishing import FishingAttempt, FishingRod, FishingResult
from ..plugins import (
    plugin_battle_started,
    plugin_battle_ended,
    plugin_whiteout,
    plugin_egg_hatched,
    plugin_wild_encounter_visible,
    plugin_egg_starting_to_hatch,
)
from ..text_printer import get_text_printer, TextPrinterState


def _ensure_plugin_hook_will_run(generator: Iterable) -> None:
    """
    Executes a plugin hook.

    This will either add the generator to the controller stack (which means it will be
    run for each frame -- which could be used to add delays etc.)

    Or, if the bot is in Manual mode and thus the controller stack would not be executed
    it will unroll the generator loop right here and now.

    :param generator: The generator to be executed.
    """
    if context.bot_mode == "Manual":
        for _ in generator:
            pass
    else:
        context.controller_stack.append(generator)


class BattleListener(BotListener):
    battle_states = (GameState.BATTLE, GameState.BATTLE_STARTING, GameState.BATTLE_ENDING)

    def __init__(self):
        self._in_battle = False
        self._reported_start_of_battle = False
        self._active_wild_encounter: EncounterInfo | None = None
        self._reported_wild_encounter_visible = False
        self._was_starting_to_become_visible = False
        self._reported_end_of_battle = False
        self._current_action: BattleAction | None = None

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (not self._in_battle or self._reported_end_of_battle) and (
            frame.game_state in self.battle_states or frame.task_is_active("Task_BattleStart")
        ):
            self._in_battle = True
            self._reported_start_of_battle = False
            self._active_wild_encounter = None
            self._reported_wild_encounter_visible = False
            self._was_starting_to_become_visible = False
            self._reported_end_of_battle = False
            self._current_action = None

        elif self._in_battle and not self._reported_start_of_battle and get_game_state() == GameState.BATTLE:
            self._reported_start_of_battle = True
            encounter_type = get_encounter_type()
            opponent = get_opponent()

            if encounter_type not in (EncounterType.Trainer, EncounterType.Tutorial):
                if BattleType.FirstBattle in get_battle_state().type:
                    self._active_wild_encounter = EncounterInfo.create(get_party()[0])
                else:
                    self._active_wild_encounter = EncounterInfo.create(opponent)
            else:
                self._active_wild_encounter = None

            action = bot_mode.on_battle_started(self._active_wild_encounter)

            if encounter_type is EncounterType.Trainer and not isinstance(action, BattleStrategy):
                action = BattleAction.Fight
            elif encounter_type is EncounterType.Tutorial:
                action = BattleAction.CustomAction
            elif action is None:
                action = handle_encounter(self._active_wild_encounter)

            if context.bot_mode == "Manual":
                _ensure_plugin_hook_will_run(plugin_battle_started(self._active_wild_encounter))
            elif isinstance(action, BattleStrategy):
                context.controller_stack.append(self.fight(action))
            elif action == BattleAction.Fight:
                context.controller_stack.append(self.fight(DefaultBattleStrategy()))
            elif action == BattleAction.RunAway:
                context.controller_stack.append(self.run_away_from_battle())
            elif action == BattleAction.Catch:
                context.controller_stack.append(self.catch())
            else:
                _ensure_plugin_hook_will_run(plugin_battle_started(self._active_wild_encounter))

            self._current_action = action

        elif (
            self._in_battle
            and get_game_state() not in self.battle_states
            and not frame.task_is_active("Task_BattleStart")
            and get_last_battle_outcome() != BattleOutcome.InProgress
        ):
            outcome = get_last_battle_outcome()
            if not self._reported_end_of_battle:
                self._reported_end_of_battle = True
                clear_opponent()
                bot_mode.on_battle_ended(outcome)
                _ensure_plugin_hook_will_run(plugin_battle_ended(outcome))
                if self._active_wild_encounter is not None:
                    context.stats.log_end_of_battle(outcome, self._active_wild_encounter)

            if (
                get_game_state_symbol() != "CB2_RETURNTOFIELD"
                and get_game_state_symbol() != "CB2_RETURNTOFIELDLOCAL"
                and "Task_ReturnToFieldNoScript" not in frame.active_tasks
                and "Task_ReturnToFieldContinueScriptPlayMapMusic" not in frame.active_tasks
                and "task_mpl_807E3C8" not in frame.active_tasks
                and len(get_map_objects()) > 0
                and player_avatar_is_standing_still()
            ):
                self._in_battle = False
                if outcome == BattleOutcome.NoSafariBallsLeft:
                    context.controller_stack.append(
                        SafariZoneListener.handle_safari_zone_timeout_global(bot_mode, "Safari balls")
                    )

        elif self._active_wild_encounter is not None and not self._reported_wild_encounter_visible:
            if BattleType.FirstBattle not in get_battle_state().type:
                # For regular battle encounter, we want to wait until the 'Wild {SPECIES} appeared!'
                # message and then trigger the `on_wild_encounter_visible()` callbacks as well as do
                # the logging.
                text_printer = get_text_printer()
                is_finally_visible = not text_printer.active or text_printer.state == TextPrinterState.WaitForButton
                is_starting_to_become_visible = text_printer.active
            else:
                # For the first battle on R/S/E we are actually interested in the player's starter
                # Pokémon and not in the opponent. So we need to wait a bit longer until the starter
                # becomes visible, hence the different trigger conditions.
                first_turn_callback = "TryDoEventsBeforeFirstTurn" if context.rom.is_emerald else "BattleBeginFirstTurn"
                main_battle_callback = get_main_battle_callback()
                is_finally_visible = main_battle_callback != first_turn_callback
                is_starting_to_become_visible = get_main_battle_callback() == first_turn_callback

            if self._was_starting_to_become_visible:
                if is_finally_visible:

                    def report_visible():
                        # First, run the `on_wild_encounter_visible()` callbacks -- which might
                        # introduce some delay, so we want to wait for that.
                        yield from plugin_wild_encounter_visible(self._active_wild_encounter)

                        # Then log the encounter.
                        log_encounter(self._active_wild_encounter)

                    _ensure_plugin_hook_will_run(report_visible())
                    self._reported_wild_encounter_visible = True

            elif is_starting_to_become_visible:
                self._was_starting_to_become_visible = True

    @debug.track
    def _wait_until_battle_is_over(self):
        while self._in_battle:
            if get_game_state() != GameState.OVERWORLD or get_map_data_for_current_position().map_type != "Underwater":
                context.emulator.press_button("B")
            yield

    @isolate_inputs
    @debug.track
    def fight(self, strategy: BattleStrategy):
        first_non_fainted_lead_before_battle = get_party().first_non_fainted.index
        yield from plugin_battle_started(self._active_wild_encounter)
        yield from handle_battle(strategy)
        yield from self._wait_until_battle_is_over()

        if (
            get_game_state() != GameState.BATTLE
            and not get_global_script_context().is_active
            and player_avatar_is_standing_still()
        ):
            if (
                should_check_for_pickup()
                and context.bot_mode_instance is not None
                and context.bot_mode_instance.on_pickup_threshold_reached()
            ):
                yield from self.check_for_pickup()
            if strategy.choose_new_lead_after_battle() is not None:
                if context.bot_mode != "Manual":
                    yield from self.rotate_lead_pokemon(
                        strategy.choose_new_lead_after_battle(), first_non_fainted_lead_before_battle
                    )

    @debug.track
    def check_for_pickup(self):
        yield from MenuWrapper(CheckForPickup()).step()

    @debug.track
    def rotate_lead_pokemon(self, new_lead_index: int, old_lead_index: int):
        yield from MenuWrapper(RotatePokemon(new_lead_index, old_lead_index)).step()

    @isolate_inputs
    @debug.track
    def catch(self):
        yield from plugin_battle_started(self._active_wild_encounter)
        yield from handle_battle(CatchStrategy())
        yield from self._wait_until_battle_is_over()
        if context.config.battle.save_after_catching:
            yield from save_the_game()

    @isolate_inputs
    @debug.track
    def run_away_from_battle(self):
        while get_game_state() != GameState.BATTLE:
            yield
        yield from plugin_battle_started(self._active_wild_encounter)
        yield from handle_battle(RunAwayStrategy())
        yield from self._wait_until_battle_is_over()


class TrainerApproachListener(BotListener):
    def __init__(self):
        self._trainer_is_approaching = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state == GameState.OVERWORLD and (
            not self._trainer_is_approaching
            and (
                frame.script_is_active("EventScript_TrainerApproach")
                or frame.script_is_active("EventScript_DoTrainerBattleFromApproach")
                or frame.script_is_active("EventScript_StartTrainerBattle")
                or frame.script_is_active("EventScript_DoTrainerBattle")
            )
        ):
            self._trainer_is_approaching = True
            bot_mode.on_spotted_by_trainer()
            context.controller_stack.append(self.handle_trainer_approach())

    @isolate_inputs
    @debug.track
    def handle_trainer_approach(self):
        while get_global_script_context().is_active:
            context.emulator.press_button("B")
            yield
        self._trainer_is_approaching = False


class FishingListener(BotListener):
    def __init__(self):
        self._is_fishing_task_active = False
        self._last_fishing_rod = None
        self._pokemon_on_hook = False
        self._last_step = None

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not self._is_fishing_task_active and frame.task_is_active("Task_Fishing"):
            fishing_task = get_task("Task_Fishing")
            self._is_fishing_task_active = True
            self._last_fishing_rod = fishing_task.data_value(15)
            self._pokemon_on_hook = False
            self._last_step = fishing_task.data_value(0)
        elif self._is_fishing_task_active:
            if not frame.task_is_active("Task_Fishing"):
                rod = FishingRod(self._last_fishing_rod)
                if self._last_step == 10:
                    attempt = FishingAttempt(rod, FishingResult.Encounter, get_opponent())
                elif self._pokemon_on_hook:
                    attempt = FishingAttempt(rod, FishingResult.GotAway)
                else:
                    attempt = FishingAttempt(rod, FishingResult.Unsuccessful)
                context.stats.log_fishing_attempt(attempt)

                self._last_step = 0
                self._is_fishing_task_active = False
            else:
                step = get_task("Task_Fishing").data_value(0)
                if step != self._last_step:
                    if step == 7:
                        self._pokemon_on_hook = True
                    self._last_step = step


class PokenavListener(BotListener):
    def __init__(self):
        self._in_call = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state == GameState.OVERWORLD and (not self._in_call and frame.task_is_active("ExecuteMatchCall")):
            self._in_call = True
            bot_mode.on_pokenav_call()
            context.controller_stack.append(self.ignore_call())

    @isolate_inputs
    @debug.track
    def ignore_call(self):
        while task_is_active("ExecuteMatchCall") or (
            get_global_script_context().is_active
            and "Route104_EventScript_SailToDewfordDadCalls" not in get_global_script_context().stack
        ):
            context.emulator.press_button("B")
            yield
        self._in_call = False


class EggHatchListener(BotListener):
    def __init__(self):
        self._is_hatching = False
        self._hatching_party_index: int = 0
        self._encounter_info: EncounterInfo | None = None
        self._reported_hatched_egg = False
        if context.rom.is_rs:
            self._script_name = "S_EggHatch"
            self._symbol_name = "gEggHatchData"
        else:
            self._script_name = "EventScript_EggHatch"
            self._symbol_name = "sEggHatchData"

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state in [GameState.OVERWORLD, GameState.EGG_HATCH] and (
            not self._is_hatching and frame.script_is_active(self._script_name)
        ):
            self._is_hatching = True
            self._reported_hatched_egg = False
            self._hatching_party_index = unpack_uint16(read_symbol("gSpecialVar_0x8004"))
            self._encounter_info = EncounterInfo.create(get_party()[self._hatching_party_index], EncounterType.Hatched)
            if context.bot_mode != "Manual":
                context.controller_stack.append(self.handle_hatching_egg())
            else:
                _ensure_plugin_hook_will_run(plugin_egg_starting_to_hatch(self._encounter_info))
        elif self._is_hatching and not frame.script_is_active(self._script_name):
            if not self._reported_hatched_egg and self._encounter_info is not None:
                log_encounter(self._encounter_info)
            self._is_hatching = False
            self._reported_hatched_egg = False
            self._encounter_info = None
        elif self._is_hatching and not self._reported_hatched_egg and frame.script_is_active(self._script_name):
            egg_data_pointer = unpack_uint32(read_symbol(self._symbol_name))
            if egg_data_pointer & 0x0200_0000:
                egg_data = context.emulator.read_bytes(egg_data_pointer, length=16)
                if egg_data[2] >= 6:
                    self._encounter_info.pokemon = get_party()[self._hatching_party_index]
                    bot_mode.on_egg_hatched(self._encounter_info, self._hatching_party_index)

                    def report_hatched():
                        yield from plugin_egg_hatched(self._encounter_info)
                        handle_encounter(self._encounter_info)

                    _ensure_plugin_hook_will_run(report_hatched())
                    self._reported_hatched_egg = True

    @isolate_inputs
    @debug.track
    def handle_hatching_egg(self):
        yield from plugin_egg_starting_to_hatch(self._encounter_info)
        while self._script_name in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        self._is_hatching = False


class RepelListener(BotListener):
    def __init__(self):
        self._message_active = False
        if context.rom.is_rs:
            self._script_name = "S_RepelWoreOff"
        else:
            self._script_name = "EventScript_RepelWoreOff"

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (
            not self._message_active
            and frame.game_state == GameState.OVERWORLD
            and frame.script_is_active(self._script_name)
        ):
            self._message_active = True
            context.controller_stack.append(self.handle_repel_expiration_message(bot_mode))

    @isolate_inputs
    @debug.track
    def handle_repel_expiration_message(self, bot_mode: BotMode):
        previous_inputs = context.emulator.reset_held_buttons()
        while self._script_name in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        context.emulator.restore_held_buttons(previous_inputs)
        self._message_active = False

        mode_callback_result = bot_mode.on_repel_effect_ended()
        if isinstance(mode_callback_result, GeneratorType):
            yield from mode_callback_result


class PoisonListener(BotListener):
    def __init__(self):
        self._message_active = False
        if context.rom.is_rs:
            self._script_name = "gUnknown_081A14B8"
        else:
            self._script_name = "EventScript_FieldPoison"

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (
            not self._message_active
            and frame.game_state == GameState.OVERWORLD
            and frame.script_is_active(self._script_name)
        ):
            self._message_active = True
            party = get_party()
            for index in range(len(party)):
                pokemon = party[index]
                if (
                    pokemon.is_valid
                    and pokemon.current_hp == 0
                    and pokemon.status_condition in (StatusCondition.Poison, StatusCondition.BadPoison)
                ):
                    bot_mode.on_pokemon_fainted_due_to_poison(pokemon, index)
            context.controller_stack.append(self.handle_fainting_message())

    @isolate_inputs
    @debug.track
    def handle_fainting_message(self):
        while self._script_name in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        self._message_active = False


class WhiteoutListener(BotListener):
    def __init__(self):
        self._whiteout_active = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not self._whiteout_active and (
            frame.game_state == GameState.WHITEOUT
            or (frame.game_state == GameState.OVERWORLD and frame.task_is_active("Task_RushInjuredPokemonToCenter"))
            or frame.script_is_active("EventScript_FieldWhiteOut")
            or frame.script_is_active("EventScript_FieldWhiteOutNoMoney")
            or frame.script_is_active("EventScript_FieldWhiteOutHasMoney")
            or frame.script_is_active("EventScript_FieldWhiteOutFade")
            or frame.script_is_active("EventScript_1A14CA")
        ):
            self._whiteout_active = True
            context.controller_stack.append(self.handle_whiteout_dialogue(bot_mode))

    @debug.track
    def handle_whiteout_dialogue(self, bot_mode: BotMode):
        context.emulator.reset_held_buttons()
        while (
            "EventScript_FieldWhiteOut" in get_global_script_context().stack
            or "EventScript_FieldWhiteOutNoMoney" in get_global_script_context().stack
            or "EventScript_FieldWhiteOutHasMoney" in get_global_script_context().stack
            or "EventScript_FieldWhiteOutFade" in get_global_script_context().stack
            or "EventScript_1A14CA" in get_global_script_context().stack
        ):
            context.emulator.press_button("B")
            yield
        while get_game_state() == GameState.WHITEOUT:
            context.emulator.press_button("B")
            yield
        while task_is_active("Task_RushInjuredPokemonToCenter"):
            context.emulator.press_button("B")
            yield
        while "EventScript_AfterWhiteOutHeal" in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        while not player_avatar_is_standing_still():
            yield

        custom_handling = bot_mode.on_whiteout()
        plugin_whiteout()
        if not custom_handling:
            context.message = "Player whited out. Switched back to manual mode."
            context.set_manual_mode()

        self._whiteout_active = False


class SafariZoneListener(BotListener):
    def __init__(self):
        self._times_up = False
        if context.rom.is_rse:
            self._safari_zone_maps = (
                MapRSE.SAFARI_ZONE_NORTHWEST,
                MapRSE.SAFARI_ZONE_NORTH,
                MapRSE.SAFARI_ZONE_SOUTHWEST,
                MapRSE.SAFARI_ZONE_SOUTH,
                MapRSE.SAFARI_ZONE_NORTHEAST,
                MapRSE.SAFARI_ZONE_SOUTHEAST,
                MapRSE.SAFARI_ZONE_REST_HOUSE,
            )
        else:
            self._safari_zone_maps = (
                MapFRLG.SAFARI_ZONE_CENTER,
                MapFRLG.SAFARI_ZONE_EAST,
                MapFRLG.SAFARI_ZONE_NORTH,
                MapFRLG.SAFARI_ZONE_WEST,
                MapFRLG.SAFARI_ZONE_CENTER_REST_HOUSE,
                MapFRLG.SAFARI_ZONE_EAST_REST_HOUSE,
                MapFRLG.SAFARI_ZONE_NORTH_REST_HOUSE,
                MapFRLG.SAFARI_ZONE_WEST_REST_HOUSE,
                MapFRLG.SAFARI_ZONE_SECRET_HOUSE,
            )

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (
            not self._times_up
            and frame.game_state == GameState.OVERWORLD
            and get_player_avatar().map_group_and_number in self._safari_zone_maps
        ):
            if frame.script_is_active("SafariZone_EventScript_TimesUp") or frame.script_is_active("gUnknown_081C3448"):
                context.controller_stack.append(self.handle_safari_zone_timeout(bot_mode, "steps"))
                self._times_up = True
            if frame.script_is_active("SafariZone_EventScript_OutOfBalls") or frame.script_is_active(
                "gUnknown_081C3459"
            ):
                context.controller_stack.append(self.handle_safari_zone_timeout(bot_mode, "Safari balls"))
                self._times_up = True

    @debug.track
    def handle_safari_zone_timeout(self, bot_mode: BotMode, limited_by: str):
        yield from SafariZoneListener.handle_safari_zone_timeout_global(bot_mode, limited_by)
        self._times_up = False

    @staticmethod
    @debug.track
    def handle_safari_zone_timeout_global(bot_mode: BotMode, limited_by: str):
        context.emulator.reset_held_buttons()

        local_coordinates_after_leaving = (9, 4) if context.rom.is_rse else (4, 4)
        while (
            get_player_avatar().local_coordinates != local_coordinates_after_leaving
            or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
        ):
            context.emulator.press_button("B")
            yield
        while not player_avatar_is_standing_still():
            yield

        custom_handling = bot_mode.on_safari_zone_timeout()
        if not custom_handling:
            context.message = (
                f"The player used up all their {limited_by} in the Safari Zone. Switched back to manual mode."
            )
            context.set_manual_mode()
