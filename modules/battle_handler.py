from typing import Generator, TYPE_CHECKING

from modules.battle_action_selection import handle_battle_action_selection
from modules.battle_evolution_scene import handle_evolution_scene
from modules.battle_move_replacing import handle_move_replacement_dialogue
from modules.battle_state import (
    battle_is_active,
    get_main_battle_callback,
    get_current_battle_script_instruction,
    BattlePokemon,
    get_battle_state,
    get_encounter_type,
    get_last_battle_outcome,
    HandledBattleResult,
)
from modules.battle_strategies import BattleStrategy
from modules.context import context
from modules.debug import debug
from modules.items import Item, get_item_by_index
from modules.keyboard import handle_naming_screen
from modules.memory import get_game_state, GameState, read_symbol, unpack_uint16
from modules.menuing import scroll_to_party_menu_index
from modules.player import get_player
from modules.plugins import plugin_should_nickname_pokemon
from modules.pokemon import StatusCondition
from modules.pokemon_party import get_party, get_party_size, PartyPokemon
from modules.tasks import task_is_active

if TYPE_CHECKING:
    from modules.encounter import EncounterInfo


_last_handled_battle_result: HandledBattleResult | None = None


@debug.track
def handle_battle(strategy: BattleStrategy) -> Generator[None, None, HandledBattleResult]:
    """
    This is the main battle-handling function that will attempt to finish the
    battle, calling the battle strategy's callbacks whenever a decision is
    needed.
    :param strategy: The battle strategy that should be queried each time there
                     is a decision to make.
    :return: A data class structure listing some things that have changed
             during the battle.
    """
    before_cash = get_player().money
    before_party = get_party()
    encounter_type = get_encounter_type()

    stolen_items: list[tuple[int, Item]] = []
    items_before_pickup: list[Item] | None = None

    while battle_is_active() and context.bot_mode != "Manual":
        instruction = get_current_battle_script_instruction()
        if get_main_battle_callback() in ("HandleTurnActionSelectionState", "sub_8012324"):
            yield from handle_battle_action_selection(strategy)
        elif get_current_battle_script_instruction() == "BattleScript_ItemSteal":
            result = yield from handle_item_stealing()
            if result is not None:
                stolen_items.append(result)
        elif (
            get_current_battle_script_instruction() == "BattleScript_PayDayMoneyAndPickUpItems"
            and items_before_pickup is None
        ):
            items_before_pickup = [pokemon.held_item for pokemon in get_party()]
            yield
        elif instruction == "BattleScript_AskToLearnMove":
            yield from handle_move_replacement_dialogue(strategy)
        elif task_is_active("Task_EvolutionScene"):
            yield from handle_evolution_scene(strategy)
        elif (
            (instruction == "BattleScript_HandleFaintedMon" or task_is_active("Task_HandleChooseMonInput"))
            and get_battle_state().own_side.is_fainted
            and len(get_party().non_fainted_pokemon) > 0
        ):
            yield from handle_fainted_pokemon(strategy)
        elif instruction in ("BattleScript_TryNicknameCaughtMon", "BattleScript_CaughtPokemonSkipNewDex"):
            yield from handle_nickname_caught_pokemon(context.stats.last_encounter)
        else:
            context.emulator.press_button("B")
            yield

    outcome = get_last_battle_outcome()
    party_indices_with_picked_up_items = []
    party_indices_that_took_damage_or_changed_status = []
    party_indices_that_gained_exp = []
    party_indices_that_evolved = []

    after_party = get_party()
    for index in range(len(after_party)):
        if len(before_party) <= index:
            break

        before: PartyPokemon = before_party[index]
        after: PartyPokemon = after_party[index]

        if before.current_hp > after.current_hp or (
            before.status_condition is StatusCondition.Healthy and after.status_condition is not StatusCondition.Healthy
        ):
            party_indices_that_took_damage_or_changed_status.append(index)

        if before.total_exp < after.total_exp:
            party_indices_that_gained_exp.append(index)

            if before.species.name != after.species.name:
                party_indices_that_evolved.append(index)

        if items_before_pickup is not None and index < len(items_before_pickup):
            if after.held_item is not items_before_pickup[index]:
                party_indices_with_picked_up_items.append(index)

    party_indices_with_stolen_items = set()
    for party_index, item in stolen_items:
        after: PartyPokemon = after_party[party_index]
        if after.held_item is item:
            party_indices_with_stolen_items.add(party_index)

    result = HandledBattleResult(
        outcome,
        encounter_type,
        get_player().money - before_cash,
        list(party_indices_with_stolen_items),
        party_indices_with_picked_up_items,
        party_indices_that_took_damage_or_changed_status,
        party_indices_that_gained_exp,
        party_indices_that_evolved,
    )

    global _last_handled_battle_result
    _last_handled_battle_result = result

    return result


