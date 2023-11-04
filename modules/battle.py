from enum import IntEnum

from modules.config import config
from modules.context import context
from modules.memory import (
    get_game_state,
    read_symbol,
    parse_tasks,
    get_symbol_name,
    get_task,
    unpack_uint16,
    unpack_uint32,
    GameState,
)

from modules.menu_parsers import (
    get_party_menu_cursor_pos,
    parse_start_menu,
    get_battle_menu,
    switch_requested,
    get_learning_move_cursor_pos,
    get_battle_cursor,
    get_learning_move,
)
from modules.menuing import (
    party_menu_is_open,
    switch_pokemon_active,
    BaseMenuNavigator,
    StartMenuNavigator,
    PokemonPartySubMenuNavigator,
    PokemonPartyMenuNavigator,
    BattlePartyMenuNavigator,
)
from modules.pokemon import get_party, get_opponent, Pokemon, Move, LearnedMove


class BattleState(IntEnum):
    # out-of-battle states
    OVERWORLD = 0
    EVOLVING = 1

    # battle states
    ACTION_SELECTION = 10
    MOVE_SELECTION = 11
    PARTY_MENU = 12
    SWITCH_POKEMON = 13
    LEARNING = 14

    # misc undetected state (move animations, buffering, etc.)
    OTHER = 20


