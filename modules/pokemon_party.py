from typing import Generator

from modules.context import context
from modules.memory import read_symbol, get_event_var
from modules.pokemon import Pokemon, Move, Species
from modules.state_cache import state_cache


class PartyPokemon(Pokemon):
    def __init__(self, data: bytes, index: int):
        super().__init__(data)
        self.index = index


class Party:
    def __init__(self, pokemon: list[PartyPokemon]):
        self._pokemon = pokemon

    def __eq__(self, other):
        if isinstance(other, Party):
            return len(other._pokemon) == len(self._pokemon) and all(
                [other[n] == self[n] for n in range(len(self._pokemon))]
            )
        else:
            return NotImplemented

    def __ne__(self, other):
        if isinstance(other, Party):
            return len(other._pokemon) != len(self._pokemon) or any(
                [other[n] != self[n] for n in range(len(self._pokemon))]
            )
        else:
            return NotImplemented

    def __contains__(self, item):
        if isinstance(item, Pokemon):
            return item in self._pokemon
        elif isinstance(item, Species):
            return any([pokemon.species is item for pokemon in self._pokemon])
        else:
            return NotImplemented

    def __iter__(self) -> Generator[PartyPokemon, None, None]:
        yield from self._pokemon

    def __len__(self) -> int:
        return len(self._pokemon)

    def __getitem__(self, item: int) -> PartyPokemon | None:
        if item not in (0, 1, 2, 3, 4, 5):
            raise KeyError(f"Cannot access a party index of `{item}`.")

        if len(self._pokemon) > item:
            return self._pokemon[item]
        else:
            return None

    @property
    def contains_eggs(self) -> bool:
        return any([pokemon.is_egg for pokemon in self._pokemon])

    @property
    def eggs(self) -> list[Pokemon]:
        return [pokemon for pokemon in self._pokemon if pokemon.is_egg]

    @property
    def non_fainted_pokemon(self) -> list[PartyPokemon]:
        return list(filter(lambda pokemon: not pokemon.is_egg and pokemon.current_hp > 0, self._pokemon))

    @property
    def first_non_fainted(self) -> PartyPokemon:
        return self.non_fainted_pokemon[0]

    def has_pokemon_with_move(self, move: Move | str) -> bool:
        return any(pokemon.knows_move(move) for pokemon in self._pokemon)

    def first_pokemon_with_move(self, move: Move | str) -> PartyPokemon | None:
        for pokemon in self._pokemon:
            if pokemon.knows_move(move):
                return pokemon
        return None

    def to_list(self) -> list[PartyPokemon]:
        return self._pokemon


def get_party_size() -> int:
    return read_symbol("gPlayerPartyCount", size=1)[0]


def get_party() -> Party:
    """
    :return: The player's party of Pokémon.
    """

    if state_cache.party.age_in_frames == 0:
        return state_cache.party.value

    def read_party_pokemon(party_index: int) -> PartyPokemon | None:
        party_pokemon = PartyPokemon(read_symbol("gPlayerParty", offset=party_index * 100, size=100), party_index)
        return party_pokemon if not party_pokemon.is_empty and party_pokemon.is_valid else None

    list_of_pokemon = []
    for index in range(get_party_size()):
        pokemon = read_party_pokemon(index)

        # It's possible for party data to be written while we are trying to read it, in which case
        # the checksum would be wrong and `parse_pokemon()` returns `None`.
        #
        # In order to still get a valid result, we will 'peek' into next frame's memory by
        # (1) advancing the emulation by one frame, (2) reading the memory, (3) restoring the previous
        # frame's state, so we don't mess with frame accuracy.
        if pokemon is None:
            retries = 5
            with context.emulator.peek_frame():
                while retries > 0 and pokemon is None:
                    retries -= 1
                    pokemon = read_party_pokemon(index)
                    if pokemon is None:
                        context.emulator._core.run_frame()
        if pokemon is None:
            if read_symbol("gPlayerParty", offset=index * 100, size=100).count(b"\x00") >= 99:
                continue
            else:
                raise RuntimeError(f"Party Pokémon #{index + 1} was invalid for two frames in a row.")

        list_of_pokemon.append(pokemon)

    party = Party(list_of_pokemon)
    state_cache.party = party

    return party


def get_opponent_party() -> Party | None:
    """
    Gets the opponent's party (obviously only makes sense to check when in a battle.)
    :return: The full party of the opponent, or `None` if there is no valid opponent at the moment.
    """
    if state_cache.opponent.age_in_frames == 0:
        return state_cache.opponent.value

    list_of_pokemon = []
    data = read_symbol("gEnemyParty")
    for index in range(6):
        offset = index * 100
        pokemon = PartyPokemon(data[offset : offset + 100], index)
        if pokemon is None:
            if index == 0:
                return None
            else:
                continue
        list_of_pokemon.append(pokemon)

    party = Party(list_of_pokemon)
    state_cache.opponent = party

    return party


def get_current_repel_level() -> int:
    """
    :return: The minimum level that wild encounters can have, given the current Repel
             state and the level of the first non-fainted Pokémon.
    """
    return get_party().first_non_fainted.level if get_event_var("REPEL_STEP_COUNT") > 0 else 0
