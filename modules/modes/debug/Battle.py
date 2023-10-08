# Displays The gBattleResults Struct when it changes and should be valid

import struct
from rich.table import Table
from rich.live import Live
from modules.Game import DecodeString
from modules.Gui import emulator
from modules.Memory import ReadSymbol
from modules.Pokemon import names_list


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
        "shinyWildMon": bool(data[5] & 0x40),  #:1;       // 0x5
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


def generate_table(data: dict) -> Table:
    br_table = Table()
    br_table.add_column("Name", justify="left", no_wrap=True)
    br_table.add_column("Value", justify="left", width=10)
    br_table.add_row("Player Faint Counter", str(data["playerFaintCounter"]))
    br_table.add_row("Opponent Faint Counter", str(data["opponentFaintCounter"]))
    br_table.add_row("Player Switch Counter", str(data["playerSwitchesCounter"]))
    br_table.add_row("Count Healing Items used", str(data["numHealingItemsUsed"]))
    br_table.add_row("Player Mon Damaged", str(data["playerMonWasDamaged"]))
    br_table.add_row("Master Ball used", str(data["usedMasterBall"]))
    br_table.add_row("Caught Mon Ball used", str(data["caughtMonBall"]))
    br_table.add_row("Wild Mon was Shiny", str(data["shinyWildMon"]))
    br_table.add_row("Count Revives used", str(data["numRevivesUsed"]))
    br_table.add_row("Player Mon 1 Species", str(data["playerMon1Species"]))
    br_table.add_row("Player Mon 1 Name", DecodeString(data["playerMon1Name"]))
    br_table.add_row("Battle turn Counter", str(data["battleTurnCounter"]))
    br_table.add_row("Player Mon 2 Species", str(data["playerMon2Species"]))
    br_table.add_row("Player Mon 2 Name", DecodeString(data["playerMon2Name"]))
    br_table.add_row("PokeBall Throws", str(data["pokeblockThrows"]))
    br_table.add_row("Last Opponent Species", str(data["lastOpponentSpecies"]))
    br_table.add_row("Last Opponent Name", SpeciesName(data["lastOpponentSpecies"]))
    br_table.add_row("Last used Move Player", str(data["lastUsedMovePlayer"]))
    br_table.add_row("Last used Move Opponent", str(data["lastUsedMoveOpponent"]))
    br_table.add_row("Cought Mon Species", str(data["caughtMonSpecies"]))
    br_table.add_row("Cought Mon Name", DecodeString(data["caughtMonNick"]))
    br_table.add_row("Catch Attempts", str(data["catchAttempts"]))
    return br_table


def ModeDebugBattle():
    last_br = BattleResult()
    with Live(generate_table(last_br), refresh_per_second=60) as live:
        while True:
            br = BattleResult()
            if last_br != br:
                last_br = br
                if br["playerMon1Species"] > 0:
                    live.update(generate_table(last_br))
            emulator.RunSingleFrame()