class EncounterPokemon:
    def __init__(self):
        self.battle_can_happen = can_battle_happen()
        self.battle = None

    def step(self):
        while True:
            match get_game_state():
                case GameState.BATTLE.value | GameState.BATTLE_STARTING.value | GameState.PARTY_MENU.value:
                    if config["battle"]["battle"] and self.battle_can_happen:
                        if self.battle is None:
                            self.battle = BattleOpponent()
                        while not self.battle.battle_ended:
                            yield from self.battle.step()
                        if config["battle"]["replace_lead_battler"] and not check_lead_can_battle():
                            lead_switcher = RotatePokemon()
                            for _ in lead_switcher:
                                yield _
                    else:
                        for _ in flee_battle():
                            yield _

                case GameState.GARBAGE_COLLECTION:
                    yield

        # TODO
        # if config['battle']['battle'] and battle_can_happen:
        #    battle_won = BattleOpponent()
        #    # adding this in for lead rotation functionality down the line
        #    replace_battler = not battle_won
        # if config['battle']['battle'] and battle_can_happen:
        #    replace_battler = replace_battler or not CheckLeadCanBattle()
        #    if config['battle']["replace_lead_battler"] and replace_battler:
        #        RotatePokemon()
        # if config['battle']["pickup"] and battle_can_happen:
        #    while get_game_state() != GameState.OVERWORLD and not config['general']['bot_mode'] == 'manual':
        #        continue
        #    if get_game_state() == GameState.OVERWORLD:
        #        CheckForPickup(stats['totals'].get('encounters', 0))


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
                match self.choice:
                    case "flee":
                        self.current_step = "handle_flee"
                    case "fight":
                        self.current_step = "choose_move"
                    case "switch":
                        self.current_step = "wait_for_party_menu"
                    case "bag":
                        context.message = "Bag not implemented yet. Switching to manual mode."
                        context.bot_mode = "Manual"
            case "wait_for_party_menu":
                self.current_step = "choose_mon"
            case "handle_flee":
                if not self.choice_was_successful:
                    self.current_step = "handle_no_escape"
                else:
                    self.current_step = "return_to_overworld"
            case "choose_move" | "choose_mon" | "return_to_overworld":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "select_action":
                match self.choice:
                    case "fight":
                        index = 0
                    case "switch":
                        index = 2
                    case "bag":
                        index = 1
                        context.message = "Bag not implemented yet. Switching to manual mode."
                        context.bot_mode = "Manual"
                    case "flee" | _:
                        index = 3
                self.navigator = self.select_option(index)
            case "handle_flee":
                self.navigator = self.handle_flee()
            case "choose_move":
                self.navigator = self.choose_move()
            case "wait_for_party_menu":
                self.navigator = self.wait_for_party_menu()
            case "choose_mon":
                self.navigator = self.choose_mon()
            case "handle_no_escape":
                self.navigator = self.handle_no_escape()
            case "return_to_overworld":
                self.navigator = self.return_to_overworld()

    def handle_flee(self):
        if self.subnavigator is None:
            self.subnavigator = flee_battle()
        for _ in self.subnavigator:
            yield _
        self.subnavigator = None
        self.navigator = None

    def choose_move(self):
        while get_battle_state() == BattleState.MOVE_SELECTION:
            if 0 > self.idx or self.idx > 3:
                context.message = "Invalid move selection. Switching to manual mode..."
                context.bot_mode = "Manual"
            else:
                if self.subnavigator is None and get_battle_state() == BattleState.OTHER:
                    yield
                elif self.subnavigator is None:
                    select_battle_option = SelectBattleOption(self.idx).step()
                    self.subnavigator = select_battle_option
                    yield
                else:
                    for _ in self.subnavigator:
                        yield _
                    self.subnavigator = None
                    self.navigator = None
        else:
            self.subnavigator = None
            self.navigator = None

    def choose_mon(self):
        while True:
            if self.subnavigator is None:
                self.subnavigator = BattlePartyMenuNavigator(idx=self.idx, mode="switch").step()
                yield
            else:
                for _ in self.subnavigator:
                    yield _
                self.navigator = None
                self.subnavigator = None

    def handle_no_escape(self):
        if self.subnavigator is None and not party_menu_is_open():
            while not party_menu_is_open():
                context.emulator.press_button("B")
                yield
        elif party_menu_is_open() and self.subnavigator is None:
            mon_to_switch = get_new_lead()
            if mon_to_switch is None:
                context.message = "Can't find a viable switch-in. Switching to manual mode."
                context.bot_mode = "Manual"
            else:
                self.subnavigator = PokemonPartyMenuNavigator(idx=mon_to_switch, mode="switch").step()
        else:
            yield from self.subnavigator

    @staticmethod
    def return_to_overworld():
        while not get_game_state() == GameState.OVERWORLD:
            context.emulator.press_button("B")
            yield

    def select_option(self, index):
        while get_battle_state() == BattleState.ACTION_SELECTION:
            if self.subnavigator is None:
                self.subnavigator = SelectBattleOption(index).step()
            else:
                for _ in self.subnavigator:
                    yield _
                self.subnavigator = None
                self.navigator = None
        else:
            self.subnavigator = None
            self.navigator = None

    @staticmethod
    def wait_for_party_menu():
        while get_battle_state() != BattleState.PARTY_MENU:
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
                match config["battle"]["new_move"]:
                    case "stop":
                        context.message = "New move trying to be learned, switching to manual mode..."
                        context.bot_mode = "Manual"
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
            case "avoid_learning":
                self.current_step = "wait_for_stop_learning"
            case "wait_for_stop_learning":
                self.current_step = "confirm_no_learn"
            case "navigate_to_move" | "confirm_no_learn":
                self.current_step = "exit"

    def update_navigator(self):
        match self.current_step:
            case "confirm_learn":
                self.navigator = self.confirm_learn()
            case "wait_for_move_learn_menu":
                self.navigator = self.wait_for_move_learn_menu()
            case "navigate_to_move":
                self.navigator = self.navigate_move_learn_menu()
            case "avoid_learning":
                self.navigator = self.avoid_learning()
            case "wait_for_stop_learning":
                self.navigator = self.wait_for_stop_learning()
            case "confirm_no_learn":
                self.navigator = self.confirm_no_learn()

    def confirm_learn(self):
        while get_learn_move_state() == "LEARN_YN":
            context.emulator.press_button("A")
            yield
        else:
            self.navigator = None

    def wait_for_move_learn_menu(self):
        while not get_learn_move_state() == "MOVE_MENU":
            yield
        else:
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
        else:
            self.navigator = None

    def wait_for_stop_learning(self):
        while get_learn_move_state() != "STOP_LEARNING":
            yield
        else:
            self.navigator = None

    def confirm_no_learn(self):
        while get_learn_move_state() == "STOP_LEARNING":
            context.emulator.press_button("A")
            yield
        else:
            self.navigator = None

