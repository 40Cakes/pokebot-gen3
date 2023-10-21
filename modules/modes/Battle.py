from modules.Config import config, ForceManualMode
from modules.Gui import GetROM, GetEmulator, SetMessage
from modules.Memory import (
    GetGameState,
    ReadSymbol,
    ParseTasks,
    GetTaskFunc,
    GetSymbolName,
    GetTask,
    unpack_uint16,
    unpack_uint32,
)
from modules.Enums import GameState, TaskFunc, BattleState
from modules.MenuParsers import (
    get_party_menu_cursor_pos,
    parse_start_menu,
    get_battle_menu,
    switch_requested,
    get_learning_move_cursor_pos,
    get_learning_mon,
    get_battle_cursor,
    get_learning_move,
)
from modules.Menuing import (
    PartyMenuIsOpen,
    NavigateMenu,
    SwitchPokemonActive, NavigateStartMenu,
)
from modules.Pokemon import pokemon_list, type_list, GetParty, GetOpponent


def encounter_pokemon():
    match GetGameState():
        case GameState.BATTLE.value | GameState.BATTLE_STARTING.value | GameState.PARTY_MENU.value:
            if config["battle"]["battle"] and can_battle_happen():
                battle_opponent = BattleOpponent()
                while True:
                    yield from battle_opponent.step()
            else:
                while True:
                    yield from flee_battle()

        case GameState.GARBAGE_COLLECTION:
            yield

        # TODO
        #if config['battle']['battle'] and battle_can_happen:
        #    battle_won = BattleOpponent()
        #    # adding this in for lead rotation functionality down the line
        #    replace_battler = not battle_won
        #if config['battle']['battle'] and battle_can_happen:
        #    replace_battler = replace_battler or not CheckLeadCanBattle()
        #    if config['battle']["replace_lead_battler"] and replace_battler:
        #        RotatePokemon()
        #if config['battle']["pickup"] and battle_can_happen:
        #    while GetGameState() != GameState.OVERWORLD and not config['general']['bot_mode'] == 'manual':
        #        continue
        #    if GetGameState() == GameState.OVERWORLD:
        #        CheckForPickup(stats['totals'].get('encounters', 0))

def flee_battle():
    if get_battle_state() == BattleState.ACTION_SELECTION:
        battle_menu = BattleMenu(3)
        while True:
            yield from battle_menu.step()
    else:
        GetEmulator().PressButton("B")
    yield


class BattleOpponent:
    """
    Function to battle wild Pokémon. This will only battle with the lead Pokémon of the party, and will run if it dies
    or runs out of PP.
    """

    def __init__(self):
        self.battle_ended = False
        self.foe_fainted = GetOpponent()["stats"]["hp"] == 0
        self.prev_battle_state = get_battle_state()
        self.previous_party = GetParty()
        self.most_recent_leveled_mon_index = -1

    def step(self):
        while not self.battle_ended:
            self.battle_state = get_battle_state()
            if self.battle_state != self.prev_battle_state:
                self.prev_battle_state = self.battle_state

            # check for level ups
            party = GetParty()
            if self.previous_party != party:
                self.most_recent_leveled_mon_index = check_for_level_up(
                    self.previous_party, party, self.most_recent_leveled_mon_index
                )
                self.previous_party = party

            self.foe_fainted = GetOpponent()["stats"]["hp"] == 0

            match self.battle_state:
                case BattleState.OVERWORLD:
                    self.battle_ended = True
                case BattleState.EVOLVING:
                    if config["battle"]["stop_evolution"]:
                        GetEmulator().PressButton("B")
                    else:
                        GetEmulator().PressButton("A")
                case BattleState.LEARNING:
                    yield from handle_move_learn(self.most_recent_leveled_mon_index)
                case BattleState.ACTION_SELECTION.value | BattleState.MOVE_SELECTION.value:
                    yield from execute_menu_action(determine_battle_menu_action())
                case BattleState.SWITCH_POKEMON:
                    yield from handle_battler_faint()
                case _:
                    GetEmulator().PressButton("B")
            yield

        if self.foe_fainted:
            return True
        return False