@debug.track
def handle_item_stealing() -> Generator[None, None, tuple[int, Item] | None]:
    item_index = unpack_uint16(read_symbol("gLastUsedItem"))
    if read_symbol("gBattlerAttacker")[0] == 0:
        stolen_by = get_battle_state().own_side.left_battler.party_index
    elif read_symbol("gBattlerAttacker")[0] == 2:
        stolen_by = get_battle_state().own_side.right_battler.party_index
    else:
        stolen_by = None

    while get_current_battle_script_instruction() == "BattleScript_ItemSteal":
        context.emulator.press_button("B")
        yield

    if stolen_by is not None:
        return stolen_by, get_item_by_index(item_index)


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
                    battle_is_active()
                    and get_current_battle_script_instruction() != "BattleScript_FaintedMonEnd"
                    and get_game_state() != GameState.PARTY_MENU
                    and get_main_battle_callback() != "HandleEndTurn_FinishBattle"
                ):
                    context.emulator.press_button("B")
                    yield

                if battle_is_active() and get_main_battle_callback() == "HandleEndTurn_FinishBattle":
                    while get_main_battle_callback() == "HandleEndTurn_FinishBattle":
                        context.emulator.press_button("B")
                        yield
                    return

    new_lead_index = strategy.choose_new_lead_after_faint(battle_state)

    # If `choose_new_lead_after_faint()` has been called while NOT being in the party selection screen,
    # `get_party()` still contains the 'original' (overworld) party order. Thus, we have to map the new
    # index to the in-battle party index (because that's what we're going to select later) but only after
    # all the sanity checks have been done.
    # On the other hand, if this function was called IN the party menu, `get_party()` already returns the
    # in-battle order and no mapping is needed.
    #
    # In practice, this function will be called OUTSIDE the party menu if the battle strategy chose to
    # send out the next Pokémon (without trying to escape) because then the call happens during the
    # dialogue.
    # Whereas the function will be called IN the party menu if the strategy tried to escape and failed,
    # because then the game automatically opens the party menu.
    index_needs_mapping = get_game_state() != GameState.PARTY_MENU

    if context.bot_mode == "Manual":
        yield
        return

    if new_lead_index < 0 or new_lead_index >= get_party_size():
        raise RuntimeError(f"Cannot send out party index #{new_lead_index} because that does not exist.")

    new_lead = get_party()[new_lead_index]
    if new_lead.is_egg:
        raise RuntimeError(f"Cannot send out party index #{new_lead_index} because it is an egg.")
    if new_lead.current_hp <= 0:
        raise RuntimeError(f"Cannot send out {new_lead.name} (#{new_lead_index}) because it has 0 HP.")

    while (
        battle_is_active()
        and get_current_battle_script_instruction() != "BattleScript_FaintedMonEnd"
        and not task_is_active("Task_HandleChooseMonInput")
        and not task_is_active("HandleBattlePartyMenu")
    ):
        context.emulator.press_button("A")
        yield

    # This will trigger if a battle ends at the same time as the player's Pokémon faints.
    # That happens if the player uses moves like Explosion or Self Destruct, or receives
    # fatal recoil damage during the finishing blow.
    # In this case, the game obviously never asks to choose a new lead and ends the battle
    # instead.
    if get_current_battle_script_instruction() == "BattleScript_FaintedMonEnd":
        return

    if index_needs_mapping:
        new_lead_index = battle_state.map_battle_party_index(new_lead_index)

    yield from scroll_to_party_menu_index(new_lead_index)
    while get_game_state() == GameState.PARTY_MENU:
        context.emulator.press_button("A")
        yield


@debug.track
def handle_nickname_caught_pokemon(encounter: "EncounterInfo"):
    nickname_choice = plugin_should_nickname_pokemon(encounter)
    if nickname_choice:
        yield from handle_naming_screen(nickname_choice)

    # Skip the nicknaming dialogue.
    while get_current_battle_script_instruction() in (
        "BattleScript_TryNicknameCaughtMon",
        "BattleScript_CaughtPokemonSkipNewDex",
    ):
        context.emulator.press_button("B")
        yield


def get_last_handled_battle_result() -> HandledBattleResult | None:
    return _last_handled_battle_result
