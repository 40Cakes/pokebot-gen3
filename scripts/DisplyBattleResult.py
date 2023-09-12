# Displays The gBattleResults Struct when it changes and should be valid
# Move this script to the root directory to ensure all imports work correctly
from modules.Console import console
from rich.table import Table
from rich.live import Live
from modules.Memory import ReadSymbol, DecodeString, names_list  # b_Trainer
import struct


def SpeciesName(value: int) -> str:
    if value > len(names_list):
        return ""
    return names_list[value - 1]


def BattleResult():
    data = ReadSymbol("gBattleResults")
    battleResult = {
        "playerFaintCounter": int(data[0]),
        "opponentFaintCounter": int(data[1]),
        "playerSwitchesCounter": int(data[2]),
        "numHealingItemsUsed": int(data[3]),
        "numRevivesUsed": int(data[4]),
        "playerMonWasDamaged": bool(data[5] & 0x1),  #:1; // 0x5
        "usedMasterBall": bool(data[5] & 0x2),  #:1;      // 0x5
        "caughtMonBall": int(data[5] & 0x30),  #:4;       // 0x5
        "shinyWildMon": bool(data[5] & 0x40),  #:1;        // 0x5
        "playerMon1Species": struct.unpack("<H", data[6:8])[0],
        "playerMon1Name": data[8:19],  # SpeciesName(battleResult.playerMon1Species)
        "battleTurnCounter": int(data[19]),
        "playerMon2Name": data[20:31],
        "pokeblockThrows": int(data[31]),
        "lastOpponentSpecies": struct.unpack("<H", data[32:34])[0],
        "lastUsedMovePlayer": struct.unpack("<H", data[34:36])[0],
        "lastUsedMoveOpponent": struct.unpack("<H", data[36:38])[0],
        "playerMon2Species": struct.unpack("<H", data[38:40])[0],
        "caughtMonSpecies": struct.unpack("<H", data[40:42])[0],
        "caughtMonNick": data[42:53],
        "catchAttempts": int(data[54]),
    }
    return battleResult


# console.print("[bold green]Found Player: " + DecodeString(b_Trainer[0:7]))
last_br = BattleResult()


def generate_table() -> Table:
    br_table = Table()
    br_table.add_column("Name", justify="left", no_wrap=True)
    br_table.add_column("Value", justify="left", width=10)
    br_table.add_row("Player Faint Counter", str(last_br["playerFaintCounter"]))
    br_table.add_row("Opponent Faint Counter", str(last_br["opponentFaintCounter"]))
    br_table.add_row("Player Switch Counter", str(last_br["playerSwitchesCounter"]))
    br_table.add_row("Count Healing Items used", str(last_br["numHealingItemsUsed"]))
    br_table.add_row("Player Mon Damaged", str(last_br["playerMonWasDamaged"]))
    br_table.add_row("Master Ball used", str(last_br["usedMasterBall"]))
    br_table.add_row("Caught Mon Ball used", str(last_br["caughtMonBall"]))
    br_table.add_row("Wild Mon was Shiny", str(last_br["shinyWildMon"]))
    br_table.add_row("Count Revives used", str(last_br["numRevivesUsed"]))
    br_table.add_row("Player Mon 1 Species", str(last_br["playerMon1Species"]))
    br_table.add_row("Player Mon 1 Name", DecodeString(last_br["playerMon1Name"]))
    br_table.add_row("Battle turn Counter", str(last_br["battleTurnCounter"]))
    br_table.add_row("Player Mon 2 Species", str(last_br["playerMon2Species"]))
    br_table.add_row("Player Mon 2 Name", DecodeString(last_br["playerMon2Name"]))
    br_table.add_row("PokeBall Throws", str(last_br["pokeblockThrows"]))
    br_table.add_row("Last Opponent Species", str(last_br["lastOpponentSpecies"]))
    br_table.add_row("Last Opponent Name", SpeciesName(last_br["lastOpponentSpecies"]))
    br_table.add_row("Last used Move Player", str(last_br["lastUsedMovePlayer"]))
    br_table.add_row("Last used Move Opponent", str(last_br["lastUsedMoveOpponent"]))
    br_table.add_row("Cought Mon Species", str(last_br["caughtMonSpecies"]))
    br_table.add_row("Cought Mon Name", DecodeString(last_br["caughtMonNick"]))
    br_table.add_row("Catch Attempts", str(last_br["catchAttempts"]))
    return br_table


with Live(generate_table(), refresh_per_second=4) as live:
    while True:
        br = BattleResult()
        if last_br != br:
            last_br = br
            if br["playerMon1Species"] > 0:
                live.update(generate_table())