def get_move_power(move, ally_types, foe_types, ally_attacks, foe_defenses) -> float:
    """
    function to calculate effective power of a move

    """
    power = move["power"]

    # Ignore banned moves and those with 0 PP
    if (not is_valid_move(move)) or (move["remaining_pp"] == 0):
        return 0

    matchups = type_list[move["type"]]
    category = matchups["category"]

    for foe_type in foe_types:
        if foe_type in matchups["immunes"]:
            return 0
        elif foe_type in matchups["weaknesses"]:
            power *= 0.5
        elif foe_type in matchups["strengths"]:
            power *= 2

    # STAB (same-type attack bonus)
    if move["type"] in ally_types:
        power *= 1.5

    # calculating attack/defense effect
    stat_calc = ally_attacks[category] / foe_defenses[category]
    power *= stat_calc

    return power


def is_valid_move(move: dict) -> bool:
    return move["name"] not in config["battle"]["banned_moves"] and move["power"] > 0


def calculate_new_move_viability(mon: dict, new_move: dict) -> int:
    """
    Function that judges the move a Pokémon is trying to learn against its moveset and returns the index of the worst
    move of the bunch.

    :param mon: The dict containing the Pokémon's info.
    :param new_move: The move that the mon is trying to learn
    :return: The index of the move to select.
    """
    # exit learning move if new move is banned or has 0 power
    if new_move["power"] == 0 or new_move["name"] in config["battle"]["banned_moves"]:
        SetMessage(f"New move has base power of 0, so {mon['name']} will skip learning it.")
        return 4
    # get the effective power of each move
    move_power = []
    full_moveset = list(mon["moves"])
    full_moveset.append(new_move)
    for move in full_moveset:
        attack_type = move["kind"]
        match attack_type:
            case "Physical":
                attack_bonus = mon["stats"]["attack"]
            case "Special":
                attack_bonus = mon["stats"]["spAttack"]
            case _:
                attack_bonus = 0
        power = move["power"] * attack_bonus
        if move["type"] in mon["type"]:
            power *= 1.5
        if move["name"] in config["battle"]["banned_moves"]:
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
        if move["power"] == 0:
            continue
        if move["type"] not in existing_move_types:
            existing_move_types[move["type"]] = move
        else:
            if not redundant_type_moves:
                redundant_type_moves.append(existing_move_types[move["type"]])
            redundant_type_moves.append(move)
    if weakest_move_power > 0 and redundant_type_moves:
        redundant_move_power = []
        for move in redundant_type_moves:
            attack_type = move["kind"]
            match attack_type:
                case "Physical":
                    attack_bonus = mon["stats"]["attack"]
                case "Special":
                    attack_bonus = mon["stats"]["spAttack"]
                case _:
                    attack_bonus = 0
            power = move["power"] * attack_bonus
            if move["type"] in mon["type"]:
                power *= 1.5
            if move["name"] in config["battle"]["banned_moves"]:
                power = 0
            redundant_move_power.append(power)
        weakest_move_power = min(redundant_move_power)
        weakest_move = full_moveset.index(redundant_type_moves[redundant_move_power.index(weakest_move_power)])
        SetMessage("Opting to replace a move that has a redundant type so as to maximize coverage.")
    SetMessage(
        f"Move to replace is {full_moveset[weakest_move]['name']} with a calculated power of {weakest_move_power}"
    )
    return weakest_move


def find_effective_move(ally: dict, foe: dict) -> dict:
    """
    Finds the best move for the ally to use on the foe.

    :param ally: The Pokémon being used to battle.
    :param foe: The Pokémon being battled.
    :return: A dictionary containing the name of the move to use, the move's index, and the effective power of the move.
    """
    move_power = []
    foe_types = pokemon_list[foe["name"]]["type"]
    foe_defenses = {
        "physical": foe["stats"]["defense"],
        "special": foe["stats"]["spDefense"],
    }
    ally_types = pokemon_list[ally["name"]]["type"]
    ally_attacks = {
        "physical": foe["stats"]["attack"],
        "special": foe["stats"]["spAttack"],
    }

    # calculate power of each possible move
    for i, move in enumerate(ally["moves"]):
        move_power.append(get_move_power(move, ally_types, foe_types, ally_attacks, foe_defenses))

    # calculate best move and return info
    best_move_index = move_power.index(max(move_power))
    return {
        "name": ally["moves"][best_move_index]["name"],
        "index": best_move_index,
        "power": max(move_power),
    }


