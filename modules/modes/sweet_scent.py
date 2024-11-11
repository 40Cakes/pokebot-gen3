from asyncio import log
from typing import Generator

from modules.context import context
from modules.menu_parsers import CursorOptionEmerald, CursorOptionFRLG, CursorOptionRS
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.modes._asserts import assert_has_pokemon_with_move
from modules.player import get_player_avatar
from modules.battle_state import BattleOutcome
from modules.pokemon import get_move_by_name, get_party
from ._asserts import assert_player_has_poke_balls
from ._interface import BotMode


class SweetScentMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Sweet Scent"

    @staticmethod
    def is_selectable() -> bool:
        return get_player_avatar().map_location.has_encounters

    def on_battle_ended(self, outcome: "BattleOutcome") -> None:
        if not outcome == BattleOutcome.Lost:
            assert_player_has_poke_balls()

    def run(self) -> Generator:
        assert_player_has_poke_balls()

        assert_has_pokemon_with_move(
            "Sweet Scent", "None of your party Pokémon know the move Sweet Scent. Please teach it to someone."
        )

        yield from StartMenuNavigator("POKEMON").step()

        move_pokemon = None
        move_wanted = get_move_by_name("Sweet Scent")
        for index in range(len(get_party())):
            for learned_move in get_party()[index].moves:
                if learned_move is not None and learned_move.move == move_wanted:
                    move_pokemon = index
                    break

        cursor = None
        if context.rom.is_emerald:
            cursor = CursorOptionEmerald
        elif context.rom.is_rs:
            cursor = CursorOptionRS
        elif context.rom.is_frlg:
            cursor = CursorOptionFRLG

        yield from PokemonPartyMenuNavigator(move_pokemon, "", cursor.SWEET_SCENT).step()
