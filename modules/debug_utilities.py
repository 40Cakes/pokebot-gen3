import random
import struct
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy

from modules.context import context
from modules.game import _event_flags, _event_vars, encode_string
from modules.items import Item
from modules.memory import get_event_flag, get_event_var, set_event_flag, set_event_var, write_symbol
from modules.player import get_player
from modules.pokemon import Pokemon, Species, Nature, StatsValues, StatusCondition, POKEMON_DATA_SUBSTRUCTS_ORDER
from modules.roms import ROMLanguage


def export_flags_and_vars(file_path: Path) -> None:
    """
    Exports event flags and event vars into a file, using an INI-like format.
    :param file_path: Path to the target file that flags and vars should be written to.
    """
    with open(file_path, "w") as file:
        file.writelines(
            [
                f"# Exported on {datetime.now().isoformat()}\n",
                f"# Game: {context.rom.game_name} ({context.rom.language.name})\n"
                f"# Profile: {context.profile.path.name}\n"
                "\n[flags]\n",
                *[f"{flag_name} = {'1' if get_event_flag(flag_name) else '0'}\n" for flag_name in _event_flags],
                "\n[vars]\n",
                *[f"{var_name} = {get_event_var(var_name)}\n" for var_name in _event_vars],
            ]
        )


def import_flags_and_vars(file_path: Path) -> int:
    """
    Reads event flags and variables from a file and updates them.
    :param file_path: Path to the file to read from.
    :return: Number of flags and variables that have been set.
    """
    in_flags_section = True
    affected_flags_and_vars = 0
    with open(file_path, "r") as file:
        line_number = 0
        for line in file.readlines():
            line_number += 1
            line = line.split("#", 1)[0].strip()
            if line.lower() == "[flags]":
                in_flags_section = True
                continue
            elif line.lower() == "[vars]":
                in_flags_section = False
                continue
            elif line == "":
                continue
            elif "=" not in line:
                raise SyntaxError(f"Error in line #{line_number}: Missing a `=` character.")
            else:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if in_flags_section:
                    if value == "1":
                        set_event_flag(key, True)
                    elif value == "0":
                        set_event_flag(key, False)
                    else:
                        raise ValueError(
                            f"Error in line #{line_number}: Invalid value '{value}' for event flag '{key}'."
                        )
                else:
                    set_event_var(key, int(value))
                affected_flags_and_vars += 1
    return affected_flags_and_vars