class BattleHandler:
    """
    Wrapper for the BattleOpponent class that makes it compatible with the current structure of the main loop.
    """
    def __init__(self):
        self.battler = BattleOpponent().step()

    def step(self):
        for _ in self.battler:
            yield _


class BattleOpponent:
    """
    Function to battle wild Pokémon. This will only battle with the lead Pokémon of the party, and will run if it dies
    or runs out of PP.
    """

    def __init__(self):
        """
        Initializes the battle handler
        """
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
        while self.choice is None or self.idx is None:
            self.determine_battle_menu_action()
        else:
            while self.battle_action is None:
                self.battle_action = BattleAction(choice=self.choice, idx=self.idx).step()
            else:
                for _ in self.battle_action:
                    yield _
                self.choice = None
                self.idx = None
                self.battle_action = None
                self.action = None

    def handle_evolution(self):
        while self.battle_state == BattleState.EVOLVING:
            self.update_battle_state()
            if config["battle"]["stop_evolution"]:
                context.emulator.press_button("B")
                yield
            else:
                context.emulator.press_button("A")
                yield
        else:
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
                for _ in self.action:
                    yield _
                self.action = None

    def determine_battle_menu_action(self):
        """
        Determines which action to select from the action menu

        :return: an ordered pair containing A) the name of the action to take (fight, switch, flee, etc.) and B) the
        index of the desired choice.
        """
        if not config["battle"]["battle"] or not can_battle_happen():
            self.choice = "flee"
            self.idx = -1
        elif config["battle"]["replace_lead_battler"] and self.should_rotate_lead:
            mon_to_switch = self.get_mon_to_switch()
            if mon_to_switch is None:
                self.choice = "flee"
                self.idx = -1
            else:
                self.choice = "switch"
                self.idx = mon_to_switch
        else:
            match config["battle"]["battle_method"]:
                case "strongest":
                    move = self.get_strongest_move()
                    if move == -1:
                        if config["battle"]["replace_lead_battler"]:
                            mon_to_switch = self.get_mon_to_switch()
                            if mon_to_switch is None:
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
                    context.message = "Not yet implemented"
                    self.choice = "flee"
                    self.idx = -1

    def update_party(self):
        """
        Updates the variable Party in the battle handler.
        """
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
        # TODO: someday support double battles maybe idk
        battler_indices = [
            int.from_bytes(read_symbol("gBattlerPartyIndexes", size=12)[2 * i: 2 * i + 2], "little")
            for i in range(self.num_battlers)
        ]
        if len(self.party) == 1:
            self.current_battler = self.party[0]
        self.current_battler = [self.party[battler_indices[i * 2]] for i in range(self.num_battlers // 2)][0]

    def get_mon_to_switch(self, show_messages=True) -> int | None:
        """
        Figures out which Pokémon should be switched out for the current active Pokémon.

        :param show_messages: Whether to display the message that Pokémon have usable moves or hit points, and whether
        Pokémon seem to be fit to fight.
        :return: the index of the Pokémon to switch with the active Pokémon
        """
        match config["battle"]["switch_strategy"]:
            case "first_available":
                for i in range(len(self.party)):
                    if self.party[i] == self.current_battler or self.party[i].is_egg:
                        continue
                    # check to see that the party member has enough HP to be subbed out
                    elif mon_has_enough_hp(self.party[i]):
                        if show_messages:
                            context.message = f"Pokémon {self.party[i].name} has more than 20% hp!"
                        for move in self.party[i].moves:
                            if move_is_usable(move):
                                if show_messages:
                                    context.message = f"Pokémon {self.party[i].name} has usable moves!"
                                return i
                if show_messages:
                    context.message = "No Pokémon seem to be fit to fight."

    @staticmethod
    def is_valid_move(move: Move) -> bool:
        return (
                move.name not in config["battle"]["banned_moves"]
                and move.base_power > 0
        )

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
        move_power = [self.get_move_power(move, ally, foe) for move in ally.moves]

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
            context.message = "Double battle detected, not yet implemented. Switching to manual mode..."
            context.bot_mode = "Manual"
        else:
            current_opponent = get_opponent()
            move = self.find_effective_move(self.current_battler, current_opponent)
            if move["power"] == 0:
                context.message = "Lead Pokémon has no effective moves to battle the foe!"
                return -1

            context.message = f"Best move against {current_opponent.name} is {move['name']}, effective power: {move['power']:.2f}"

            return move["index"]

    @property
    def should_rotate_lead(self) -> bool:
        """
        Determines whether the battle engine should swap out the lead Pokémon.
        """
        battler_health_percentage = self.current_battler.current_hp / self.current_battler.stats.hp
        return battler_health_percentage < 0.2

    # TODO
    def handle_battler_faint(self):
        """
        function that handles lead battler fainting
        """
        context.message = "Lead Pokémon fainted!"
        match config["battle"]["faint_action"]:
            case "stop":
                context.message = "Switching to manual mode..."
                context.bot_mode = "Manual"
            case "flee":
                while get_battle_state() not in [BattleState.OVERWORLD, BattleState.PARTY_MENU]:
                    context.emulator.press_button("B")
                    yield
                if get_battle_state() == BattleState.PARTY_MENU:
                    context.message = "Couldn't flee. Switching to manual mode..."
                    context.bot_mode = "Manual"
                else:
                    while not get_game_state() == GameState.OVERWORLD:
                        context.emulator.press_button("B")
                        yield
                    return False
            case "rotate":
                party = get_party()
                if sum([mon.current_hp for mon in party]) == 0:
                    context.message = "All Pokémon have fainted. Switching to manual mode..."
                    context.bot_mode = "Manual"
                while get_battle_state() != BattleState.PARTY_MENU:
                    context.emulator.press_button("A")
                    yield
                new_lead = self.get_mon_to_switch()
                if new_lead is None:
                    context.message = "No viable pokemon to switch in!"
                    faint_action_default = str(config["battle"]["faint_action"])
                    config["battle"]["faint_action"] = "flee"
                    self.handle_battler_faint()
                    config["battle"]["faint_action"] = faint_action_default
                    return False
                switcher = send_out_pokemon(new_lead)
                for i in switcher:
                    yield i
                while get_battle_state() in (BattleState.SWITCH_POKEMON, BattleState.PARTY_MENU):
                    context.emulator.press_button("A")
                    yield
            case _:
                context.message = "Invalid faint_action option. Switching to manual mode..."
                context.bot_mode = "Manual"


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
                            if switch_requested():
                                return BattleState.SWITCH_POKEMON
                            else:
                                return BattleState.OTHER


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
            match context.rom.game_title:
                case "POKEMON RUBY" | "POKEMON SAPP":
                    learn_move_yes_no = (
                            unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][0:2]) == 21
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][16:18]) == 4
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][18:20]) == 5
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][20:22]) == 9
                    )
                    stop_learn_move_yes_no = (
                            unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][0:2]) == 21
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][16:18]) == 4
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][18:20]) == 10
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][20:22]) == 0
                    )
                case "POKEMON EMER":
                    learn_move_yes_no = (
                            unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][0:2]) == 22
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][12:14]) in [3, 4]
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][14:16]) == 5
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][16:18]) == 10
                    )
                    stop_learn_move_yes_no = (
                            unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][0:2]) == 22
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][12:14]) == [3, 4]
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][14:16]) == 11
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][16:18]) == 0
                    )

                case "POKEMON FIRE" | "POKEMON LEAF":
                    learn_move_yes_no = (
                            unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][0:2]) == 24
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][12:14]) == 4
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][14:16]) == 5
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][16:18]) == 10
                    )
                    stop_learn_move_yes_no = (
                            unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][0:2]) == 24
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][12:14]) == 4
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][14:16]) == 11
                            and unpack_uint16(get_task("TASK_EVOLUTIONSCENE")["data"][16:18]) == 0
                    )
    match context.rom.game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            move_menu_task = get_task("SUB_809E260")
        case "POKEMON EMER":
            move_menu_task = get_task("TASK_HANDLEREPLACEMOVEINPUT")
        case "POKEMON FIRE" | "POKEMON LEAF":
            move_menu_task = get_task("TASK_INPUTHANDLER_SELECTORFORGETMOVE")
        case _:
            move_menu_task = None
    move_menu = move_menu_task != {} and move_menu_task["isActive"]

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
    party_menu_index = get_party_menu_cursor_pos()["slot_id"]
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
        party_menu_index = get_party_menu_cursor_pos()["slot_id"]
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1
        yield

    match context.rom.game_title:
        case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
            for i in range(60):
                if "TASK_HANDLESELECTIONMENUINPUT" not in [task["func"] for task in parse_tasks()]:
                    context.emulator.press_button("A")
                else:
                    break
                yield
            while "TASK_HANDLESELECTIONMENUINPUT" in [task["func"] for task in parse_tasks()]:
                yield from PokemonPartySubMenuNavigator("SHIFT").step()
        case _:
            for i in range(60):
                if "TASK_HANDLEPOPUPMENUINPUT" not in [task["func"] for task in parse_tasks()]:
                    context.emulator.press_button("A")
                yield
            while "TASK_HANDLEPOPUPMENUINPUT" in [task["func"] for task in parse_tasks()]:
                context.emulator.press_button("A")
                yield


