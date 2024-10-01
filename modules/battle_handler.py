from typing import Generator

from modules.battle_action_selection import handle_battle_action_selection
from modules.battle_evolution_scene import handle_evolution_scene
from modules.battle_move_replacing import handle_move_replacement_dialogue
from modules.battle_state import (
    get_battle_state,
    battle_is_active,
    get_main_battle_callback,
    get_current_battle_script_instruction,
    BattlePokemon,
    get_battle_state,
    get_battle_controller_callback,
)
from modules.battle_strategies import BattleStrategy
from modules.context import context
from modules.debug import debug
from modules.keyboard import KeyboardNavigator
from modules.memory import get_game_state, GameState
from modules.menuing import scroll_to_party_menu_index
from modules.plugins import plugin_should_nickname_pokemon
from modules.pokemon import get_party, get_opponent
from modules.pokemon_nicknaming import max_pokemon_name_length
from modules.tasks import task_is_active


@debug.track
def handle_battle(strategy: BattleStrategy) -> Generator:
    """
    This is the main battle-handling function that will attempt to finish the
    battle, calling the battle strategy's callbacks whenever a decision is
    needed.
    :param strategy: The battle strategy that should be queried each time there
                     is a decision to make.
    """
    while battle_is_active():
        instruction = get_current_battle_script_instruction()
        if get_main_battle_callback() in ("HandleTurnActionSelectionState", "sub_8012324"):
            yield from handle_battle_action_selection(strategy)
        elif instruction == "BattleScript_AskToLearnMove":
            yield from handle_move_replacement_dialogue(strategy)
        elif task_is_active("Task_EvolutionScene"):
            yield from handle_evolution_scene(strategy)
        elif (
            (instruction == "BattleScript_HandleFaintedMon" or task_is_active("Task_HandleChooseMonInput"))
            and get_battle_state().own_side.is_fainted
            and any(not pokemon.is_egg and pokemon.current_hp > 0 for pokemon in get_party())
        ):
            yield from handle_fainted_pokemon(strategy)
        elif instruction in ("BattleScript_TryNicknameCaughtMon", "BattleScript_CaughtPokemonSkipNewDex"):
            yield from handle_nickname_caught_pokemon()
        else:
            context.emulator.press_button("B")
            yield


@debug.track
def handle_fainted_pokemon(strategy: BattleStrategy):
    fainted_pokemon: BattlePokemon | None = None
    battle_state = get_battle_state()
    if battle_state.own_side.left_battler is None or battle_state.own_side.left_battler.current_hp == 0:
        fainted_pokemon = battle_state.own_side.left_battler
    elif battle_state.is_double_battle and (
        battle_state.own_side.right_battler is None or battle_state.own_side.right_battler.current_hp == 0
    ):
        fainted_pokemon = battle_state.own_side.right_battler

    if fainted_pokemon is None:
        # I can't remember how this could ever happen, but I'll leave this check in here for now.
        context.message = "fainted_pokemon was None"
        context.debug_stepping_mode()
        # context.emulator.press_button("B")
        # for _ in range(180):
        #     yield
        return

    if not battle_state.is_trainer_battle:
        if strategy.should_flee_after_faint(battle_state):
            if context.bot_mode != "Manual":
                while (
                    get_game_state() != GameState.PARTY_MENU
                    and get_main_battle_callback() != "HandleEndTurn_FinishBattle"
                ):
                    context.emulator.press_button("B")
                    yield

                if get_main_battle_callback() == "HandleEndTurn_FinishBattle":
                    while get_main_battle_callback() == "HandleEndTurn_FinishBattle":
                        context.emulator.press_button("B")
                        yield
                    return

    new_lead_index = strategy.choose_new_lead_after_faint(battle_state)
    if context.bot_mode == "Manual":
        yield
        return

    if new_lead_index < 0 or new_lead_index >= len(get_party()):
        raise RuntimeError(f"Cannot send out party index #{new_lead_index} because that does not exist.")

    new_lead = get_party()[new_lead_index]
    if new_lead.is_egg:
        raise RuntimeError(f"Cannot send out party index #{new_lead_index} because it is an egg.")
    if new_lead.current_hp <= 0:
        raise RuntimeError(f"Cannot send out {new_lead.name} (#{new_lead_index}) because it has 0 HP.")

    while not task_is_active("Task_HandleChooseMonInput"):
        context.emulator.press_button("A")
        yield

    yield from scroll_to_party_menu_index(new_lead_index)
    while get_game_state() == GameState.PARTY_MENU:
        context.emulator.press_button("A")
        yield


@debug.track
def handle_nickname_caught_pokemon():
    nickname_choice = plugin_should_nickname_pokemon(get_opponent())
    if nickname_choice:
        while get_game_state() != GameState.NAMING_SCREEN:
            context.emulator.press_button("A")
            yield
        while get_game_state() == GameState.NAMING_SCREEN:
            yield from KeyboardNavigator(name=nickname_choice, max_length=max_pokemon_name_length()).step()
            yield
    else:
        while get_current_battle_script_instruction() in (
            "BattleScript_TryNicknameCaughtMon",
            "BattleScript_CaughtPokemonSkipNewDex",
        ):
            context.emulator.press_button("B")
            yield
