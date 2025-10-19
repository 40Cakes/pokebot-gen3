from typing import Generator
from enum import IntEnum

from modules.context import context
from modules.map import get_map_data_for_current_position
from modules.modes import BattleAction
from modules.pokemon_party import get_party
from modules.player import get_player_avatar
from modules.map_data import MapRSE
from ._asserts import assert_party_has_damaging_move
from ._interface import BotMode, BotModeError
from .util import change_lead_party_pokemon
from .util.map import map_has_pokemon_center_nearby
from .util.pokecenter_loop import PokecenterLoopController
from ..battle_state import BattleOutcome
from ..battle_strategies import BattleStrategy
from ..battle_strategies.level_balancing import LevelBalancingBattleStrategy
from ..battle_strategies.level_up import LevelUpLeadBattleStrategy
from ..encounter import EncounterInfo
from ..gui.multi_select_window import ask_for_choice, Selection, ask_for_confirmation
from ..pokemon import pokemon_has_usable_damaging_move
from ..runtime import get_sprites_path
from ..sprites import get_sprite
from .util import (
    ensure_facing_direction,
    follow_waypoints,
    navigate_to,
    register_key_item,
    talk_to_npc,
    wait_for_player_avatar_to_be_controllable,
    wait_for_n_frames,
    wait_for_task_to_start_and_finish,
    wait_until_task_is_active,
    wait_for_script_to_start_and_finish,
    wait_until_script_is_active,
    wait_for_no_script_to_run,
)


class ContestTypeChoice(IntEnum):
    '''Contest type. Number corresponds to placement in dropdown menu'''
    COOLNESS = 0,
    BEAUTY = 1,
    CUTENESS = 2,
    SMARTNESS = 3,
    TOUGHNESS = 4,


class ContestRankChoice(IntEnum):
    '''Contest rank. Number corresponds to placement in dropdown menu'''
    NORMAL = 0
    SUPER = 1
    HYPER = 2
    MASTER = 3


