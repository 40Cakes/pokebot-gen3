import signal

from modules.data.map import MapRSE, MapFRLG

from modules.battle import BattleOutcome, flee_battle, BattleHandler, check_lead_can_battle, RotatePokemon
from modules.context import context
from modules.encounter import encounter_pokemon
from modules.map import get_map_objects
from modules.memory import get_game_state, GameState, read_symbol, unpack_uint32, get_game_state_symbol
from modules.menuing import MenuWrapper, CheckForPickup, should_check_for_pickup
from modules.player import get_player_avatar, TileTransitionState
from modules.pokemon import (
    get_party,
    get_opponent,
    clear_opponent,
    get_battle_type_flags,
    BattleTypeFlag,
    StatusCondition,
)
from modules.tasks import task_is_active, get_global_script_context
from ._interface import BattleAction, BotMode, FrameInfo, BotListener
from ._util import isolate_inputs


class BattleListener(BotListener):
    battle_states = (GameState.BATTLE, GameState.BATTLE_STARTING, GameState.BATTLE_ENDING)

    def __init__(self):
        self._in_battle = False
        self._reported_end_of_battle = False
        self._current_action: BattleAction | None = None

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not self._in_battle and (frame.game_state in self.battle_states or task_is_active("Task_BattleStart")):
            self._in_battle = True
            self._reported_end_of_battle = False
            action = bot_mode.on_battle_started()
            if action is None:
                opponent = get_opponent()
                battle_type = get_battle_type_flags()

                if BattleTypeFlag.TRAINER in battle_type:
                    if context.config.battle.battle:
                        action = BattleAction.Fight
                    else:
                        context.message = (
                            "We ran into a trainer, but automatic battling is disabled. Switching to manual mode."
                        )
                        context.set_manual_mode()
                else:
                    encounter_pokemon(opponent)
                    if context.bot_mode != "Manual":
                        if context.config.battle.battle:
                            action = BattleAction.Fight
                        else:
                            action = BattleAction.RunAway

            if action == BattleAction.Fight:
                context.controller_stack.append(self.fight())
            elif action == BattleAction.RunAway:
                context.controller_stack.append(self.run_away_from_battle())
            elif action == BattleAction.Catch:
                # todo
                context.message = "Auto catching is not implemented yet."
                context.set_manual_mode()

            self._current_action = action

        elif self._in_battle and get_game_state() not in self.battle_states and not task_is_active("Task_BattleStart"):
            if not self._reported_end_of_battle:
                self._reported_end_of_battle = True
                outcome = BattleOutcome(read_symbol("gBattleOutcome")[0])
                clear_opponent()
                bot_mode.on_battle_ended(outcome)

            if (
                get_game_state_symbol() != "CB2_RETURNTOFIELD"
                and get_game_state_symbol() != "CB2_RETURNTOFIELDLOCAL"
                and not task_is_active("Task_ReturnToFieldNoScript")
                and not task_is_active("Task_ReturnToFieldContinueScriptPlayMapMusic")
                and "heldMovementFinished" in get_map_objects()[0].flags
            ):
                self._in_battle = False

    def _wait_until_battle_is_over(self):
        while self._in_battle:
            context.emulator.press_button("B")
            yield

    @isolate_inputs
    def fight(self):
        yield from BattleHandler().step()
        yield from self._wait_until_battle_is_over()

        if context.config.battle.pickup and should_check_for_pickup():
            context.controller_stack.append(self.check_for_pickup())
        elif context.config.battle.replace_lead_battler and not check_lead_can_battle():
            context.controller_stack.append(self.rotate_lead_pokemon())

    @isolate_inputs
    def run_away_from_battle(self):
        while not get_game_state() == GameState.BATTLE:
            yield
        yield from flee_battle()
        yield from self._wait_until_battle_is_over()

    @isolate_inputs
    def check_for_pickup(self):
        yield from MenuWrapper(CheckForPickup()).step()

    @isolate_inputs
    def rotate_lead_pokemon(self):
        yield from MenuWrapper(RotatePokemon()).step()


