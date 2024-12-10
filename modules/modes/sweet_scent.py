from typing import Generator

from modules.battle_state import BattleOutcome
from modules.context import context
from modules.menu_parsers import CursorOptionEmerald, CursorOptionFRLG, CursorOptionRS
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon_party import get_party
from ._asserts import assert_player_has_poke_balls, assert_has_pokemon_with_any_move
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

        assert_has_pokemon_with_any_move(
            ["Sweet Scent"], "None of your party Pokémon know the move Sweet Scent. Please teach it to someone."
        )

        yield from StartMenuNavigator("POKEMON").step()

        move_pokemon = get_party().first_pokemon_with_move("Sweet Scent")

        cursor = None
        if context.rom.is_emerald:
            cursor = CursorOptionEmerald
        elif context.rom.is_rs:
            cursor = CursorOptionRS
        elif context.rom.is_frlg:
            cursor = CursorOptionFRLG

        yield from PokemonPartyMenuNavigator(move_pokemon.index, "", cursor.SWEET_SCENT).step()