# TODO
def switch_out_pokemon(index):
    """
    Navigates from the party menu to the index of the desired Pokémon
    """
    cursor_positions = len(get_party()) + 1

    while not party_menu_is_open():
        context.emulator.press_button("A")
        yield

    party_menu_index = get_party_menu_cursor_pos()["slot_id"]
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
        party_menu_index = get_party_menu_cursor_pos()["slot_id"]
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1
        yield

    if context.rom.game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        while (
                not get_task("TASK_HANDLESELECTIONMENUINPUT") != {}
                and get_task("TASK_HANDLESELECTIONMENUINPUT")["isActive"]
        ):
            context.emulator.press_button("A")
            yield
        while get_task("TASK_HANDLESELECTIONMENUINPUT") != {} and get_task("TASK_HANDLESELECTIONMENUINPUT")["isActive"]:
            yield from PokemonPartySubMenuNavigator("SWITCH").step()
        while get_party_menu_cursor_pos()["action"] != 8:
            context.emulator.press_button("A")
            yield
        while get_party_menu_cursor_pos()["action"] == 8:
            if get_party_menu_cursor_pos()["slot_id_2"] == 7:
                context.emulator.press_button("Down")
            elif get_party_menu_cursor_pos()["slot_id_2"] != 0:
                context.emulator.press_button("Left")
            else:
                context.emulator.press_button("A")
            yield

        while get_game_state() == GameState.PARTY_MENU:
            context.emulator.press_button("B")
            yield
    else:
        while "SUB_8089D94" not in [task["func"] for task in parse_tasks()]:
            context.emulator.press_button("A")
            yield

        while ("SUB_8089D94" in [task["func"] for task in parse_tasks()]) and not (
                "SUB_808A060" in [task["func"] for task in parse_tasks()]
                or "HANDLEPARTYMENUSWITCHPOKEMONINPUT" in [task["func"] for task in parse_tasks()]
        ):
            yield from PokemonPartySubMenuNavigator("SWITCH").step()
            yield
        while switch_pokemon_active():
            if get_party_menu_cursor_pos()["slot_id_2"] != 0:
                context.emulator.press_button("Up")
            else:
                context.emulator.press_button("A")
            yield

        while (
                get_task("HANDLEDEFAULTPARTYMENU") == {}
                and get_task("HANDLEPARTYMENUSWITCHPOKEMONINPUT") == {}
                and get_task("HANDLEBATTLEPARTYMENU") == {}
        ):
            context.emulator.press_button("B")
            yield

    while get_game_state() != GameState.OVERWORLD or parse_start_menu()["open"]:
        context.emulator.press_button("B")
        yield

    for i in range(30):
        if get_game_state() != GameState.OVERWORLD or parse_start_menu()["open"]:
            break
        context.emulator.press_button("B")
        yield

    while get_game_state() != GameState.OVERWORLD or parse_start_menu()["open"]:
        context.emulator.press_button("B")
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
    if new_move.base_power == 0 or new_move.name in config["battle"]["banned_moves"]:
        context.message = f"New move has base power of 0, so {mon.name} will skip learning it."
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
        if move.name in config["battle"]["banned_moves"]:
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
            if move.name in config["battle"]["banned_moves"]:
                power = 0
            redundant_move_power.append(power)
        weakest_move_power = min(redundant_move_power)
        weakest_move = full_moveset.index(redundant_type_moves[redundant_move_power.index(weakest_move_power)])
        context.message = "Opting to replace a move that has a redundant type so as to maximize coverage."
    context.message = f"Move to replace is {full_moveset[weakest_move].name} with a calculated power of {weakest_move_power}"

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
    for i in range(len(old_party)):
        if old_party[i].level < new_party[i].level:
            return i
    return leveled_mon