class TrainerApproachListener(BotListener):
    def __init__(self):
        self._trainer_is_approaching = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state == GameState.OVERWORLD:
            if not self._trainer_is_approaching and (
                "EventScript_TrainerApproach" in get_global_script_context().stack
                or "EventScript_DoTrainerBattle" in get_global_script_context().stack
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
        if frame.game_state == GameState.OVERWORLD:
            if not self._in_call and task_is_active("ExecuteMatchCall"):
                self._in_call = True
                bot_mode.on_pokenav_call()
                context.controller_stack.append(self.ignore_call())
            elif self._in_call and not task_is_active("ExecuteMatchCall"):
                self._in_call = False

    @isolate_inputs
    def ignore_call(self):
        while task_is_active("ExecuteMatchCall"):
            context.emulator.press_button("B")
            yield


class EggHatchListener(BotListener):
    def __init__(self):
        self._is_hatching = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if frame.game_state == GameState.OVERWORLD or frame.game_state == GameState.EGG_HATCH:
            if not self._is_hatching and "EventScript_EggHatch" in get_global_script_context().stack:
                self._is_hatching = True
                context.controller_stack.append(self.handle_hatching_egg(bot_mode))

    @isolate_inputs
    def handle_hatching_egg(self, bot_mode: BotMode):
        while True:
            egg_data_pointer = unpack_uint32(read_symbol("sEggHatchData"))
            if egg_data_pointer & 0x0200_0000:
                egg_data = context.emulator.read_bytes(egg_data_pointer, length=16)
            else:
                egg_data = b"\x00\x00\x00\x00\x00"
            state = egg_data[2]
            if state < 4:
                context.emulator.press_button("B")
                yield
            else:
                party_index = egg_data[4]
                break
        hatched_pokemon = get_party()[party_index]
        encounter_pokemon(hatched_pokemon)
        bot_mode.on_egg_hatched(hatched_pokemon, party_index)
        while "EventScript_EggHatch" in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        self._is_hatching = False


class RepelListener(BotListener):
    def __init__(self):
        self._message_active = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (
            not self._message_active
            and frame.game_state == GameState.OVERWORLD
            and "EventScript_RepelWoreOff" in get_global_script_context().stack
        ):
            self._message_active = True
            context.controller_stack.append(self.handle_repel_expiration_message(bot_mode))

    @isolate_inputs
    def handle_repel_expiration_message(self, bot_mode: BotMode):
        while "EventScript_RepelWoreOff" in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        self._message_active = False
        bot_mode.on_repel_effect_ended()


class PoisonListener(BotListener):
    def __init__(self):
        self._message_active = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if (
            not self._message_active
            and frame.game_state == GameState.OVERWORLD
            and "EventScript_FieldPoison" in get_global_script_context().stack
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
        while "EventScript_FieldPoison" in get_global_script_context().stack:
            context.emulator.press_button("B")
            yield
        self._message_active = False


class WhiteoutListener(BotListener):
    def __init__(self):
        self._whiteout_active = False

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not self._whiteout_active and (
            frame.game_state == GameState.WHITEOUT
            or (frame.game_state == GameState.OVERWORLD and task_is_active("Task_RushInjuredPokemonToCenter"))
            or "EventScript_FieldWhiteOut" in get_global_script_context().stack
            or "EventScript_FieldWhiteOutNoMoney" in get_global_script_context().stack
            or "EventScript_FieldWhiteOutHasMoney" in get_global_script_context().stack
            or "EventScript_FieldWhiteOutFade" in get_global_script_context().stack
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
            self._local_coordinates_after_leaving = (9, 4)
            self._safari_zone_maps = (
                MapRSE.SAFARI_ZONE.value,
                MapRSE.SAFARI_ZONE_A.value,
                MapRSE.SAFARI_ZONE_B.value,
                MapRSE.SAFARI_ZONE_C.value,
                MapRSE.SAFARI_ZONE_D.value,
                MapRSE.SAFARI_ZONE_E.value,
                MapRSE.SAFARI_ZONE_F.value,
            )
        else:
            self._local_coordinates_after_leaving = (4, 4)
            self._safari_zone_maps = (
                MapFRLG.SAFARI_ZONE.value,
                MapFRLG.SAFARI_ZONE_A.value,
                MapFRLG.SAFARI_ZONE_B.value,
                MapFRLG.SAFARI_ZONE_C.value,
                MapFRLG.SAFARI_ZONE_D.value,
                MapFRLG.SAFARI_ZONE_E.value,
                MapFRLG.SAFARI_ZONE_F.value,
                MapFRLG.SAFARI_ZONE_G.value,
                MapFRLG.SAFARI_ZONE_H.value,
            )

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        if not self._times_up and get_player_avatar().map_group_and_number in self._safari_zone_maps:
            if "SafariZone_EventScript_TimesUp" in get_global_script_context().stack:
                context.controller_stack.append(self.handle_safari_zone_timeout(bot_mode))
                self._times_up = True

    def handle_safari_zone_timeout(self, bot_mode: BotMode):
        context.emulator.reset_held_buttons()
        while (
            get_player_avatar().local_coordinates != self._local_coordinates_after_leaving
            or get_player_avatar().tile_transition_state != TileTransitionState.NOT_MOVING
        ):
            context.emulator.press_button("B")
            yield
        while "heldMovementFinished" not in get_map_objects()[0].flags:
            yield

        custom_handling = bot_mode.on_safari_zone_timeout()
        if not custom_handling:
            context.message = "The player used up all their steps in the Safari Zone. Switched back to manual mode."
            context.set_manual_mode()
        self._times_up = False


class LinuxTimeoutListener(BotListener):
    def __init__(self):
        def raise_timeout_error(*args):
            if not context.gui._emulator_screen._stepping_mode:
                raise TimeoutError

        signal.signal(signal.SIGALRM, raise_timeout_error)

    def handle_frame(self, bot_mode: BotMode, frame: FrameInfo):
        pass
        # signal.alarm(10)