def get_battle_state() -> BattleState:
    """
    Determines the state of the battle so the battle loop can figure out the right choice to make.
    """
    match GetGameState():
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
    match GetGameState():
        case GameState.BATTLE:
            learn_move_yes_no = (
                GetSymbolName(unpack_uint32(ReadSymbol("gBattleScriptCurrInstr", size=4)) - 17)
                == "BATTLESCRIPT_ASKTOLEARNMOVE"
            )
            stop_learn_move_yes_no = (
                GetSymbolName(unpack_uint32(ReadSymbol("gBattleScriptCurrInstr", size=4)) - 32)
                == "BATTLESCRIPT_ASKTOLEARNMOVE"
            )

        case GameState.EVOLUTION:
            match GetROM().game_title:
                case "POKEMON RUBY" | "POKEMON SAPP":
                    learn_move_yes_no = (
                        unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][0:2]) == 21
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][16:18]) == 4
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][18:20]) == 5
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][20:22]) == 9
                    )
                    stop_learn_move_yes_no = (
                        unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][0:2]) == 21
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][16:18]) == 4
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][18:20]) == 10
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][20:22]) == 0
                    )
                case "POKEMON EMER":
                    learn_move_yes_no = (
                        unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][0:2]) == 22
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][12:14]) in [3, 4]
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][14:16]) == 5
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][16:18]) == 10
                    )
                    stop_learn_move_yes_no = (
                        unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][0:2]) == 22
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][12:14]) == [3, 4]
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][14:16]) == 11
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][16:18]) == 0
                    )

                case "POKEMON FIRE" | "POKEMON LEAF":
                    learn_move_yes_no = (
                        unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][0:2]) == 24
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][12:14]) == 4
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][14:16]) == 5
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][16:18]) == 10
                    )
                    stop_learn_move_yes_no = (
                        unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][0:2]) == 24
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][12:14]) == 4
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][14:16]) == 11
                        and unpack_uint16(GetTask("TASK_EVOLUTIONSCENE")["data"][16:18]) == 0
                    )
    match GetROM().game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            move_menu_task = GetTask("SUB_809E260")
        case "POKEMON EMER":
            move_menu_task = GetTask("TASK_HANDLEREPLACEMOVEINPUT")
        case "POKEMON FIRE" | "POKEMON LEAF":
            move_menu_task = GetTask("TASK_INPUTHANDLER_SELECTORFORGETMOVE")
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