class ContestMode(BotMode):

    ''' Frames to wait after pressing UP/DOWN in menu '''
    MENU_DIRECTION_DELAY = 2

    @staticmethod
    def name() -> str:
        return "Contest"

    @staticmethod
    def is_selectable() -> bool:
        current_location = get_map_data_for_current_position()
        if current_location is None:
            return False


        targeted_tile = get_player_avatar().map_location_in_front
        return targeted_tile in MapRSE.LILYCOVE_CITY_CONTEST_LOBBY and targeted_tile.local_position == (
            14,
            3,
        )

        return True

    def __init__(self):
        super().__init__()
        # self._controller = PokecenterLoopController()

    def on_battle_started(self, encounter: EncounterInfo | None) -> BattleAction | BattleStrategy | None:
        return self._controller.on_battle_started(encounter)

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        return self._controller.on_battle_ended()

    def on_whiteout(self) -> bool:
        return self._controller.on_whiteout()

    def contest_type_to_choice_number(self, contest_type: str) -> ContestTypeChoice:
        match contest_type:
            case 'Coolness':
                return ContestTypeChoice.COOLNESS
            case 'Beauty':
                return ContestTypeChoice.BEAUTY
            case 'Cuteness':
                return ContestTypeChoice.CUTENESS
            case 'Smartness':
                return ContestTypeChoice.SMARTNESS
            case 'Toughness':
                return ContestTypeChoice.TOUGHNESS
            case _:
                raise BotModeError(f"Invalid contest type: {contest_type}")

    def contest_rank_to_choice_number(self, contest_rank: str) -> ContestRankChoice:
        match contest_rank:
            case 'Normal':
                return ContestRankChoice.NORMAL
            case 'Super':
                return ContestRankChoice.SUPER
            case 'Hyper':
                return ContestRankChoice.HYPER
            case 'Master':
                return ContestRankChoice.MASTER
            case _:
                raise BotModeError(f"Invalid contest rank: {contest_rank}")

    def select_move(self, round: int) -> None:
        # The move selection cursor does not reset between rounds

        if round == 0:
            # Default move is move 1. Continue
            context.emulator.press_button("A")
        elif round == 1 or round == 3:
            # Selected move is move 1. Move down to move 2
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(5)
            context.emulator.press_button("A")
        elif round == 2:
            # Selected move is move 2. Move back to move 1
            context.emulator.press_button("Up")
            yield from wait_for_n_frames(5)
            context.emulator.press_button("A")
        elif round == 4:
            # Selected move is move 2. Do move 3
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(5)
            context.emulator.press_button("A")
        else:
            raise BotModeError("Invalid round given for move selection")

    def _enter_contest(self, contest_type: str, contest_rank: str):
        print(f"Entering {contest_type} Contest")

        # # Talk to lady and get to Contest menu
        yield from wait_until_script_is_active("LilycoveCity_ContestLobby_EventScript_ChooseContestRank", "A")
        # Choose contest rank
        contest_rank_choice_number =self.contest_rank_to_choice_number(contest_rank)
        yield from wait_for_n_frames(60)  # Wait for menu to draw
        for i in range(int(contest_rank_choice_number)):
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(5)

        context.emulator.press_button("A")
        print("Contest rank chosen!")

        # Choose which contest to enter
        contest_type_choice_number = self.contest_type_to_choice_number(contest_type)
        yield from wait_for_n_frames(60)  # Wait for menu to draw
        for i in range(int(contest_type_choice_number)):
            context.emulator.press_button("Down")
            yield from wait_for_n_frames(5)

        context.emulator.press_button("A")
        print("Contest type chosen!")

        yield from wait_for_script_to_start_and_finish("LilycoveCity_ContestLobby_EventScript_ChooseContestMon", "A")
        print("Pokemon chosen")

    def _do_contest(self):
        # Contest consist of 5 rounds
        for i in range(0, 5):
            yield from wait_for_task_to_start_and_finish("Task_DisplayAppealNumberText", "A")
            yield from wait_for_n_frames(5) # needed?
            context.emulator.press_button("A")  # needed? Go to move selection screen
            yield from wait_for_n_frames(5)
            print(f"Move {i}")
            yield from self.select_move(i)

        print("Appeals done. Declaring winner")

        # Winner is declared. Mash A until prizes have been given out
        yield from wait_for_no_script_to_run("A")
        # Wait for exit warp
        print("Got winner. Waiting for warp")
        yield from wait_for_n_frames(60)  # TODO find lower limit (or remove?)
        # Face contest lady to be ready for next run
        context.emulator.press_button("Up")
        print("Facing contest lady. Ready for next round")

    def run(self) -> Generator:
        # Check training spot first to see if it has encounters to not print multi choices windows for nothing

        party_lead_pokemon = get_party().non_eggs[0]
        contest_type = self._ask_for_contest_type(party_lead_pokemon)

        if contest_type is None:
            context.set_manual_mode()
            yield
            return

        contest_rank = self._ask_for_contest_rank(party_lead_pokemon)

        if contest_rank is None:
            context.set_manual_mode()
            yield
            return
        
        while(True):
            yield from self._enter_contest(contest_type, contest_rank)
            yield from self._do_contest()
            if contest_rank != "Master":
                # TODO check if won or not before exiting
                print("Won non-master contest. Exiting")
                break

        # One run before all is tested
        print("Done!")
        context.set_manual_mode()
        yield
        return

    def _get_party_lead(self):
        for index, pokemon in enumerate(get_party()):
            if not pokemon.is_egg:
                return pokemon, index
        raise BotModeError("No valid Pokémon found in the party.")

    def _ask_for_contest_type(self, party_lead_pokemon):
        return ask_for_choice(
            [
                Selection("Coolness", get_sprites_path() / "items" / "Red Scarf.png"),
                Selection("Beauty", get_sprites_path() / "items" / "Blue Scarf.png"),
                Selection("Cuteness", get_sprites_path() / "items" / "Pink Scarf.png"),
                Selection("Smartness", get_sprites_path() / "items" / "Green Scarf.png"),
                Selection("Toughmess", get_sprites_path() / "items" / "Yellow Scarf.png"),
            ],
            "What contest to do?",
        )

    def _ask_for_contest_rank(self, party_lead_pokemon):
        return ask_for_choice(
            [
                Selection("Normal", get_sprites_path() / "items" / "None.png"),
                Selection("Super", get_sprites_path() / "items" / "None.png"),
                Selection("Hyper", get_sprites_path() / "items" / "None.png"),
                Selection("Master", get_sprites_path() / "items" / "None.png"),
            ],
            "What contest to do?",
        )

