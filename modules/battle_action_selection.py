from typing import Generator

from modules.battle_menuing import scroll_to_battle_action, scroll_to_move
from modules.battle_state import (
    BattleState,
    get_battle_state,
    battle_is_active,
    get_main_battle_callback,
    get_battle_controller_callback,
)
from modules.battle_strategies import BattleStrategy, TurnAction, SafariTurnAction
from modules.context import context
from modules.debug import debug
from modules.items import Item, ItemBattleUse, get_pokeblocks
from modules.memory import read_symbol, unpack_uint32, get_game_state, GameState, get_game_state_symbol, unpack_uint16
from modules.menuing import scroll_to_item_in_bag, scroll_to_party_menu_index
from modules.pokemon import get_party


@debug.track
def handle_battle_action_selection(strategy: BattleStrategy) -> Generator:
    battle_state = get_battle_state()
    previous_battler_index = None

    while battle_is_active() and get_main_battle_callback() in ("HandleTurnActionSelectionState", "sub_8012324"):
        if get_battle_controller_callback(0) in ("HandleInputChooseAction", "sub_802C098", "bx_battle_menu_t6_2"):
            battler_index = 0
            if battle_state.is_safari_zone_encounter:
                action, index = strategy.decide_turn_in_safari_zone(battle_state)
            elif battle_state.is_double_battle:
                action, index = strategy.decide_turn_in_double_battle(battle_state, 0)
            else:
                action, index = strategy.decide_turn(battle_state)

        elif battle_state.is_double_battle and get_battle_controller_callback(2) in (
            "HandleInputChooseAction",
            "sub_802C098",
        ):
            battler_index = 2
            action, index = strategy.decide_turn_in_double_battle(battle_state, 1)

        elif get_battle_controller_callback(0) in (
            "HandleInputChooseMove",
            "HandleAction_ChooseMove",
        ) or (
            battle_state.is_double_battle
            and get_battle_controller_callback(2) in ("HandleInputChooseMove", "HandleAction_ChooseMove")
        ):
            context.emulator.press_button("B")
            yield
            continue

        else:
            yield
            continue

        if context.bot_mode == "Manual":
            yield
            continue

        # In double battles, both player Pokémon will do their inputs in the same run. So the active
        # battler might change in the middle of this function. If we detect that, we update the battle
        # state as the previous Pokémon's actions might have changed it (e.g. by using potions.)
        if previous_battler_index != battler_index:
            battle_state = get_battle_state()
            previous_battler_index = battler_index

        match action:
            case TurnAction.UseMove | TurnAction.UseMoveAgainstRightSideOpponent | TurnAction.UseMoveAgainstPartner:
                yield from battle_action_use_move(action, battler_index, index, battle_state)

            case TurnAction.UseItem:
                if isinstance(index, tuple):
                    index, target_index = index
                else:
                    target_index = None

                if not isinstance(index, Item):
                    raise RuntimeError(f"`TurnAction.UseItem` needs an item object as its first argument.")
                if index.battle_use == ItemBattleUse.NotUsable:
                    raise RuntimeError(f"Item `{index.name}` cannot be used in battle.")
                if index.battle_use in (ItemBattleUse.Healing, ItemBattleUse.PpRecovery) and target_index is None:
                    raise RuntimeError(f"Item `{index.name}` needs a target Pokémon.")

                yield from battle_action_use_item(index, target_index)

            case TurnAction.RotateLead:
                if index >= len(get_party()):
                    raise RuntimeError(
                        f"Cannot switch in party slot #{index} because the party only has {len(get_party())} Pokémon."
                    )

                if index == battle_state.battling_pokemon[0].party_index or (
                    len(battle_state.battling_pokemon) > 2 and index == battle_state.battling_pokemon[2].party_index
                ):
                    raise RuntimeError(f"Cannot switch in {get_party()[index].name} because it is already in battle.")

                in_battle_index = battle_state.map_battle_party_index(index)

                yield from scroll_to_battle_action(2)
                context.emulator.press_button("A")
                yield from scroll_to_party_menu_index(in_battle_index)
                while get_game_state() == GameState.PARTY_MENU:
                    context.emulator.press_button("A")
                    yield

            case TurnAction.RunAway | SafariTurnAction.RunAway:
                if battle_state.is_trainer_battle:
                    raise RuntimeError("Tried to run away from a trainer battle.")
                yield from scroll_to_battle_action(3)
                context.emulator.press_button("A")
                yield

            case SafariTurnAction.ThrowBall:
                yield from scroll_to_battle_action(0)
                context.emulator.press_button("A")
                yield

            case SafariTurnAction.GoNear:
                if context.rom.is_frlg:
                    raise RuntimeError("The 'Go Near' option is not available in FR/LG Safari battles.")

                yield from scroll_to_battle_action(2)
                context.emulator.press_button("A")
                yield

            case SafariTurnAction.Pokeblock:
                if context.rom.is_frlg:
                    raise RuntimeError("The 'Pokéblock' option is not available in FR/LG Safari battles.")

                yield from battle_action_use_pokeblock(index)

            case SafariTurnAction.Bait:
                if context.rom.is_rse:
                    raise RuntimeError("The 'Bait' option is not available in R/S/E Safari battles.")

                yield from scroll_to_battle_action(1)
                context.emulator.press_button("A")
                yield

            case SafariTurnAction.Rock:
                if context.rom.is_rse:
                    raise RuntimeError("The 'Rock' option is not available in R/S/E Safari battles.")

                yield from scroll_to_battle_action(2)
                context.emulator.press_button("A")
                yield

            case TurnAction.SwitchToManual | SafariTurnAction.SwitchToManual:
                context.set_manual_mode()
                yield

            case _:
                raise RuntimeError(f"Invalid turn action: {action}")


