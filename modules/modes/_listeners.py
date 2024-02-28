import signal

from modules.battle import BattleHandler, BattleOutcome, RotatePokemon, check_lead_can_battle, flee_battle
from modules.context import context
from modules.encounter import handle_encounter
from modules.map import get_map_objects, get_map_data_for_current_position
from modules.map_data import MapFRLG, MapRSE
from modules.memory import GameState, get_game_state, get_game_state_symbol, read_symbol, unpack_uint32
from modules.menuing import CheckForPickup, MenuWrapper, should_check_for_pickup
from modules.player import TileTransitionState, get_player_avatar
from modules.pokemon import (
    BattleTypeFlag,
    StatusCondition,
    clear_opponent,
    get_battle_type_flags,
    get_opponent,
    get_party,
)
from modules.tasks import get_global_script_context, task_is_active
from ._interface import BattleAction, BotListener, BotMode, FrameInfo
from ._util import isolate_inputs


class BattleListener(BotListener):
    battle_states = (GameState.BATTLE, GameState.BATTLE_STARTING, GameState.BATTLE_ENDING)

    def __init__(self):
        self._in_battle = False
        self._reported_start_of_battle = False
        self._reported_end_of_battle = False
        self._current_action: BattleAction | None = None

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (not self._in_battle or self._reported_end_of_battle) and (
            frame.game_state in self.battle_states or frame.task_is_active("Task_BattleStart")
        ):
            self._in_battle = True
            self._reported_start_of_battle = False
            self._reported_end_of_battle = False
            self._current_action = None

        elif self._in_battle and not self._reported_start_of_battle and get_game_state() == GameState.BATTLE:
            self._reported_start_of_battle = True
            action = bot_mode.on_battle_started()
            battle_type = get_battle_type_flags()
            opponent = get_opponent()

            if BattleTypeFlag.DOUBLE in battle_type:
                context.message = "A double battle has started, which is not yet supported by the bot."
                context.set_manual_mode()
                action = BattleAction.CustomAction
            elif BattleTypeFlag.TRAINER in battle_type:
                if (not context.config.battle.battle and action is None) or action == BattleAction.RunAway:
                    context.message = (
                        "We ran into a trainer, but automatic battling is disabled. Switching to manual mode."
                    )
                    context.set_manual_mode()
                    action = BattleAction.CustomAction
                if action is None:
                    action = BattleAction.Fight
            elif action is None:
                action = handle_encounter(opponent)

            if action == BattleAction.Fight:
                context.controller_stack.append(self.fight())
            elif action == BattleAction.RunAway:
                context.controller_stack.append(self.run_away_from_battle())
            elif action == BattleAction.Catch:
                context.controller_stack.append(self.catch())

            self._current_action = action

        elif (
            self._in_battle
            and get_game_state() not in self.battle_states
            and not frame.task_is_active("Task_BattleStart")
            and read_symbol("gBattleOutcome", size=1)[0] != 0
        ):
            outcome = BattleOutcome(read_symbol("gBattleOutcome", size=1)[0])
            if not self._reported_end_of_battle:
                self._reported_end_of_battle = True
                clear_opponent()
                bot_mode.on_battle_ended(outcome)

            if (
                get_game_state_symbol() != "CB2_RETURNTOFIELD"
                and get_game_state_symbol() != "CB2_RETURNTOFIELDLOCAL"
                and "Task_ReturnToFieldNoScript" not in frame.active_tasks
                and "Task_ReturnToFieldContinueScriptPlayMapMusic" not in frame.active_tasks
                and "task_mpl_807E3C8" not in frame.active_tasks
                and len(get_map_objects()) > 0
                and "heldMovementFinished" in get_map_objects()[0].flags
            ):
                self._in_battle = False
                if outcome == BattleOutcome.NoSafariBallsLeft:
                    context.controller_stack.append(
                        SafariZoneListener.handle_safari_zone_timeout_global(bot_mode, "Safari balls")
                    )

    def _wait_until_battle_is_over(self):
        while self._in_battle:
            if get_game_state() != GameState.OVERWORLD or get_map_data_for_current_position().map_type != "Underwater":
                context.emulator.press_button("B")
            yield

    @isolate_inputs
    def fight(self):
        yield from BattleHandler().step()
        yield from self._wait_until_battle_is_over()

        map_objects = get_map_objects()
        if (
            get_game_state() != GameState.BATTLE
            and not get_global_script_context().is_active
            and len(map_objects) > 0
            and "heldMovementActive" in map_objects[0].flags
            and "heldMovementFinished" in map_objects[0].flags
            and "frozen" not in get_map_objects()[0].flags
        ):
            if context.config.battle.pickup and should_check_for_pickup():
                yield from MenuWrapper(CheckForPickup()).step()
            elif context.config.battle.lead_cannot_battle_action == "rotate" and not check_lead_can_battle():
                yield from MenuWrapper(RotatePokemon()).step()

    @isolate_inputs
    def catch(self):
        yield from BattleHandler(try_to_catch=True).step()
        yield from self._wait_until_battle_is_over()

    @isolate_inputs
    def run_away_from_battle(self):
        while get_game_state() != GameState.BATTLE:
            yield
        yield from flee_battle()
        yield from self._wait_until_battle_is_over()


