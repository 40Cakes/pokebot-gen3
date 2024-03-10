import contextlib
from enum import Enum, IntEnum, auto

from modules.context import context
from modules.items import Item, get_item_bag, get_item_by_index, get_item_by_name
from modules.map import get_map_data_for_current_position
from modules.memory import GameState, get_game_state, get_symbol_name, read_symbol, unpack_uint16, unpack_uint32
from modules.menu_parsers import (
    get_battle_cursor,
    get_battle_menu,
    get_learning_move,
    get_learning_move_cursor_pos,
    get_party_menu_cursor_pos,
    switch_requested,
)
from modules.menuing import (
    BaseMenuNavigator,
    BattlePartyMenuNavigator,
    PartyMenuExit,
    PokemonPartyMenuNavigator,
    PokemonPartySubMenuNavigator,
    StartMenuNavigator,
    party_menu_is_open,
)
from modules.modes import BotModeError
from modules.modes.util import scroll_to_item_in_bag
from modules.player import get_player_avatar
from modules.pokedex import get_pokedex
from modules.pokemon import (
    BattleTypeFlag,
    LearnedMove,
    Move,
    Pokemon,
    StatusCondition,
    get_battle_type_flags,
    get_opponent,
    get_party,
    get_type_by_name,
)
from modules.tasks import get_global_script_context, get_task, get_tasks, task_is_active
from modules.tcg_card import generate_tcg_card


class BattleOutcome(Enum):
    Won = 1
    Lost = 2
    Draw = 3
    RanAway = 4
    PlayerTeleported = 5
    OpponentFled = 6
    Caught = 7
    NoSafariBallsLeft = 8
    Forfeited = 9
    OpponentTeleported = 10
    LinkBattleRanAway = 128


class BattleState(IntEnum):
    # out-of-battle states
    OVERWORLD = auto()
    EVOLVING = auto()
    # battle states
    ACTION_SELECTION = auto()
    MOVE_SELECTION = auto()
    PARTY_MENU = auto()
    BAG_MENU = auto()
    SWITCH_POKEMON = auto()
    LEARNING = auto()
    # misc undetected state (move animations, buffering, etc.)
    OTHER = auto()


def flee_battle():
    while get_game_state() == GameState.BATTLE:
        if get_battle_state() == BattleState.ACTION_SELECTION:
            battle_menu = BattleMenu(3)
            yield from battle_menu.step()
        else:
            context.emulator.press_button("B")
            yield


class BattleAction(BaseMenuNavigator):
    """
    Menu navigator object for handling battle actions like fighting, switching, or fleeing.
    """

    def __init__(self, choice: str, idx: int | None):
        super().__init__()
        self.choice = choice
        if idx is None:
            idx = -1
        self.idx = idx
        # Extra info is used to hold additional info for help determining, for example, which bag pocket the desired
        # item is in.
        self.extra_info = ""
        self.choice_was_successful = True
        self.subnavigator = None

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "select_action"
            case "select_action":
                if BattleTypeFlag.SAFARI in get_battle_type_flags():
                    self.current_step = "exit" if self.choice == "catch" else "handle_flee"
                else:
                    match self.choice:
                        case "flee":
                            self.current_step = "handle_flee"
                        case "fight":
                            self.current_step = "choose_move"
                        case "switch":
                            self.current_step = "wait_for_party_menu"
                        case "catch":
                            self.current_step = "wait_for_bag_menu"
                        case "bag":
                            context.message = "Bag not implemented yet, switching to manual mode..."
                            context.set_manual_mode()
            case "wait_for_party_menu":
                self.current_step = "choose_mon"
            case "wait_for_bag_menu":
                self.current_step = "throw_poke_ball"
            case "handle_flee":
                if not self.choice_was_successful:
                    self.current_step = "handle_no_escape"
                else:
                    self.current_step = "return_to_overworld"
            case "choose_move" | "choose_mon" | "throw_poke_ball" | "throw_safari_ball" | "return_to_overworld":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "select_action":
                if BattleTypeFlag.SAFARI in get_battle_type_flags():
                    if self.choice == "catch":
                        self.navigator = self.throw_safari_ball()
                    else:
                        self.navigator = self.select_option(3)
                else:
                    match self.choice:
                        case "fight":
                            index = 0
                        case "switch":
                            index = 2
                        case "catch":
                            index = 1
                        case "bag":
                            index = 1
                            context.message = "Bag not implemented yet, switching to manual mode..."
                            context.set_manual_mode()
                        case "flee" | _:
                            index = 3
                    self.navigator = self.select_option(index)
            case "handle_flee":
                self.navigator = self.handle_flee()
            case "choose_move":
                self.navigator = self.choose_move()
            case "wait_for_party_menu":
                self.navigator = self.wait_for_party_menu()
            case "wait_for_bag_menu":
                self.navigator = self.wait_for_bag_menu()
            case "choose_mon":
                self.navigator = self.choose_mon()
            case "throw_poke_ball":
                self.navigator = self.throw_poke_ball()
            case "throw_safari_ball":
                self.navigator = self.throw_safari_ball()
            case "handle_no_escape":
                self.navigator = self.handle_no_escape()
            case "return_to_overworld":
                self.navigator = self.return_to_overworld()

    def handle_flee(self):
        if self.subnavigator is None:
            self.subnavigator = flee_battle()
        yield from self.subnavigator
        self.subnavigator = None
        self.navigator = None

    def choose_move(self):
        while get_battle_state() == BattleState.MOVE_SELECTION:
            if self.idx < 0 or self.idx > 3:
                context.message = "Invalid move selection, switching to manual mode..."
                context.set_manual_mode()
            elif self.subnavigator is None and get_battle_state() == BattleState.OTHER:
                yield
            elif self.subnavigator is None:
                select_battle_option = SelectBattleOption(self.idx).step()
                self.subnavigator = select_battle_option
                yield
            else:
                yield from self.subnavigator
                self.subnavigator = None
                self.navigator = None
        self.subnavigator = None
        self.navigator = None

    def choose_mon(self):
        while self.navigator is not None:
            if self.subnavigator is None:
                self.subnavigator = BattlePartyMenuNavigator(idx=self.idx, mode="switch").step()
                yield
            else:
                yield from self.subnavigator
                self.navigator = None
                self.subnavigator = None

    @staticmethod
    def _ball_throwing_task_name() -> str:
        if context.rom.is_emerald:
            return "AnimTask_ThrowBall_Step"
        elif context.rom.is_rs:
            return "sub_813FB7C"
        else:
            return "AnimTask_ThrowBall_WaitAnimObjComplete"

    def throw_poke_ball(self):
        yield from scroll_to_item_in_bag(get_item_by_index(self.idx))

        while not task_is_active(self._ball_throwing_task_name()):
            context.emulator.press_button("A")
            yield

        while task_is_active(self._ball_throwing_task_name()):
            context.emulator.press_button("B")
            yield

        yield

    def throw_safari_ball(self):
        while not task_is_active(self._ball_throwing_task_name()):
            context.emulator.press_button("A")
            yield

        while task_is_active(self._ball_throwing_task_name()):
            context.emulator.press_button("B")
            yield

        if task_is_active("sub_81414BC"):
            while task_is_active("sub_81414BC"):
                context.emulator.press_button("B")
                yield

        yield

    def handle_no_escape(self):
        if self.subnavigator is None and not party_menu_is_open():
            while not party_menu_is_open():
                context.emulator.press_button("B")
                yield
        elif party_menu_is_open() and self.subnavigator is None:
            mon_to_switch = get_new_lead()
            if mon_to_switch is None:
                context.message = "Can't find a viable switch-in, switching to manual mode..."
                context.set_manual_mode()
            else:
                self.subnavigator = BattlePartyMenuNavigator(idx=mon_to_switch, mode="switch").step()
        else:
            yield from self.subnavigator

    @staticmethod
    def return_to_overworld():
        while get_game_state() != GameState.OVERWORLD:
            context.emulator.press_button("B")
            yield

    def select_option(self, index):
        while get_battle_state() == BattleState.ACTION_SELECTION:
            if self.subnavigator is None:
                self.subnavigator = SelectBattleOption(index).step()
            else:
                yield from self.subnavigator
                self.subnavigator = None
                self.navigator = None
        self.subnavigator = None
        self.navigator = None

    @staticmethod
    def wait_for_party_menu():
        while get_battle_state() != BattleState.PARTY_MENU:
            yield

    @staticmethod
    def wait_for_bag_menu():
        while get_battle_state() != BattleState.BAG_MENU:
            yield