def debug_create_pokemon(
    original_pokemon: Pokemon | None,
    is_egg: bool,
    is_shiny: bool,
    gender: Literal["male", "female"] | None,
    species: Species,
    nickname: str,
    level: int,
    held_item: Item | None,
    has_second_ability: bool,
    nature: Nature,
    experience: int,
    friendship: int,
    moves: list[dict],
    ivs: StatsValues,
    evs: StatsValues,
    current_hp: int,
    status_condition: StatusCondition,
) -> Pokemon:
    """
    Generates a Pokémon data block given a set of criteria.

    This function can receive an 'original Pokémon' from which all the other data
    (such as OT, met location/level, etc.) will be copied. If one is not provided,
    some default values are chosen. (OT will be the current player, and it will be
    set to have been met in the Safari Zone but caught in a Premier Ball. This is
    obviously not possible to achieve legitimately in-game, but this way custom
    Pokémon will be easy to recognise later.)

    If possible, it will retain the Personality Value of the original Pokémon, but
    if some chosen criteria (such as gender, shininess or nature) do not match it,
    a new one will be generated.
    """
    iv_egg_ability = (
        ivs.hp
        | (ivs.attack << 5)
        | (ivs.defence << 10)
        | (ivs.speed << 15)
        | (ivs.special_attack << 20)
        | (ivs.special_defence << 25)
    )
    if has_second_ability:
        iv_egg_ability |= 1 << 31
    if is_egg:
        iv_egg_ability |= 1 << 30

    pp_bonuses = (
        (moves[0]["pp_ups"] << 6) | (moves[1]["pp_ups"] << 4) | (moves[2]["pp_ups"] << 2) | (moves[3]["pp_ups"] << 0)
    )

    if original_pokemon is None or original_pokemon.is_empty:
        player = get_player()

        match context.rom.language:
            case ROMLanguage.Japanese:
                language = 1
            case ROMLanguage.French:
                language = 3
            case ROMLanguage.Italian:
                language = 4
            case ROMLanguage.German:
                language = 5
            case ROMLanguage.Spanish:
                language = 7
            case _:
                language = 2

        original_pokemon = Pokemon(
            # Personality Value, gets generated later
            (b"\x00" * 4)
            + player.trainer_id.to_bytes(2, byteorder="little")
            + player.secret_id.to_bytes(2, byteorder="little")
            # Nickname, gets generated later
            + (b"\x00" * 10)
            + language.to_bytes(1)
            + (b"\x06" if is_egg else b"\x02")
            + encode_string(player.name).ljust(7, b"\xFF")
            + (b"\x00" * 73)
        )

        if context.rom.is_sapphire:
            game_number = 1
        elif context.rom.is_ruby:
            game_number = 2
        elif context.rom.is_emerald:
            game_number = 3
        elif context.rom.is_fr:
            game_number = 4
        elif context.rom.is_lg:
            game_number = 5
        else:
            game_number = 15
        decrypted_data = (
            # First 3 blocks don't matter.
            (b"\x00" * (12 * 3 + 32))
            # Pokérus Status
            + b"\x00"
            # Met Location (0x88 and 0x39 are the Kanto and Hoenn Safari Zones)
            + (b"\x88" if context.rom.is_frlg else b"\x39")
            + (
                # OT gender
                bool(player.gender == "female") << 15
                |
                # Ball (12 = Premier Ball)
                (12 << 11)
                |
                # Game of Origin
                (game_number << 7)
                |
                # Met at Level
                level
            ).to_bytes(2, "little")
            + (b"\x00" * 4)
            + (0 if species.name not in ("Mew", "Deoxys") else 1 << 31).to_bytes(4, "little")
            + (b"\x00" * 20)
        )
    else:
        decrypted_data = original_pokemon._decrypted_data

    if is_egg and friendship > species.egg_cycles:
        friendship = species.egg_cycles

    data_to_encrypt = (
        species.index.to_bytes(2, byteorder="little")
        + (held_item.index if held_item is not None else 0).to_bytes(2, byteorder="little")
        + experience.to_bytes(4, byteorder="little")
        + pp_bonuses.to_bytes(1)
        + friendship.to_bytes(1)
        + decrypted_data[42:44]
        + moves[0]["id"].to_bytes(2, byteorder="little")
        + moves[1]["id"].to_bytes(2, byteorder="little")
        + moves[2]["id"].to_bytes(2, byteorder="little")
        + moves[3]["id"].to_bytes(2, byteorder="little")
        + moves[0]["remaining_pp"].to_bytes(1)
        + moves[1]["remaining_pp"].to_bytes(1)
        + moves[2]["remaining_pp"].to_bytes(1)
        + moves[3]["remaining_pp"].to_bytes(1)
        + evs.hp.to_bytes(1)
        + evs.attack.to_bytes(1)
        + evs.defence.to_bytes(1)
        + evs.speed.to_bytes(1)
        + evs.special_attack.to_bytes(1)
        + evs.special_defence.to_bytes(1)
        + decrypted_data[62:72]
        + iv_egg_ability.to_bytes(4, byteorder="little")
        + decrypted_data[76:80]
    )

    if nickname != "" and nickname != species.name.upper():
        encoded_nickname = encode_string(nickname, ignore_errors=True)
    else:
        encoded_nickname = encode_string(species.localised_names[original_pokemon.language.value].upper())

    if original_pokemon.language is ROMLanguage.Japanese:
        encoded_nickname = encoded_nickname[:5]
    else:
        encoded_nickname = encoded_nickname[:10]

    stats = StatsValues.calculate(species, ivs, evs, nature, level)

    def personality_value_matches_criteria(pv: int) -> bool:
        if pv % 25 != nature.index:
            return False

        if 0 < species.gender_ratio < 254:
            is_male = pv & 0xFF >= species.gender_ratio
            if is_male and gender != "male":
                return False
            if not is_male and gender == "male":
                return False

        shiny_value = (
            original_pokemon.original_trainer.id
            ^ original_pokemon.original_trainer.secret_id
            ^ (pv >> 16)
            ^ (pv & 0xFFFF)
        )
        if is_shiny and shiny_value > 7:
            return False
        if not is_shiny and shiny_value <= 7:
            return False

        return True

    personality_value = original_pokemon.personality_value
    n = 0
    while not personality_value_matches_criteria(personality_value):
        if n > 10_000_000:
            raise RuntimeError("Could not find a suitable PV in time.")
        n += 1
        personality_value = random.randint(0, 2**32)

    data = (
        personality_value.to_bytes(length=4, byteorder="little")
        + original_pokemon.data[4:8]
        + encoded_nickname.ljust(10, b"\xFF")
        + original_pokemon.data[18:19]
        + (b"\x06" if is_egg else b"\x02")
        + original_pokemon.data[20:28]
        + (sum(struct.unpack("<24H", data_to_encrypt)) & 0xFFFF).to_bytes(length=2, byteorder="little")
        + original_pokemon.data[30:32]
        + data_to_encrypt
        + status_condition.to_bitfield().to_bytes(length=1, byteorder="little")
        + original_pokemon.data[81:84]
        + level.to_bytes(length=1, byteorder="little")
        + original_pokemon.data[85:86]
        + current_hp.to_bytes(length=2, byteorder="little")
        + stats.hp.to_bytes(length=2, byteorder="little")
        + stats.attack.to_bytes(length=2, byteorder="little")
        + stats.defence.to_bytes(length=2, byteorder="little")
        + stats.speed.to_bytes(length=2, byteorder="little")
        + stats.special_attack.to_bytes(length=2, byteorder="little")
        + stats.special_defence.to_bytes(length=2, byteorder="little")
    )

    u32le = numpy.dtype("<u4")
    personality_value_bytes = numpy.frombuffer(data, count=1, dtype=u32le)
    original_trainer_id = numpy.frombuffer(data, count=1, offset=4, dtype=u32le)
    key = numpy.repeat(personality_value_bytes ^ original_trainer_id, 3)
    order = POKEMON_DATA_SUBSTRUCTS_ORDER[personality_value % 24]

    encrypted_data = numpy.concatenate(
        [numpy.frombuffer(data, count=3, offset=32 + (order.index(i) * 12), dtype=u32le) ^ key for i in range(4)]
    )

    return Pokemon(data[:32] + encrypted_data.tobytes() + data[80:100])


def debug_write_party(party_pokemon: list[Pokemon]) -> None:
    """
    Replaces the current party in memory by a new list of Pokémon. If this
    gets passed less than 6 Pokémon, the remaining slots will stay empty.

    :param party_pokemon: List of Pokémon to write to game memory.
    """
    if len(party_pokemon) == 0:
        raise ValueError("Cannot write an empty party.")
    if len(party_pokemon) > 6:
        raise ValueError(f"A party can only consist of 6 Pokémon, {len(party_pokemon)} given instead.")

    write_symbol("gPlayerPartyCount", len(party_pokemon).to_bytes(1, byteorder="little"))
    new_party_data = b""
    for pokemon in party_pokemon:
        new_party_data += pokemon.data
    write_symbol("gPlayerParty", new_party_data.ljust(600, b"\x00"))