class TrainerApproachListener(BotListener):
    def __init__(self):
        self._trainer_is_approaching = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state == GameState.OVERWORLD and (
            not self._trainer_is_approaching
            and (
                frame.script_is_active("EventScript_TrainerApproach")
                or frame.script_is_active("EventScript_StartTrainerBattle")
                or frame.script_is_active("EventScript_DoTrainerBattle")
            )
        ):
            self._trainer_is_approaching = True
            bot_mode.on_spotted_by_trainer()
            context.controller_stack.append(self.handle_trainer_approach())

    @isolate_inputs
    def handle_trainer_approach(self):
        while get_global_script_context().is_active:
            context.emulator.press_button("B")
            yield
        self._trainer_is_approaching = False


class PokenavListener(BotListener):
    def __init__(self):
        self._in_call = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state == GameState.OVERWORLD and (not self._in_call and frame.task_is_active("ExecuteMatchCall")):
            self._in_call = True
            bot_mode.on_pokenav_call()
            context.controller_stack.append(self.ignore_call())

    @isolate_inputs
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
            context.controller_stack.append(self.handle_hatching_egg(bot_mode))

    @isolate_inputs
    def handle_hatching_egg(self, bot_mode: BotMode):
        while True:
            egg_data = None
            if get_game_state() == GameState.EGG_HATCH:
                yield
                egg_data_pointer = unpack_uint32(read_symbol(self._symbol_name))
                if egg_data_pointer & 0x0200_0000:
                    egg_data = context.emulator.read_bytes(egg_data_pointer, length=16)
            if egg_data is None or egg_data[2] < 4:
                context.emulator.press_button("B")
                yield
            else:
                party_index = egg_data[4]
                break
        hatched_pokemon = get_party()[party_index]
        bot_mode.on_egg_hatched(hatched_pokemon, party_index)
        handle_encounter(hatched_pokemon, do_not_log_battle_action=True)
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
    def handle_repel_expiration_message(self, bot_mode: BotMode):
        while self._script_name in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        self._message_active = False
        bot_mode.on_repel_effect_ended()


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
        while len(get_map_objects()) < 1:
            yield
        while "heldMovementFinished" not in get_map_objects()[0].flags:
            yield

        custom_handling = bot_mode.on_whiteout()
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

    def handle_safari_zone_timeout(self, bot_mode: BotMode, limited_by: str):
        yield from SafariZoneListener.handle_safari_zone_timeout_global(bot_mode, limited_by)
        self._times_up = False

    @staticmethod
    def handle_safari_zone_timeout_global(bot_mode: BotMode, limited_by: str):
        context.emulator.reset_held_buttons()

        local_coordinates_after_leaving = (9, 4) if context.rom.is_rse else (4, 4)
        while (
            get_player_avatar().local_coordinates != local_coordinates_after_leaving
            or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
        ):
            context.emulator.press_button("B")
            yield
        while "heldMovementFinished" not in get_map_objects()[0].flags:
            yield

        custom_handling = bot_mode.on_safari_zone_timeout()
        if not custom_handling:
            context.message = (
                f"The player used up all their {limited_by} in the Safari Zone. Switched back to manual mode."
            )
            context.set_manual_mode()


class LinuxTimeoutListener(BotListener):
    def __init__(self):
        def raise_timeout_error(*args):
            if not context.gui._emulator_screen._stepping_mode:
                raise TimeoutError

        signal.signal(signal.SIGALRM, raise_timeout_error)

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        pass
        # signal.alarm(10)