class BattleMoveLearner(BaseMenuNavigator):
    def __init__(self, mon: Pokemon):
        super().__init__()
        self.move_to_replace = -1
        self.mon = mon

    def get_next_func(self):
        match self.current_step:
            case "None":
                self.current_step = "init_learn_move"
            case "init_learn_move":
                match context.config.battle.new_move:
                    case "stop":
                        context.message = "New move trying to be learned, switching to manual mode..."
                        context.set_manual_mode()
                        self.current_step = "exit"
                    case "cancel":
                        self.current_step = "avoid_learning"
                    case "learn_best":
                        self.current_step = "calculate_best"
                        learning_move = get_learning_move()
                        self.move_to_replace = calculate_new_move_viability(self.mon, learning_move)
            case "calculate_best":
                match self.move_to_replace:
                    case 4:
                        self.current_step = "avoid_learning"
                    case _:
                        self.current_step = "confirm_learn"
            case "confirm_learn":
                self.current_step = "wait_for_move_learn_menu"
            case "wait_for_move_learn_menu":
                self.current_step = "navigate_to_move"
            case "navigate_to_move":
                self.current_step = "confirm_replace"
            case "avoid_learning":
                self.current_step = "wait_for_stop_learning"
            case "wait_for_stop_learning":
                self.current_step = "confirm_no_learn"
            case "confirm_replace":
                self.current_step = "wait_for_next_state"
            case "wait_for_next_state" | "confirm_no_learn":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "confirm_learn":
                self.navigator = self.confirm_learn()
            case "wait_for_move_learn_menu":
                self.navigator = self.wait_for_move_learn_menu()
            case "navigate_to_move":
                self.navigator = self.navigate_move_learn_menu()
            case "confirm_replace":
                self.navigator = self.confirm_replace()
            case "avoid_learning":
                self.navigator = self.avoid_learning()
            case "wait_for_stop_learning":
                self.navigator = self.wait_for_stop_learning()
            case "confirm_no_learn":
                self.navigator = self.confirm_no_learn()
            case "wait_for_next_state":
                self.navigator = self.wait_for_next_state()

    def wait_for_next_state(self):
        for _ in range(300):
            if get_battle_state() == BattleState.LEARNING:
                break
            yield
        while get_battle_state() == BattleState.LEARNING:
            context.emulator.press_button("B")
            yield

    def confirm_learn(self):
        while get_learn_move_state() == "LEARN_YN":
            context.emulator.press_button("A")
            yield
        self.navigator = None

    def confirm_replace(self):
        while get_learn_move_state() == "MOVE_MENU":
            context.emulator.press_button("A")
            yield
        self.navigator = None

    def wait_for_move_learn_menu(self):
        while get_learn_move_state() != "MOVE_MENU":
            yield
        self.navigator = None

    def navigate_move_learn_menu(self):
        while get_learn_move_state() == "MOVE_MENU":
            if get_learning_move_cursor_pos() == self.move_to_replace:
                context.emulator.press_button("A")
                self.navigator = None
                yield
            if get_learning_move_cursor_pos() < self.move_to_replace:
                up_presses = get_learning_move_cursor_pos() + 5 - self.move_to_replace
                down_presses = self.move_to_replace - get_learning_move_cursor_pos()
            else:
                up_presses = get_learning_move_cursor_pos() - self.move_to_replace
                down_presses = self.move_to_replace - get_learning_move_cursor_pos() + 5
            if down_presses > up_presses:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("Down")
            yield

    def avoid_learning(self):
        while get_learn_move_state() == "LEARN_YN":
            context.emulator.press_button("B")
            yield
        self.navigator = None

    def wait_for_stop_learning(self):
        while get_learn_move_state() != "STOP_LEARNING":
            yield
        self.navigator = None

    def confirm_no_learn(self):
        while get_learn_move_state() == "STOP_LEARNING":
            context.emulator.press_button("A")
            yield
        self.navigator = None