def get_current_battler() -> list:
    """
    Determines which Pokémon is battling
    """
    match GetROM().game_title:
        case "POKEMON RUBY" | "POKEMON SAPP":
            # this tells us which pokemon from our party are battling. 0 represents a pokemon in the party who isn't battling, and also the pokemon at index 0 :(
            battler_indices = [
                int.from_bytes(ReadSymbol("gBattlerPartyIndexes", size=12)[2 * i : 2 * i + 2], "little")
                for i in range(len(GetParty()))
            ]
            # this tells us how many pokemon are battling (2 for single battle, 4 for double) which allows us to get the pokemon info for the party members currently participating in the battle
            num_battlers = ReadSymbol("gBattlersCount", size=1)[0]
            # If we only have one party member, it's obviously the current battler so don't do the calcs for who's in battle
            if len(GetParty()) == 1:
                return GetParty()
            current_battlers = [GetParty()[battler_indices[i * 2]] for i in range(num_battlers // 2)]
            return current_battlers
        case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
            # this tells us which pokemon from our party are battling. 0 represents a pokemon in the party who isn't battling, and also the pokemon at index 0 :(
            battler_indices = [
                int.from_bytes(ReadSymbol("gBattlerPartyIndexes", size=12)[2 * i : 2 * i + 2], "little")
                for i in range(len(GetParty()))
            ]
            # this tells us how many pokemon are battling (2 for single battle, 4 for double) which allows us to get the pokemon info for the party members currently participating in the battle
            num_battlers = ReadSymbol("gBattlersCount", size=1)[0]
            # If we only have one party member, it's obviously the current battler so don't do the calcs for who's in battle
            if len(GetParty()) == 1:
                return GetParty()
            current_battlers = [GetParty()[battler_indices[i * 2]] for i in range(num_battlers // 2)]
            return current_battlers


def get_strongest_move() -> int:
    """
    Function that determines the strongest move to use given the current battler and the current
    """
    current_battlers = get_current_battler()
    if len(current_battlers) > 1:
        SetMessage("Double battle detected, not yet implemented. Switching to manual mode...")
        ForceManualMode()
    else:
        current_battler = current_battlers[0]
        current_opponent = GetOpponent()
        move = find_effective_move(current_battler, current_opponent)
        if move["power"] == 0:
            SetMessage("Lead Pokémon has no effective moves to battle the foe!")
            return -1

        SetMessage(f"Best move against {current_opponent['name']} is {move['name']}, effective power: {move['power']:.2f}")
        return move["index"]


def get_mon_to_switch(active_mon: int, show_messages=True) -> int:
    """
    Figures out which Pokémon should be switched out for the current active Pokémon.

    :param active_mon: the party index of the Pokémon that is being replaced.
    :param show_messages: Whether to display the message that Pokémon have usable moves or hit points, and whether
    Pokémon seem to be fit to fight.
    :return: the index of the Pokémon to switch with the active Pokémon
    """
    party = GetParty()
    match config["battle"]["switch_strategy"]:
        case "first_available":
            for i in range(len(party)):
                if party[i] == active_mon or party[i]["isEgg"]:
                    continue
                # check to see that the party member has enough HP to be subbed out
                elif party[i]["stats"]["hp"] / party[i]["stats"]["maxHP"] > 0.2:
                    if show_messages:
                        SetMessage(f"Pokémon {party[i]['name']} has more than 20% hp!")
                    for move in party[i]["moves"]:
                        if (
                            move["power"] > 0
                            and move["remaining_pp"] > 0
                            and move["name"] not in config["battle"]["banned_moves"]
                            and move["kind"] in ["Physical", "Special"]
                        ):
                            if show_messages:
                                SetMessage(f"Pokémon {party[i]['name']} has usable moves!")
                            return i
            if show_messages:
                SetMessage("No Pokémon seem to be fit to fight.")


def should_rotate_lead() -> bool:
    """
    Determines whether the battle engine should swap out the lead pokemon.
    """
    battler = get_current_battler()[0]
    battler_health_percentage = battler["stats"]["hp"] / battler["stats"]["maxHP"]
    return battler_health_percentage < 0.2


# TODO
def send_out_pokemon(index):
    """
    Navigates from the party menu to the index of the desired pokemon
    """
    # options are the entire length of the party plus a cancel option
    cursor_positions = len(GetParty()) + 1

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
            GetEmulator().PressButton("Up")
        else:
            GetEmulator().PressButton("Down")
        party_menu_index = get_party_menu_cursor_pos()["slot_id"]
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1
        yield

    match GetROM().game_title:
        case "POKEMON EMER" | "POKEMON FIRE" | "POKEMON LEAF":
            for i in range(60):
                if "TASK_HANDLESELECTIONMENUINPUT" not in [task["func"] for task in ParseTasks()]:
                    GetEmulator().PressButton("A")
                else:
                    break
                yield
            while "TASK_HANDLESELECTIONMENUINPUT" in [task["func"] for task in ParseTasks()]:
                NavigateMenu("SHIFT")
        case _:
            for i in range(60):
                if "TASK_HANDLEPOPUPMENUINPUT" not in [task["func"] for task in ParseTasks()]:
                    GetEmulator().PressButton("A")
                yield
            while "TASK_HANDLEPOPUPMENUINPUT" in [task["func"] for task in ParseTasks()]:
                GetEmulator().PressButton("A")
                yield


# TODO
def switch_out_pokemon(index):
    """
    Navigates from the party menu to the index of the desired Pokémon
    """
    cursor_positions = len(GetParty()) + 1

    while not PartyMenuIsOpen():
        GetEmulator().PressButton("A")
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
            GetEmulator().PressButton("Up")
        else:
            GetEmulator().PressButton("Down")
        party_menu_index = get_party_menu_cursor_pos()["slot_id"]
        if party_menu_index >= cursor_positions:
            party_menu_index = cursor_positions - 1
        yield

    if GetROM().game_title in ["POKEMON EMER", "POKEMON FIRE", "POKEMON LEAF"]:
        while (
            not GetTask("TASK_HANDLESELECTIONMENUINPUT") != {} and GetTask("TASK_HANDLESELECTIONMENUINPUT")["isActive"]
        ):
            GetEmulator().PressButton("A")
            yield
        while GetTask("TASK_HANDLESELECTIONMENUINPUT") != {} and GetTask("TASK_HANDLESELECTIONMENUINPUT")["isActive"]:
            NavigateMenu("SWITCH")
        while get_party_menu_cursor_pos()["action"] != 8:
            GetEmulator().PressButton("A")
            yield
        while get_party_menu_cursor_pos()["action"] == 8:
            if get_party_menu_cursor_pos()["slot_id_2"] == 7:
                GetEmulator().PressButton("Down")
            elif get_party_menu_cursor_pos()["slot_id_2"] != 0:
                GetEmulator().PressButton("Left")
            else:
                GetEmulator().PressButton("A")
            yield

        while GetGameState() == GameState.PARTY_MENU:
            GetEmulator().PressButton("B")
            yield
    else:
        while "SUB_8089D94" not in [task["func"] for task in ParseTasks()]:
            GetEmulator().PressButton("A")
            yield

        while ("SUB_8089D94" in [task["func"] for task in ParseTasks()]) and not (
            "SUB_808A060" in [task["func"] for task in ParseTasks()]
            or "HANDLEPARTYMENUSWITCHPOKEMONINPUT" in [task["func"] for task in ParseTasks()]
        ):
            NavigateMenu("SWITCH")
            yield
        while SwitchPokemonActive():
            if get_party_menu_cursor_pos()["slot_id_2"] != 0:
                GetEmulator().PressButton("Up")
            else:
                GetEmulator().PressButton("A")
            yield

        while TaskFunc.PARTY_MENU not in [GetTaskFunc(task["func"]) for task in ParseTasks()]:
            GetEmulator().PressButton("B")
            yield

    while GetGameState() != GameState.OVERWORLD or parse_start_menu()["open"]:
        GetEmulator().PressButton("B")
        yield

    for i in range(30):
        if GetGameState() != GameState.OVERWORLD or parse_start_menu()["open"]:
            break
        GetEmulator().PressButton("B")
        yield

    while GetGameState() != GameState.OVERWORLD or parse_start_menu()["open"]:
        GetEmulator().PressButton("B")
        yield


# TODO
def handle_battler_faint():
    """
    function that handles lead battler fainting
    """
    SetMessage("Lead Pokémon fainted!")
    match config["battle"]["faint_action"]:
        case "stop":
            SetMessage("Switching to manual mode...")
            ForceManualMode()
        case "flee":
            while get_battle_state() not in [BattleState.OVERWORLD, BattleState.PARTY_MENU]:
                GetEmulator().PressButton("B")
                yield
            if get_battle_state() == BattleState.PARTY_MENU:
                SetMessage("Couldn't flee. Switching to manual mode...")
                ForceManualMode()
            else:
                while not GetGameState() == GameState.OVERWORLD:
                    GetEmulator().PressButton("B")
                    yield
                return False
        case "rotate":
            party = GetParty()
            if sum([mon["stats"]["hp"] for mon in party]) == 0:
                SetMessage("All Pokémon have fainted. Switching to manual mode...")
                ForceManualMode()
            while get_battle_state() != BattleState.PARTY_MENU:
                GetEmulator().PressButton("A")
                yield
            new_lead = get_mon_to_switch(get_current_battler()[0])
            if new_lead is None:
                SetMessage("No viable pokemon to switch in!")
                faint_action_default = str(config["battle"]["faint_action"])
                config["battle"]["faint_action"] = "flee"
                handle_battler_faint()
                config["battle"]["faint_action"] = faint_action_default
                return False
            send_out_pokemon(new_lead)
            while get_battle_state() in (BattleState.SWITCH_POKEMON, BattleState.PARTY_MENU):
                GetEmulator().PressButton("A")
                yield
        case _:
            SetMessage("Invalid faint_action option. Switching to manual mode...")
            ForceManualMode()


# TODO
def check_for_level_up(old_party: list[dict], new_party: list[dict], leveled_mon) -> int:
    """
    Compares the previous party state to the most recently gathered party state, and returns the index of the first
    pokemon whose level is higher in the new party state.

    :param old_party: The previous party state
    :param new_party: The most recent party state
    :param leveled_mon: The index of the pokemon that was most recently leveled before this call.
    :return: The first index where a pokemon's level is higher in the new party than the old one.
    """
    if len(old_party) != len(new_party):
        SetMessage("Party length has changed. Assuming a pokemon was just caught.")
    for i in range(len(old_party)):
        if old_party[i]["level"] < new_party[i]["level"]:
            return i
    return leveled_mon


def can_battle_happen() -> bool:
    """
    Determines whether the bot can battle with the state of the current party
    :return: True if the party is capable of having a battle, False otherwise
    """
    first_suitable_battler = get_mon_to_switch(-1, show_messages=False)
    if first_suitable_battler is None:
        return False
    return True


def determine_battle_menu_action() -> tuple:
    """
    Determines which action to select from the action menu

    :return: a tuple containing 1. the action to take, 2. the move to use if so desired, 3. the index of the pokemon to
    switch to if so desired.
    """
    if not config["battle"]["battle"] or not can_battle_happen():
        return "RUN", -1, -1
    elif config["battle"]["replace_lead_battler"] and should_rotate_lead():
        mon_to_switch = get_mon_to_switch(get_current_battler()[0])
        if mon_to_switch is None:
            return "RUN", -1, -1
        return "SWITCH", -1, mon_to_switch
    else:
        match config["battle"]["battle_method"]:
            case "strongest":
                move = get_strongest_move()
                if move == -1:
                    if config["battle"]["replace_lead_battler"]:
                        mon_to_switch = get_mon_to_switch(get_current_battler()[0])
                        if mon_to_switch is None:
                            return "RUN", -1, -1
                        return "SWITCH", -1, mon_to_switch
                    action = "RUN"
                else:
                    action = "FIGHT"
                return action, move, -1
            case _:
                SetMessage("Not yet implemented")
                return "RUN", -1, -1


class BattleMenu:
    def __init__(self, index: int):
        self.index: int = index
        if not 0 <= self.index <= 3:
            return
        self.battle_state = get_battle_state()
        match self.battle_state:
            case BattleState.ACTION_SELECTION:
                self.cursor_type = "gActionSelectionCursor"
            case BattleState.MOVE_SELECTION:
                self.cursor_type = "gMoveSelectionCursor"
            case _:
                return

    def step(self):
        if get_battle_cursor(self.cursor_type) != self.index:
            match (get_battle_cursor(self.cursor_type) % 2) - (self.index % 2):
                case -1:
                    GetEmulator().PressButton("Right")
                case 1:
                    GetEmulator().PressButton("Left")
            match (get_battle_cursor(self.cursor_type) // 2) - (self.index // 2):
                case -1:
                    GetEmulator().PressButton("Down")
                case 1:
                    GetEmulator().PressButton("Up")
        elif get_battle_cursor(self.cursor_type) == self.index:
            if get_battle_state() == self.battle_state:
                GetEmulator().PressButton("A")
        yield


class SelectBattleOption:
    """
    Takes a desired battle menu option, navigates to it, and presses it.

    :param desired_option: The desired index for the selection. For the base battle menu, 0 will be FIGHT, 1 will be
    BAG, 2 will be PKMN, and 3 will be RUN.
     options.
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
                    GetEmulator().PressButton("Right")
                case 1:
                    GetEmulator().PressButton("Left")
            match (get_battle_cursor(self.cursor_type) // 2) - (self.index // 2):
                case -1:
                    GetEmulator().PressButton("Down")
                case 1:
                    GetEmulator().PressButton("Up")
            yield
        if get_battle_cursor(self.cursor_type) == self.index and get_battle_state() == self.battle_state:
            GetEmulator().PressButton("A")
        yield


# TODO
def handle_move_learn(leveled_mon: int):
    match config["battle"]["new_move"]:
        case "stop":
            SetMessage("New move trying to be learned, switching to manual mode...")
            ForceManualMode()
        case "cancel":
            while GetGameState() != GameState.OVERWORLD:
                if get_learn_move_state() != "STOP_LEARNING":
                    GetEmulator().PressButton("B")
                else:
                    GetEmulator().PressButton("A")
                yield
        case "learn_best":
            if GetGameState() == GameState.BATTLE:
                learning_mon = GetParty()[leveled_mon]
            else:
                learning_mon = get_learning_mon()
            learning_move = get_learning_move()
            worst_move = calculate_new_move_viability(learning_mon, learning_move)
            if worst_move == 4:
                while get_learn_move_state() == "LEARN_YN":
                    GetEmulator().PressButton("B")
                    yield

                # for i in range(60):
                #    if get_learn_move_state() != "STOP_LEARNING":
                #        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
                #    else:
                #        break

                while get_learn_move_state() == "STOP_LEARNING":
                    GetEmulator().PressButton("A")
                    yield
            else:
                while get_learn_move_state() == "LEARN_YN":
                    GetEmulator().PressButton("A")
                    yield

                # for i in range(60):
                #    if not get_learn_move_state() == "MOVE_MENU":
                #        GetEmulator().RunSingleFrame()  # TODO bad (needs to be refactored so main loop advances frame)
                #    else:
                #        break

                navigate_move_learn_menu(worst_move)

                while get_learn_move_state() == "STOP_LEARNING":
                    GetEmulator().PressButton("B")
                    yield

            while get_battle_state() == BattleState.LEARNING and get_learn_move_state() not in [
                "MOVE_MENU",
                "LEARN_YN",
                "STOP_LEARNING",
            ]:
                GetEmulator().PressButton("B")
                yield


# TODO
def navigate_move_learn_menu(index):
    """
    Function that handles navigation of the move learning menu

    :param index: the move to select (usually for forgetting a move)
    """
    while get_learn_move_state() == "MOVE_MENU":
        if get_learning_move_cursor_pos() < index:
            up_presses = get_learning_move_cursor_pos() + 5 - index
            down_presses = index - get_learning_move_cursor_pos()
        else:
            up_presses = get_learning_move_cursor_pos() - index
            down_presses = index - get_learning_move_cursor_pos() + 5
        if down_presses > up_presses:
            GetEmulator().PressButton("Up")
        else:
            GetEmulator().PressButton("Down")
        if get_learning_move_cursor_pos() == index:
            GetEmulator().PressButton("A")
        yield


# TODO
def execute_menu_action(decision: tuple):
    """
    Given a decision made by the battle engine, executes the desired action.

    :param decision: The output of determine_battle_menu_action, containing an action, move index, and pokemon index.
    """
    action, move, pokemon = decision
    match action:
        case "RUN":
            flee_battle()
            return
        case "FIGHT":
            if 0 > move or move > 3:
                SetMessage("Invalid move selection. Switching to manual mode...")
                ForceManualMode()
            while True:
                match get_battle_state():
                    case BattleState.ACTION_SELECTION:
                        select_battle_option = SelectBattleOption(0).step()
                        while True:
                            yield from select_battle_option
                    case BattleState.MOVE_SELECTION:
                        select_battle_option = SelectBattleOption(move).step()
                        while True:
                            yield from select_battle_option
                    case _:
                        GetEmulator().PressButton("B")
                yield
        case "BAG":
            SetMessage("Bag not yet implemented. Switching to manual mode...")
            ForceManualMode()
        case "SWITCH":
            if pokemon is None:
                execute_menu_action(("RUN", -1, -1))
            elif 0 > pokemon or pokemon > 6:
                SetMessage("Invalid Pokemon selection. Switching to manual mode...")
                ForceManualMode()
            else:
                select_battle_option = SelectBattleOption(2)
                while not get_battle_state() == BattleState.PARTY_MENU:
                    yield from select_battle_option.step()
                send_out_pokemon(pokemon)
            return


# TODO
def check_lead_can_battle():
    """
    Determines whether the lead Pokémon is fit to fight
    """
    lead = GetParty()[0]
    lead_has_moves = False
    for move in lead['moves']:
        if (
            move['power'] > 0 and
            move['name'] not in config['battle']['banned_moves'] and
            move['remaining_pp'] > 0
        ):
            lead_has_moves = True
            break
    lead_has_hp = lead['stats']['hp'] > .2 * lead['stats']['maxHP']
    return lead_has_hp and lead_has_moves


# TODO
def RotatePokemon():
    new_lead = get_mon_to_switch(0)
    if new_lead is not None:
        NavigateStartMenu("POKEMON")
        for i in range(30):
            if GetGameState() != GameState.PARTY_MENU:
                GetEmulator().PressButton('A')
                yield
        send_out_pokemon(new_lead)
