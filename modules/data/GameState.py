from enum import StrEnum  # https://docs.python.org/3/library/enum.html


class GameState(StrEnum):
    OVERWORLD = "CB2_Overworld"
    MISC_MENU = "sMenuCBTemp"
    BAG_MENU = "CB2_BagMenuRun"
    PARTY_MENU = "CB2_UpdatePartyMenu"
    POKEDEX = "CB2_PokedexScreen"
    # Needs further investigation; these values have multiple meanings
    BATTLE = "BattleMainCB2"
    ENTERING_BATTLE = "CB2_OverworldBasic"
    BATTLE_START = "CB2_HandleStartBattle"
    WHITEOUT = "CB2_WhiteOut"
    EVOLUTION = "CB2_EvolutionSceneUpdate"
    # BATTLE_2 = 2
    # FOE_DEFEATED = 5
    GARBAGE = "_"
    GARBAGE_COLLECTION = ".gcc2_compiled."