class BattleHandler:
    """
    Wrapper for the BattleOpponent class that makes it compatible with the current structure of the main loop.
    """

    def __init__(self, try_to_catch: bool = False):
        self.battler = BattleOpponent(try_to_catch).step()

    def step(self):
        yield from self.battler


class BattleOpponent:
    """
    Function to battle wild Pokémon. This will only battle with the lead Pokémon of the party, and will run if it dies
    or runs out of PP.
    """

    def __init__(self, try_to_catch: bool = False):
        """
        Initializes the battle handler
        """
        self.navigator = None
        self.subnavigator = None
        self.battle_ended = False
        self.opponent = get_opponent()
        self.prev_battle_state = get_battle_state()
        self.party = get_party()
        self.most_recent_leveled_mon_index = -1
        self.battle_state = BattleState.OTHER
        self.current_battler = self.party[0]
        self.num_battlers = read_symbol("gBattlersCount", size=1)[0]
        self.action = None
        self.choice = None
        self.idx = None
        self.battle_action = None
        self.try_to_catch = try_to_catch

    @property
    def foe_fainted(self):
        return self.opponent.current_hp == 0

    def update_battle_state(self):
        """
        Checks the
        """
        self.battle_state = get_battle_state()
        if self.battle_state != self.prev_battle_state:
            self.prev_battle_state = self.battle_state

            # In an effort to reduce bot usage, we will only update the party/current battler/foe HP when the battle
            # state changes. No point checking if the battle state hasn't changed, right?

            # update party
            self.update_party()

            # ensure that the current battler is correct
            self.update_current_battler()

            # Update the foe too
            self.opponent = get_opponent()

    def update_battle_action(self):
        """
        Given the state of the battle, updates the object's action to the proper generator
        """
        match self.battle_state:
            case BattleState.OVERWORLD:
                self.battle_ended = True
                return
            case BattleState.EVOLVING:
                self.action = self.handle_evolution()
            case BattleState.LEARNING:
                self.action = BattleMoveLearner(self.party[self.most_recent_leveled_mon_index]).step()
            case BattleState.ACTION_SELECTION | BattleState.MOVE_SELECTION:
                self.action = self.select_option()
            case BattleState.SWITCH_POKEMON:
                self.action = self.handle_battler_faint()

    def select_option(self):
        while get_battle_state() in [BattleState.ACTION_SELECTION, BattleState.MOVE_SELECTION]:
            while self.choice is None or self.idx is None:
                self.determine_battle_menu_action()
            else:
                if self.choice == "stop":
                    context.message = "Switching to manual mode..."
                    context.set_manual_mode()
                    self.subnavigator = None
                    self.navigator = None
                    self.choice = None
                    self.idx = None
                    self.battle_action = None
                    self.action = None
                    break
                while self.battle_action is None:
                    self.battle_action = BattleAction(choice=self.choice, idx=self.idx).step()
                yield from self.battle_action
                self.choice = None
                self.idx = None
                self.battle_action = None
                self.action = None

    def handle_evolution(self):
        before_party_list: list[Pokemon] = list(get_party())
        while self.battle_state == BattleState.EVOLVING:
            self.update_battle_state()
            if context.config.battle.stop_evolution:
                context.emulator.press_button("B")
            else:
                context.emulator.press_button("A")
            yield
        else:
            for i, party_member in enumerate(get_party()):
                if party_member.is_shiny and party_member != before_party_list[i]:
                    generate_tcg_card(party_member, location=f"Evolved at {get_player_avatar().map_location.map_name}")
                    break
            self.action = None

    def step(self):
        """
        Used to make the battle handler a generator and iterate through the set of instructions for the battle.

        :return: True if the battle was won, False if the battle was lost.
        """
        while not self.battle_ended:
            # check battle state
            self.update_battle_state()

            if self.action is None:
                if self.battle_state == BattleState.OTHER:
                    context.emulator.press_button("B")
                self.update_battle_action()
                yield
            else:
                yield from self.action
                self.action = None

    def determine_battle_menu_action(self):
        """
        Determines which action to select from the action menu

        :return: an ordered pair containing 1, the name of the action to take (fight, switch, flee, etc.) and 2, the
        index of the desired choice.
        """

        # prevent attempting to flee if in trainer battle
        script_ctx = get_global_script_context()
        is_trainer_battle = False
        if "EventScript_DoNoIntroTrainerBattle" in script_ctx.stack:
            is_trainer_battle = True
        if "EventScript_DoTrainerBattle" in script_ctx.stack:
            is_trainer_battle = True

        if not is_trainer_battle and self.try_to_catch:
            self.choose_action_for_auto_catch()
        elif not is_trainer_battle and (
            not context.config.battle.battle or not can_battle_happen() or not should_mon_be_battled(self.opponent)
        ):
            self.choice = "flee"
            self.idx = -1
        elif not check_mon_can_battle(self.current_battler):
            match context.config.battle.lead_cannot_battle_action:
                case "flee":
                    self.choice = "stop" if is_trainer_battle else "flee"
                    self.idx = -1
                case "stop":
                    self.choice = "stop"
                    self.idx = -1
                case "rotate":
                    mon_to_switch = self.get_mon_to_switch()
                    if mon_to_switch is None:
                        self.choice = "flee"
                        self.idx = -1
                        if is_trainer_battle:
                            context.message = "The lead Pokémon is too weak to fight and there is no suitable replacement in your party. Since this is a trainer battle, we also cannot flee. Switching to manual mode."
                            context.set_manual_mode()
                    else:
                        self.choice = "switch"
                        self.idx = mon_to_switch
        else:
            match context.config.battle.battle_method:
                case "strongest":
                    move = self.get_strongest_move()
                    if move == -1:
                        if context.config.battle.lead_cannot_battle_action == "rotate":
                            mon_to_switch = self.get_mon_to_switch()
                            if mon_to_switch is None and not is_trainer_battle:
                                self.choice = "flee"
                                self.idx = -1
                            else:
                                self.choice = "switch"
                                self.idx = mon_to_switch
                        else:
                            self.choice = "flee"
                            self.idx = -1
                    else:
                        self.choice = "fight"
                        self.idx = move
                case _:
                    context.message = "Not yet implemented."
                    self.choice = "flee"
                    self.idx = -1

    def update_party(self):
        """
        Updates the variable Party in the battle handler.

        Especially during battles, the party data in memory is sometimes garbled for
        a bit. If that happens two frames in a row, `get_party()` will throw an error.
        Rather than crashing the bot, we'll just keep working with the last known-good
        state of the party and hope that nothing too important happened in the meantime.
        """
        with contextlib.suppress(RuntimeError):
            party = get_party()
            if party != self.party:
                self.most_recent_leveled_mon_index = check_for_level_up(
                    self.party, party, self.most_recent_leveled_mon_index
                )
                self.party = party

    def update_current_battler(self):
        """
        Determines which Pokémon is battling.
        """
        if BattleTypeFlag.SAFARI in get_battle_type_flags():
            return

        # TODO: someday support double battles maybe idk
        battler_indices = [
            int.from_bytes(read_symbol("gBattlerPartyIndexes", size=12)[2 * i : 2 * i + 2], "little")
            for i in range(self.num_battlers)
        ]
        if len(self.party) == 1:
            self.current_battler = self.party[0]
        self.current_battler = [self.party[battler_indices[i * 2]] for i in range(self.num_battlers // 2)][0]

    def choose_action_for_auto_catch(self) -> None:
        selected_poke_ball = self.get_best_poke_ball_for(self.opponent)
        if selected_poke_ball is None:
            raise BotModeError("Player does not have any Poké Balls, cannot catch.")

        self.choice = "catch"
        self.idx = selected_poke_ball.index

        if (
            BattleTypeFlag.SAFARI not in get_battle_type_flags()
            and self.calculate_catch_chance(self.opponent, selected_poke_ball) < 0.7
            and not self.opponent_might_end_battle_next_turn()
        ):
            # Try to paralyse/put to sleep opponent
            if self.opponent.status_condition == StatusCondition.Healthy:
                status_move_index: int = -1
                status_move_value: float = 0
                for index in range(len(self.current_battler.moves)):
                    learned_move = self.current_battler.moves[index]
                    if learned_move is None or learned_move.pp == 0:
                        continue
                    value = 0
                    if learned_move.move.effect == "SLEEP" and self.opponent.ability.name not in (
                        "Insomnia",
                        "Vital Spirit",
                    ):
                        value = 2 * learned_move.move.accuracy
                    if learned_move.move.effect == "PARALYZE" and self.opponent.ability.name != "Limber":
                        value = 1.5 * learned_move.move.accuracy
                    if status_move_value < value:
                        status_move_index = index
                        status_move_value = value
                if status_move_index >= 0:
                    self.choice = "fight"
                    self.idx = status_move_index

            # False Swipe if possible
            if self.opponent.current_hp > 1:
                false_swipe_index = -1
                for index in range(len(self.current_battler.moves)):
                    learned_move = self.current_battler.moves[index]
                    if learned_move is None:
                        continue
                    if learned_move.move.name == "False Swipe" and learned_move.pp > 0:
                        false_swipe_index = index
                        break
                if false_swipe_index >= 0:
                    self.choice = "fight"
                    self.idx = false_swipe_index

    def opponent_might_end_battle_next_turn(self) -> bool:
        if BattleTypeFlag.ROAMER in get_battle_type_flags():
            return True

        smoke_ball = get_item_by_name("Smoke Ball")
        for move in self.opponent.moves:
            if move is None:
                continue

            match move.move.name:
                case "Selfdestruct" | "Perish Song" | "Explosion" | "Memento":
                    return True

                case "Curse":
                    if self.opponent.current_hp / self.opponent.total_hp <= 0.5:
                        return True

                case "Substitute":
                    if self.opponent.current_hp / self.opponent.total_hp <= 0.25:
                        return True

                case "Teleport":
                    if self.opponent.ability.name == "Run Away" or self.opponent.held_item == smoke_ball:
                        return True

                case "Whirlwind" | "Roar":
                    if self.current_battler.ability.name != "Suction Cups":
                        return True

        return False

    def get_mon_to_switch(self, show_messages=True) -> int | None:
        """
        Figures out which Pokémon should be switched out for the current active Pokémon.

        :param show_messages: Whether to display the message that Pokémon have usable moves or hit points, and whether
        Pokémon seem to be fit to fight.
        :return: the index of the Pokémon to switch with the active Pokémon
        """
        match context.config.battle.switch_strategy:
            case "first_available":
                for i in range(len(self.party)):
                    if self.party[i] == self.current_battler or self.party[i].is_egg:
                        continue
                    # check to see that the party member has enough HP to be subbed out
                    elif mon_has_enough_hp(self.party[i]):
                        if show_messages:
                            context.message = (
                                f"Pokémon {self.party[i].name} has more than {context.config.battle.hp_threshold}% hp!"
                            )
                        for move in self.party[i].moves:
                            if move_is_usable(move):
                                if show_messages:
                                    context.message = f"Pokémon {self.party[i].name} has usable moves!"
                                return i
                if show_messages:
                    context.message = "No Pokémon seem to be fit to fight."

    @staticmethod
    def is_valid_move(move: Move) -> bool:
        return move is not None and move.name not in context.config.battle.banned_moves and move.base_power > 0

    @staticmethod
    def get_move_power(move: LearnedMove, battler: Pokemon, target: Pokemon):
        """
        Calculates the effective power of a move.

        :param move: The move in question
        :param battler: The Pokémon using the move
        :param target: The Pokémon that the move is targeting
        :return: The effective power of the move given the battler and target Pokémon
        """
        power = move.move.base_power

        # Ignore banned moves and moves that have no PP remaining
        if not move_is_usable(move):
            return 0

        for target_type in target.species.types:
            power *= move.move.type.get_effectiveness_against(target_type)

        # Factor in STAB
        if move.move.type in battler.species.types:
            power *= 1.5

        # Determine how each Pokémon's stats affect the damage
        match move.move.type.kind:
            case "Physical":
                stat_calc = battler.stats.attack / target.stats.defence
            case "Special":
                stat_calc = battler.stats.special_attack / target.stats.special_defence
            case _:
                return 0
        return power * stat_calc

    def find_effective_move(self, ally: Pokemon, foe: Pokemon) -> dict:
        """
        Finds the best move for the ally to use on the foe.

        :param ally: The Pokémon being used to battle.
        :param foe: The Pokémon being battled.
        :return: A dictionary containing the name of the move to use, the move's index, and the effective power of the move.
        """
        # calculate power of each possible move
        move_power = [self.get_move_power(move, ally, foe) for move in ally.moves if move is not None]

        # calculate best move and return info
        best_move_index = move_power.index(max(move_power))
        return {
            "name": ally.moves[best_move_index].move.name,
            "index": best_move_index,
            "power": max(move_power),
        }

    def get_strongest_move(self) -> int:
        """
        Function that determines the strongest move to use given the current battler and the current
        """
        if self.num_battlers > 2:
            context.message = "Double battle detected, not yet implemented, switching to manual mode..."
            context.set_manual_mode()
        else:
            current_opponent = get_opponent()
            move = self.find_effective_move(self.current_battler, current_opponent)
            if context.bot_mode == "Nugget Bridge":
                return move["index"]
            if move["power"] == 0:
                context.message = "Lead Pokémon has no effective moves to battle the foe!"
                return -1

            context.message = (
                f"Best move against {current_opponent.name} is {move['name']}, effective power: {move['power']:,.2f}"
            )

            return move["index"]

    def get_best_poke_ball_for(self, opponent: Pokemon) -> Item | None:
        best_poke_ball: Item | None = None
        best_catch_rate_multiplier: float = 0
        for ball in get_item_bag().poke_balls:
            catch_rate_multiplier = self.get_poke_ball_catch_rate_multiplier(opponent, ball.item)

            if best_catch_rate_multiplier < catch_rate_multiplier:
                best_poke_ball = ball.item
                best_catch_rate_multiplier = catch_rate_multiplier

        return best_poke_ball

    @staticmethod
    def get_poke_ball_catch_rate_multiplier(opponent: Pokemon, ball: Item) -> float:
        catch_rate_multiplier = 1
        match ball.index:
            # Master Ball -- we never choose to throw this one, should be the player's choice
            case 1:
                catch_rate_multiplier = -1

            # Ultra Ball
            case 2:
                catch_rate_multiplier = 2

            # Great Ball, Safari Ball:
            case 3 | 5:
                catch_rate_multiplier = 1.5

            # Net Ball
            case 6:
                water = get_type_by_name("Water")
                bug = get_type_by_name("Bug")
                if opponent.species.has_type(water) or opponent.species.has_type(bug):
                    catch_rate_multiplier = 3

            # Dive Ball
            case 7:
                if get_map_data_for_current_position().map_type == "Underwater":
                    catch_rate_multiplier = 3.5

            # Nest Ball
            case 8:
                if opponent.level < 40:
                    catch_rate_multiplier = max(1.0, (40 - opponent.level) / 10)

            # Repeat Ball
            case 9:
                if opponent.species in get_pokedex().owned_species:
                    catch_rate_multiplier = 3

            # Timer Ball
            case 10:
                battle_turn_counter = read_symbol("gBattleResults", offset=0x13, size=1)[0]
                catch_rate_multiplier = (10 + battle_turn_counter) / 10

        return catch_rate_multiplier

    @staticmethod
    def calculate_catch_chance(opponent: Pokemon, ball: Item) -> float:
        catch_rate = max(1, opponent.species.catch_rate)
        catch_rate *= BattleOpponent.get_poke_ball_catch_rate_multiplier(opponent, ball)
        catch_rate *= (3 * opponent.total_hp - 2 * opponent.current_hp) / (3 * opponent.total_hp)
        if opponent.status_condition in (StatusCondition.Sleep, StatusCondition.Freeze):
            catch_rate *= 2
        elif opponent.status_condition in (StatusCondition.Paralysis, StatusCondition.Poison, StatusCondition.Burn):
            catch_rate *= 1.5
        elif opponent.status_condition == StatusCondition.BadPoison and not context.rom.is_rs:
            catch_rate *= 1.5

        if catch_rate > 254:
            return 1

        chance = 16711680 // int(catch_rate)
        chance = int(chance**0.5)
        chance = int(chance**0.5)
        chance = 1048560 // chance
        return ((65535 - chance) / 65535) ** 4

    @property
    def should_rotate_lead(self) -> bool:
        """
        Determines whether the battle engine should swap out the lead Pokémon.
        """
        return mon_has_enough_hp(self.current_battler)

    # TODO
    def handle_battler_faint(self):
        """
        function that handles lead battler fainting
        """
        context.message = "Lead Pokémon fainted!"
        match context.config.battle.faint_action:
            case "stop":
                context.message = "Switching to manual mode..."
                context.set_manual_mode()
            case "flee":
                while get_battle_state() not in [
                    BattleState.OVERWORLD,
                    BattleState.PARTY_MENU,
                ]:
                    context.emulator.press_button("B")
                    yield
                if get_battle_state() == BattleState.PARTY_MENU:
                    context.message = "Couldn't flee, switching to manual mode..."
                    context.set_manual_mode()
                else:
                    while get_game_state() != GameState.OVERWORLD:
                        context.emulator.press_button("B")
                        yield
                    return False
            case "rotate":
                party = get_party()
                if sum(mon.current_hp for mon in party) == 0:
                    context.message = "All Pokémon have fainted, switching to manual mode..."
                    context.set_manual_mode()
                while get_battle_state() != BattleState.PARTY_MENU:
                    context.emulator.press_button("A")
                    yield
                new_lead = self.get_mon_to_switch()
                if new_lead is None:
                    context.message = "No viable pokemon to switch in!"
                    faint_action_default = str(context.config.battle.faint_action)
                    context.config.battle.faint_action = "flee"
                    self.handle_battler_faint()
                    context.config.battle.faint_action = faint_action_default
                    return False
                yield from send_out_pokemon(new_lead)
                while get_battle_state() in (
                    BattleState.SWITCH_POKEMON,
                    BattleState.PARTY_MENU,
                ):
                    context.emulator.press_button("A")
                    yield
            case _:
                context.message = "Invalid faint_action option, switching to manual mode..."
                context.set_manual_mode()


def get_battle_state() -> BattleState:
    """
    Determines the state of the battle so the battle loop can figure out the right choice to make.
    """
    match get_game_state():
        case GameState.OVERWORLD:
            return BattleState.OVERWORLD
        case GameState.EVOLUTION:
            match get_learn_move_state():
                case "LEARN_YN" | "MOVEMENU" | "STOP_LEARNING":
                    return BattleState.LEARNING
                case _:
                    return BattleState.EVOLVING
        case GameState.PARTY_MENU:
            return BattleState.PARTY_MENU
        case GameState.BAG_MENU:
            return BattleState.BAG_MENU
        case _:
            match get_learn_move_state():
                case "LEARN_YN" | "MOVEMENU" | "STOP_LEARNING":
                    return BattleState.LEARNING
                case _:
                    match get_battle_menu():
                        case "ACTION":
                            return BattleState.ACTION_SELECTION
                        case "MOVE":
                            return BattleState.MOVE_SELECTION
                        case _:
                            return BattleState.SWITCH_POKEMON if switch_requested() else BattleState.OTHER


def get_learn_move_state() -> str:
    """
    Determines what step of the move_learning process we're on.
    """
    learn_move_yes_no = False
    stop_learn_move_yes_no = False
    match get_game_state():
        case GameState.BATTLE:
            learn_move_yes_no = (
                get_symbol_name(unpack_uint32(read_symbol("gBattleScriptCurrInstr", size=4)) - 17)
                == "BATTLESCRIPT_ASKTOLEARNMOVE"
            )
            stop_learn_move_yes_no = (
                get_symbol_name(unpack_uint32(read_symbol("gBattleScriptCurrInstr", size=4)) - 32)
                == "BATTLESCRIPT_ASKTOLEARNMOVE"
            )

        case GameState.EVOLUTION:
            task_evolution_scene = get_task("TASK_EVOLUTIONSCENE")
            match context.rom.game_title:
                case "POKEMON RUBY" | "POKEMON SAPP":
                    learn_move_yes_no = (
                        unpack_uint16(task_evolution_scene.data[:2]) == 21
                        and unpack_uint16(task_evolution_scene.data[16:18]) == 4
                        and unpack_uint16(task_evolution_scene.data[18:20]) == 5
                        and unpack_uint16(task_evolution_scene.data[20:22]) == 9
                    )
                    stop_learn_move_yes_no = (
                        unpack_uint16(task_evolution_scene.data[:2]) == 21
                        and unpack_uint16(task_evolution_scene.data[16:18]) == 4
                        and unpack_uint16(task_evolution_scene.data[18:20]) == 10
                        and unpack_uint16(task_evolution_scene.data[20:22]) == 0
                    )
                case "POKEMON EMER":
                    learn_move_yes_no = (
                        unpack_uint16(task_evolution_scene.data[:2]) == 22
                        and unpack_uint16(task_evolution_scene.data[12:14]) in [3, 4]
                        and unpack_uint16(task_evolution_scene.data[14:16]) == 5
                        and unpack_uint16(task_evolution_scene.data[16:18]) == 10
                    )
                    stop_learn_move_yes_no = (
                        unpack_uint16(task_evolution_scene.data[:2]) == 22
                        and unpack_uint16(task_evolution_scene.data[12:14]) in [3, 4]
                        and unpack_uint16(task_evolution_scene.data[14:16]) == 11
                        and unpack_uint16(task_evolution_scene.data[16:18]) == 0
                    )

                case "POKEMON FIRE" | "POKEMON LEAF":
                    learn_move_yes_no = (
                        unpack_uint16(task_evolution_scene.data[:2]) == 24
                        and unpack_uint16(task_evolution_scene.data[12:14]) == 4
                        and unpack_uint16(task_evolution_scene.data[14:16]) == 5
                        and unpack_uint16(task_evolution_scene.data[16:18]) == 10
                    )
                    stop_learn_move_yes_no = (
                        unpack_uint16(task_evolution_scene.data[:2]) == 24
                        and unpack_uint16(task_evolution_scene.data[12:14]) == 4
                        and unpack_uint16(task_evolution_scene.data[14:16]) == 11
                        and unpack_uint16(task_evolution_scene.data[16:18]) == 0
                    )
    match context.rom.game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            move_menu = task_is_active("SUB_809E260")
        case "POKEMON EMER":
            move_menu = task_is_active("TASK_HANDLEREPLACEMOVEINPUT")
        case "POKEMON FIRE" | "POKEMON LEAF":
            move_menu = task_is_active("TASK_INPUTHANDLER_SELECTORFORGETMOVE")
        case _:
            move_menu = False

    if move_menu:
        return "MOVE_MENU"
    elif stop_learn_move_yes_no:
        return "STOP_LEARNING"
    elif learn_move_yes_no:
        return "LEARN_YN"
    else:
        return "NO"


# TODO
def send_out_pokemon(index):
    """
    Navigates from the party menu to the index of the desired Pokémon
    """
    # options are the entire length of the party plus a cancel option
    cursor_positions = len(get_party()) + 1

    # navigate to the desired index as quickly as possible
    party_menu_index = get_party_menu_cursor_pos(cursor_positions - 1)["slot_id"]
    if party_menu_index >= cursor_positions:
        party_menu_index = cursor_positions - 1
    while party_menu_index != index:
        if party_menu_index > index:
            up_presses = party_menu_index - index
            down_presses = index + cursor_positions - party_menu_index
        else:
            up_presses = party_menu_index + cursor_positions - index
            down_presses = index - party_menu_index
        if down_presses > up_presses:
            context.emulator.press_button("Up")
        else:
            context.emulator.press_button("Down")
        party_menu_index = get_party_menu_cursor_pos(cursor_positions - 1)["slot_id"]
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1
        yield

    match context.rom.game_title:
        case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
            for _ in range(60):
                if "TASK_HANDLESELECTIONMENUINPUT" not in [task.symbol for task in get_tasks()]:
                    context.emulator.press_button("A")
                else:
                    break
                yield
            while "TASK_HANDLESELECTIONMENUINPUT" in [task.symbol for task in get_tasks()]:
                yield from PokemonPartySubMenuNavigator("SHIFT").step()
        case _:
            for _ in range(60):
                if "TASK_HANDLEPOPUPMENUINPUT" not in [task.symbol for task in get_tasks()]:
                    context.emulator.press_button("A")
                yield
            while "TASK_HANDLEPOPUPMENUINPUT" in [task.symbol for task in get_tasks()]:
                context.emulator.press_button("A")
                yield


def calculate_new_move_viability(mon: Pokemon, new_move: Move) -> int:
    """
    Function that judges the move a Pokémon is trying to learn against its moveset and returns the index of the worst
    move of the bunch.

    :param mon: The Pokémon that is trying to learn a move
    :param new_move: The move that the mon is trying to learn
    :return: The index of the move to select.
    """

    # exit learning move if new move is banned or has 0 power
    if new_move.base_power == 0 or new_move.name in context.config.battle.banned_moves:
        context.message = f"{new_move.name} has base power of 0, so {mon.name} will skip learning it."
        return 4
    # get the effective power of each move
    move_power = []
    full_moveset = [move.move for move in mon.moves]
    full_moveset.append(new_move)
    for move in full_moveset:
        attack_type = move.type.kind
        match attack_type:
            case "Physical":
                attack_bonus = mon.stats.attack
            case "Special":
                attack_bonus = mon.stats.special_attack
            case _:
                attack_bonus = 0
        power = move.base_power * attack_bonus
        if move.type in mon.species.types:
            power *= 1.5
        if move.name in context.config.battle.banned_moves:
            power = 0
        move_power.append(power)
    # find the weakest move of the bunch
    weakest_move_power = min(move_power)
    weakest_move = move_power.index(weakest_move_power)
    # try and aim for good coverage- it's generally better to have a wide array of move types than 4 moves of the same
    # type
    redundant_type_moves = []
    existing_move_types = {}
    for move in full_moveset:
        if move.base_power == 0:
            continue
        if move.type not in existing_move_types:
            existing_move_types[move.type] = move
        else:
            if not redundant_type_moves:
                redundant_type_moves.append(existing_move_types[move.type])
            redundant_type_moves.append(move)
    if weakest_move_power > 0 and redundant_type_moves:
        redundant_move_power = []
        for move in redundant_type_moves:
            attack_type = move.type.kind
            if attack_type == "Physical":
                attack_bonus = mon.stats.attack
            else:
                attack_bonus = mon.stats.special_attack
            power = move.base_power * attack_bonus
            if move.type in mon.species.types:
                power *= 1.5
            if move.name in context.config.battle.banned_moves:
                power = 0
            redundant_move_power.append(power)
        weakest_move_power = min(redundant_move_power)
        weakest_move = full_moveset.index(redundant_type_moves[redundant_move_power.index(weakest_move_power)])
        context.message = "Opting to replace a move that has a redundant type so as to maximize coverage."
    context.message = (
        f"Move to replace is {full_moveset[weakest_move].name} with a calculated power of {weakest_move_power}"
    )

    return weakest_move


def check_for_level_up(old_party: list[Pokemon], new_party: list[Pokemon], leveled_mon) -> int:
    """
    Compares the previous party state to the most recently gathered party state, and returns the index of the first
    Pokémon whose level is higher in the new party state.

    :param old_party: The previous party state
    :param new_party: The most recent party state
    :param leveled_mon: The index of the Pokémon that was most recently leveled before this call.
    :return: The first index where a Pokémon's level is higher in the new party than the old one.
    """
    if len(old_party) != len(new_party):
        context.message = "Party length has changed. Assuming a pokemon was just caught."
    return next(
        (i for i in range(len(old_party)) if old_party[i].level < new_party[i].level),
        leveled_mon,
    )


def can_battle_happen(check_lead_only: bool = False) -> bool:
    """
    Determines whether the bot can battle with the state of the current party
    :return: True if the party is capable of having a battle, False otherwise
    """
    party = [get_party()[0]] if check_lead_only else get_party()
    return any(check_mon_can_battle(mon) for mon in party)


def should_mon_be_battled(mon: Pokemon) -> bool:
    """
    Determines whether an opponent Pokémon should be battled
    :return: True if the Pokémon should be battled, False otherwise
    """
    return (
        not any(context.config.battle.targeted_pokemon) or mon.species.name in context.config.battle.targeted_pokemon
    ) and (
        not any(context.config.battle.avoided_pokemon) or mon.species.name not in context.config.battle.avoided_pokemon
    )


class BattleMenu:
    def __init__(self, index: int):
        self.index: int = index
        if not 0 <= self.index <= 3:
            print(f"Invalid index of {self.index}")
            return
        self.battle_state = get_battle_state()
        match self.battle_state:
            case BattleState.ACTION_SELECTION:
                self.cursor_type = "gActionSelectionCursor"
            case BattleState.MOVE_SELECTION:
                self.cursor_type = "gMoveSelectionCursor"
            case _:
                print(f"Error getting cursor type. Battle state is {self.battle_state}")
                return

    def step(self):
        if get_battle_cursor(self.cursor_type) != self.index:
            match (get_battle_cursor(self.cursor_type) % 2) - (self.index % 2):
                case -1:
                    context.emulator.press_button("Right")
                case 1:
                    context.emulator.press_button("Left")
            match (get_battle_cursor(self.cursor_type) // 2) - (self.index // 2):
                case -1:
                    context.emulator.press_button("Down")
                case 1:
                    context.emulator.press_button("Up")
        elif get_battle_cursor(self.cursor_type) == self.index:
            if get_battle_state() == self.battle_state:
                context.emulator.press_button("A")
        yield


class SelectBattleOption:
    """
    Takes a desired battle menu option, navigates to it, and presses it.
    """

    def __init__(self, index: int):
        self.index = index
        self.battle_state = get_battle_state()
        match self.battle_state:
            case BattleState.ACTION_SELECTION:
                self.cursor_type = "gActionSelectionCursor"
            case BattleState.MOVE_SELECTION:
                self.cursor_type = "gMoveSelectionCursor"

    def step(self):
        while get_battle_cursor(self.cursor_type) != self.index:
            match (get_battle_cursor(self.cursor_type) % 2) - (self.index % 2):
                case -1:
                    context.emulator.press_button("Right")
                case 1:
                    context.emulator.press_button("Left")
            match (get_battle_cursor(self.cursor_type) // 2) - (self.index // 2):
                case -1:
                    context.emulator.press_button("Down")
                case 1:
                    context.emulator.press_button("Up")
            yield
        while get_battle_cursor(self.cursor_type) == self.index and get_battle_state() == self.battle_state:
            context.emulator.press_button("A")
            yield


# TODO
def execute_menu_action(decision: tuple):
    """
    Given a decision made by the battle engine, executes the desired action.

    :param decision: The output of determine_battle_menu_action, containing an action, move index, and Pokémon index.
    """
    action, move, pokemon = decision
    match action:
        case "RUN":
            flee_battle()
            return
        case "FIGHT":
            if move < 0 or move > 3:
                context.message = "Invalid move selection. Switching to manual mode..."
                context.set_manual_mode()
            else:
                match get_battle_state():
                    case BattleState.ACTION_SELECTION:
                        select_battle_option = SelectBattleOption(0).step()
                        for _ in select_battle_option:
                            yield
                    case BattleState.MOVE_SELECTION:
                        select_battle_option = SelectBattleOption(move).step()
                        for _ in select_battle_option:
                            yield
                    case _:
                        context.emulator.press_button("B")
                yield
        case "BAG":
            context.message = "Bag not yet implemented. Switching to manual mode..."
            context.set_manual_mode()
        case "SWITCH":
            if pokemon is None:
                execute_menu_action(("RUN", -1, -1))
            elif pokemon < 0 or pokemon > 6:
                context.message = "Invalid Pokemon selection. Switching to manual mode..."
                context.set_manual_mode()
            else:
                select_battle_option = SelectBattleOption(2)
                while get_battle_state() != BattleState.PARTY_MENU:
                    yield from select_battle_option.step()
                switcher = send_out_pokemon(pokemon)
                for _ in switcher:
                    yield
            return


def check_lead_can_battle() -> bool:
    """
    Determines whether the lead Pokémon is fit to fight
    """
    if len(get_party()) < 1:
        return False

    lead = get_party()[0]
    return check_mon_can_battle(lead)


def check_mon_can_battle(mon: Pokemon) -> bool:
    """
    Determines whether a Pokémon is fit to fight
    """
    if context.bot_mode == "Nugget Bridge":
        return True

    if mon.is_egg or not mon_has_enough_hp(mon):
        return False

    return any(move_is_usable(move) for move in mon.moves)


def get_new_lead() -> int | None:
    """
    Determines which Pokémon to put at the head of the party

    :return: the index of the Pokémon to put at the head of the party
    """
    party = get_party()
    for i in range(len(party)):
        mon = party[i]
        if mon.is_egg:
            continue
        # check to see that the party member has enough HP to be subbed out
        elif mon_has_enough_hp(mon):
            for move in mon.moves:
                if move_is_usable(move):
                    return i
    return None


def mon_has_enough_hp(mon: Pokemon) -> bool:
    return mon.current_hp / mon.stats.hp > context.config.battle.hp_threshold / 100


def move_is_usable(m: LearnedMove) -> bool:
    return (
        m is not None and m.move.base_power > 0 and m.pp > 0 and m.move.name not in context.config.battle.banned_moves
    )


class RotatePokemon(BaseMenuNavigator):
    def __init__(self):
        super().__init__()
        self.party = get_party()
        self.new_lead = get_new_lead()

    def get_next_func(self):
        match self.current_step:
            case "None":
                match self.new_lead:
                    case None:
                        self.current_step = "exit"
                    case _:
                        self.current_step = "open_party_menu"
            case "open_party_menu":
                self.current_step = "switch_pokemon"
            case "switch_pokemon":
                self.current_step = "confirm_switch"
            case "confirm_switch":
                self.current_step = "exit_to_overworld"
            case "exit_to_overworld":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "open_party_menu":
                self.navigator = StartMenuNavigator("POKEMON").step()
            case "switch_pokemon":
                self.navigator = PokemonPartyMenuNavigator(idx=self.new_lead, mode="switch").step()
            case "switch_pokemon":
                self.navigator = self.confirm_switch()
            case "exit_to_overworld":
                self.navigator = PartyMenuExit().step()

    @staticmethod
    def confirm_switch():
        while task_is_active("TASK_HANDLECHOOSEMONINPUT") or task_is_active("HANDLEPARTYMENUSWITCHPOKEMONINPUT"):
            context.emulator.press_button("A")
            yield