@debug.track
def battle_action_use_item(item: Item, target_index: int = 0):
    yield from scroll_to_battle_action(1)
    context.emulator.press_button("A")
    yield
    yield from scroll_to_item_in_bag(item)
    context.emulator.press_button("A")
    for _ in range(3 if context.rom.is_rse else 5):
        yield
    context.emulator.press_button("A")
    yield
    if target_index is not None:
        yield from scroll_to_party_menu_index(target_index)
        context.emulator.press_button("A")
        yield
        while get_game_state_symbol() != "BATTLEMAINCB2":
            context.emulator.press_button("B")
            yield


@debug.track
def battle_action_use_pokeblock(poke_block_index: int):
    yield from scroll_to_battle_action(1)
    context.emulator.press_button("A")
    while get_game_state_symbol() not in ("CB2_POKEBLOCKMENU", "SUB_810B674"):
        yield
    for _ in range(22):
        yield

    if len(get_pokeblocks()) <= poke_block_index:
        raise RuntimeError(
            f"Cannot use Pokéblock with index '{poke_block_index}' because the Pokéblock Case only contains {len(get_pokeblocks())} blocks."
        )

    def _get_pokeblock_scroll_position() -> int:
        if context.rom.is_rs:
            data = read_symbol("gUnknown_02039248")
            position_offset = data[0]
            scroll_offset = data[1]
        else:
            data = read_symbol("sSavedPokeblockData")
            position_offset = unpack_uint16(data[4:6])
            scroll_offset = unpack_uint16(data[6:8])
        return position_offset + scroll_offset

    while _get_pokeblock_scroll_position() != poke_block_index:
        if _get_pokeblock_scroll_position() < poke_block_index:
            context.emulator.press_button("Down")
        else:
            context.emulator.press_button("Up")
        yield
        yield

    while get_game_state_symbol() in ("CB2_POKEBLOCKMENU", "SUB_810B674"):
        context.emulator.press_button("A")
        yield

    yield
    if context.rom.is_rs:
        while get_battle_controller_callback(0) != "bx_battle_menu_t6_2":
            yield
        yield


@debug.track
def battle_action_use_move(
    action: TurnAction, battler_index: int, move_index: int, battle_state: BattleState
) -> Generator:
    if context.rom.is_rs:
        yield

    # Choose the 'Fight' option.
    if get_battle_controller_callback(battler_index) not in ("HandleInputChooseMove", "HandleAction_ChooseMove"):
        yield from scroll_to_battle_action(0)
        yield
        context.emulator.press_button("A")
    for _ in range(6 if context.rom.is_rse else 7):
        yield

    # It's possible the game does not actually offer the move list at this point, for example
    # if the Pokémon is completely out of PP. In that case we only get a message saying that
    # Struggle is being used. So we just want to confirm that message and then stop the further
    # execution of this function.
    if get_battle_controller_callback(battler_index) not in ("HandleInputChooseMove", "HandleAction_ChooseMove"):
        while get_main_battle_callback() == "HandleTurnActionSelectionState" and get_battle_controller_callback(
            battler_index
        ) not in ("HandleInputChooseMove", "HandleAction_ChooseMove"):
            context.emulator.press_button("A")
            yield
        return

    # Select move and target
    yield from scroll_to_move(move_index, battler_index > 1)
    while get_battle_controller_callback(battler_index) in ("HandleInputChooseMove", "HandleAction_ChooseMove"):
        context.emulator.press_button("A")
        yield
    if action is TurnAction.UseMove:
        target_index = 1
        if battle_state.opponent.left_battler is None:
            raise RuntimeError("Cannot attack the left-side opponent Pokémon because there isn't one.")
    elif action is TurnAction.UseMoveAgainstRightSideOpponent:
        target_index = 3
        if battle_state.opponent.right_battler is None:
            raise RuntimeError("Cannot attack the right-side opponent Pokémon because there isn't one.")
    elif action is TurnAction.UseMoveAgainstPartner:
        target_index = 0 if battler_index == 2 else 2
        if (battler_index == 0 and battle_state.own_side.right_battler is None) or (
            battler_index == 2 and battle_state.own_side.left_battler is None
        ):
            raise RuntimeError("Cannot attack the partnering Pokémon because there isn't one.")
    else:
        target_index = 1
    while get_battle_controller_callback(battler_index) == "HandleInputChooseTarget":
        current_target = unpack_uint32(read_symbol("gMultiUsePlayerCursor"))
        if current_target == target_index:
            context.emulator.press_button("A")
            yield
        else:
            context.emulator.press_button("Down")
            yield
