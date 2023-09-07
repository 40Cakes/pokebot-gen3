from typing import NoReturn
import os

from modules.Config import config
from modules.Inputs import PressButton, WaitFrames
from modules.Memory import ReadSymbol, GetTrainer, pokemon_list, type_list, GetParty, GetOpponent, DecodeString
from modules.data.GameState import GameState
from modules.Console import console


def SelectBattleOption(desired_option: int, cursor_type: str = "gActionSelectionCursor") -> NoReturn:
    """
    Takes a desired battle menu option, navigates to it, and presses it.

    :param desired_option: The desired index for the selection. For the base battle menu, 0 will be FIGHT, 1 will be
    BAG, 2 will be PKMN, and 3 will be RUN.
    :param cursor_type: The symbol to use for the cursor. This is different between selecting moves and selecting battle
     options.
    """
    while ReadSymbol(cursor_type)[0] != desired_option:
        match (ReadSymbol(cursor_type)[0] % 2) - (desired_option % 2):
            case - 1:
                PressButton(["Right"])
            case 1:
                PressButton(["Left"])
        match (ReadSymbol(cursor_type)[0] // 2) - (desired_option // 2):
            case - 1:
                PressButton(["Down"])
            case 1:
                PressButton(["Up"])
            case 0:
                pass
    if ReadSymbol(cursor_type)[0] == desired_option:
        # get current displayed string
        current_string = DecodeString(ReadSymbol('gDisplayedStringBattle'))
        # mash A until the string changes
        while DecodeString(ReadSymbol('gDisplayedStringBattle')) == current_string:
            PressButton(['A'])


def FleeBattle() -> NoReturn:
    """
    Readable function to select and execute the Run option from the battle menu.
    """
    SelectBattleOption(3, cursor_type='gActionSelectionCursor')
    while GetTrainer()['state'] != GameState.OVERWORLD:
        PressButton(["B"])


def getMovePower(move, ally_types, foe_types, ally_attacks, foe_defenses) -> float:
    """
    function to calculate effective power of a move

    """
    power = move["power"]

    # Ignore banned moves and those with 0 PP
    if (not isValidMove(move)) or (move["remaining_pp"] == 0):
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


def isValidMove(move: dict) -> bool:
    return move["name"] not in config["banned_moves"] and move["power"] > 0


def calculate_new_move_viability(party: dict) -> bool:
    """
    new_party = GetParty()
    for pkmn in new_party.values():
        for i in range(len(party)):
            if party[i]["pid"] == pkmn["pid"]:
                old_pkmn = party[i]
                if old_pkmn["level"] < pkmn["level"]:
                    print(
                        f"{pkmn['name']} has grown {pkmn['level'] - old_pkmn['level']} level{'s'*((pkmn['level'] - old_pkmn['level']) > 1)}"
                    )
                    pkmn_name = pkmn["name"]
                    print(f"Learnset: {ReadSymbol(f's{pkmn_name}LevelUpLearnset')}")
                    print(f"Text flags: {DecodeString(ReadSymbol('gTextFlags'))}")
                    print(f"Text: {DecodeString(ReadSymbol('.text'))}")
                    print(f"G String Var 1: {DecodeString(ReadSymbol('gStringVar1'))}")
                    print(f"G String Var 2: {DecodeString(ReadSymbol('gStringVar2'))}")
                    print(f"G String Var 3: {DecodeString(ReadSymbol('gStringVar3'))}")
                    print(f"G String Var 4: {DecodeString(ReadSymbol('gStringVar4'))}")
                    print(f"G String Var 4: {DecodeString(ReadSymbol('gStringVar4'))}")
                    print(f"PlayerHandleGetRawMonData: {ParsePokemon(ReadSymbol('PlayerHandleGetRawMonData'))}")
    """
    return False


def FindEffectiveMove(ally: dict, foe: dict) -> dict:
    """
    Finds the best move for the ally to use on the foe.

    :param ally: The pokemon being used to battle.
    :param foe: The pokemon being battled.
    :return: A dictionary containing the name of the move to use, the move's index, and the effective power of the move.
    """
    move_power = []
    foe_types = pokemon_list[foe["name"]]["type"]
    foe_defenses = {
        'physical': foe['stats']['defense'],
        'special': foe['stats']['spDefense'],
    }
    ally_types = pokemon_list[ally["name"]]["type"]
    ally_attacks = {
        'physical': foe['stats']['attack'],
        'special': foe['stats']['spAttack'],
    }

    # calculate power of each possible move
    for i, move in enumerate(ally["moves"]):
        move_power.append(getMovePower(move, ally_types, foe_types, ally_attacks, foe_defenses))

    # calculate best move and return info
    best_move_index = move_power.index(max(move_power))
    return {
        "name": ally["moves"][best_move_index]["name"],
        "index": best_move_index,
        "power": max(move_power),
    }


def BattleOpponent() -> bool:
    """
    Function to battle wild Pokémon. This will only battle with the lead pokemon of the party, and will run if it dies
    or runs out of PP.
    :return: Boolean value of whether the battle was won.
    """
    ally_fainted = False
    foe_fainted = False

    while not ally_fainted and not foe_fainted and GetTrainer()["state"] != GameState.OVERWORLD:
        if GetTrainer()["state"] == GameState.OVERWORLD:
            return True

        best_move = FindEffectiveMove(GetParty()[0], GetOpponent())

        if best_move["power"] < 10:
            console.print("Lead pokemon has no effective moves to battle the foe!")
            FleeBattle()
            os._exit(0)
            # For future use when auto lead rotation is on
            # return False

        # If effective moves are present, let's fight this thing!
        while "What will" in DecodeString(ReadSymbol("gDisplayedStringBattle")):
            console.print("Navigating to the Fight button...")
            SelectBattleOption(0, cursor_type="gActionSelectionCursor")

        WaitFrames(5)

        console.print(f"Best move against foe is {best_move['name']} (Effective power is {best_move['power']})")

        SelectBattleOption(best_move["index"], cursor_type="gMoveSelectionCursor")

        WaitFrames(5)

        while GetTrainer()["state"] != GameState.OVERWORLD and "What will" not in DecodeString(
            ReadSymbol("gDisplayedStringBattle")
        ):
            if "Delete a move" not in DecodeString(ReadSymbol("gDisplayedStringBattle")):
                PressButton(["B"])
                WaitFrames(1)
            if "Delete a move" in DecodeString(ReadSymbol("gDisplayedStringBattle")):
                handle_move_learning()

        ally_fainted = GetParty()[0]["stats"]["hp"] == 0
        foe_fainted = GetOpponent()["stats"]["hp"] == 0

    if ally_fainted:
        console.print("Lead Pokemon fainted!")
        FleeBattle()
        return False
    return True


def handle_move_learning():
    match config["new_move_mode"]:
        case "stop":
            os._exit(1)
        case "cancel":
            # TODO: figure out what gamestate corresponds to evolution and allow evolution as a config option maybe?
            while GetTrainer()["state"] != GameState.OVERWORLD:
                if "Stop learning" not in DecodeString(ReadSymbol('gDisplayedStringBattle')):
                    PressButton(["B"])
                else:
                    PressButton(["A"])
        case "learn_best":
            # TODO: figure this out

            """
            calculate_new_move_viability(party)
            WaitFrames(240)
            PressButton(["A"])
            print(f"Move to learn: {ReadSymbol('gMoveToLearn')}")
            print(
                f"Current string: {DecodeString(ReadSymbol('gDisplayedStringBattle'))}"
            )
            print(f"Move to learn: {DecodeString(ReadSymbol('gMoveToLearn'))}")
            print(
                f"Leveled up in battle: {DecodeString(ReadSymbol('gLeveledUpInBattle'))}"
            )
            print(
                f"Action Selection Cursor: {DecodeString(ReadSymbol('gActionSelectionCursor'))}"
            )
            print(
                f"Move Selection Cursor: {DecodeString(ReadSymbol('gMoveSelectionCursor'))}"
            )
            print(f"G String Var 1: {DecodeString(ReadSymbol('gStringVar1'))}")
            print(f"G String Var 2: {DecodeString(ReadSymbol('gStringVar2'))}")
            print(f"G String Var 3: {DecodeString(ReadSymbol('gStringVar3'))}")
            print(f"G String Var 4: {DecodeString(ReadSymbol('gStringVar4'))}")
            print(
                f"PlayerHandleGetRawMonData: {ParsePokemon(ReadSymbol('PlayerHandleGetRawMonData'))}"
            )
            for i in range(10):
                WaitFrames(120)
                print(
                    f"Current string: {DecodeString(ReadSymbol('gDisplayedStringBattle'))}"
                )
                print(f"Move to learn: {ReadSymbol('gMoveToLearn')}")
                print(f"Move to learn: {DecodeString(ReadSymbol('gMoveToLearn'))}")
                print(
                    f"Leveled up in battle: {DecodeString(ReadSymbol('gLeveledUpInBattle'))}"
                )
                print(
                    f"Action Selection Cursor: {DecodeString(ReadSymbol('gActionSelectionCursor'))}"
                )
                print(
                    f"Move Selection Cursor: {DecodeString(ReadSymbol('gMoveSelectionCursor'))}"
                )
                print(f"G String Var 1: {DecodeString(ReadSymbol('gStringVar1'))}")
                print(f"G String Var 2: {DecodeString(ReadSymbol('gStringVar2'))}")
                print(f"G String Var 3: {DecodeString(ReadSymbol('gStringVar3'))}")
                print(f"G String Var 4: {DecodeString(ReadSymbol('gStringVar4'))}")
                print(
                    f"PlayerHandleGetRawMonData: {ParsePokemon(ReadSymbol('PlayerHandleGetRawMonData'))}"
                )
                PressButton(["Down"])
            os._exit(0)
            """
        case _:
            console.print("Config new_move_mode invalid.")