def can_battle_happen() -> bool:
    """
    Determines whether the bot can battle with the state of the current party
    :return: True if the party is capable of having a battle, False otherwise
    """
    party = get_party()
    for mon in party:
        if mon.current_hp / mon.stats.hp > 0.2 and not mon.is_egg:
            for move in mon.moves:
                if (
                        move.move.base_power > 0
                        and move.move.name not in config["battle"]["banned_moves"]
                        and move.pp > 0
                ):
                    return True
    return False


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
        else:
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
            if 0 > move or move > 3:
                context.message = "Invalid move selection. Switching to manual mode..."
                context.bot_mode = "Manual"
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
            context.bot_mode = "Manual"
        case "SWITCH":
            if pokemon is None:
                execute_menu_action(("RUN", -1, -1))
            elif 0 > pokemon or pokemon > 6:
                context.message = "Invalid Pokemon selection. Switching to manual mode..."
                context.bot_mode = "Manual"
            else:
                select_battle_option = SelectBattleOption(2)
                while not get_battle_state() == BattleState.PARTY_MENU:
                    yield from select_battle_option.step()
                switcher = send_out_pokemon(pokemon)
                for _ in switcher:
                    yield
            return


# TODO
def check_lead_can_battle():
    """
    Determines whether the lead Pokémon is fit to fight
    """
    lead = get_party()[0]
    lead_has_moves = False
    for move in lead.moves:
        if move.move.base_power > 0 and move.move.name not in config["battle"]["banned_moves"] and move.pp > 0:
            lead_has_moves = True
            break
    lead_has_hp = lead.current_hp > 0.2 * lead.stats.hp
    return lead_has_hp and lead_has_moves


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
        elif mon.current_hp / mon.stats.hp > 0.2:
            for move in mon.moves:
                if move_is_usable(move):
                    return i
    return None


# TODO
def RotatePokemon():
    new_lead = get_new_lead()
    if new_lead is not None:
        yield from StartMenuNavigator("POKEMON").step()
        for i in range(30):
            if get_game_state() != GameState.PARTY_MENU:
                context.emulator.press_button("A")
                yield
        switcher = send_out_pokemon(new_lead)
        for _ in switcher:
            yield
    else:
        context.bot_mode = "Manual"


def mon_has_enough_hp(mon: Pokemon) -> bool:
    return mon.current_hp / mon.stats.hp > 0.2


def move_is_usable(m: LearnedMove) -> bool:
    return m.move.base_power > 0 and m.pp > 0 and m.move.name not in config["battle"]["banned_moves"]
