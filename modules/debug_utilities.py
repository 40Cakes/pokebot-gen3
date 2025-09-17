import random
import struct
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy

from modules.context import context
from modules.game import _event_flags, _event_vars, encode_string
from modules.items import Item, ItemSlot, get_item_bag, _items_by_index, ItemPocket, get_item_by_name
from modules.map import get_encounter_affecting_abilities
from modules.memory import (
    get_event_flag,
    get_event_var,
    set_event_flag,
    set_event_var,
    write_symbol,
    write_to_save_block,
    pack_uint8,
    pack_uint16,
    pack_uint32,
    decrypt16,
    decrypt32,
    get_save_block,
    unpack_uint16,
    unpack_uint32,
)
from modules.player import get_player
from modules.pokemon import (
    Pokemon,
    Species,
    Nature,
    Move,
    LearnedMove,
    StatsValues,
    StatusCondition,
    POKEMON_DATA_SUBSTRUCTS_ORDER,
    get_species_by_name,
    get_nature_by_index,
    get_move_by_name,
    get_nature_by_name,
    get_species_by_national_dex,
    LearnedMove,
    ContestConditions,
)
from modules.pokemon_party import get_party
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
    species: Species,
    level: int,
    original_pokemon: Pokemon | None = None,
    is_egg: bool = False,
    is_shiny: bool = False,
    gender: Literal["male", "female"] | None = None,
    nickname: str = "",
    held_item: Item | None = None,
    has_second_ability: bool = False,
    nature: Nature | None = None,
    experience: int | None = None,
    friendship: int = 70,
    moves: list[LearnedMove] | None = None,
    ivs: StatsValues | None = None,
    evs: StatsValues | None = None,
    current_hp: int | None = None,
    status_condition: StatusCondition = StatusCondition.Healthy,
    contest_conditions: ContestConditions | None = None,
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
    if ivs is None:
        ivs = StatsValues(15, 15, 15, 15, 15, 15) if original_pokemon is None else original_pokemon.ivs

    if evs is None:
        evs = StatsValues(0, 0, 0, 0, 0, 0) if original_pokemon is None else original_pokemon.evs

    if gender is None and species.gender_ratio != 255:
        if original_pokemon is None:
            gender = "male" if species.gender_ratio <= 127 else "female"
        else:
            gender = original_pokemon.gender

    if nature is None:
        nature = get_nature_by_index(0) if original_pokemon is None else original_pokemon.nature

    if level == 100:
        experience = species.level_up_type.get_experience_needed_for_level(100)
    elif experience is None:
        experience = (
            species.level_up_type.get_experience_needed_for_level(level)
            if original_pokemon is None
            else original_pokemon.total_exp
        )
    else:
        min_exp = species.level_up_type.get_experience_needed_for_level(level)
        max_exp = species.level_up_type.get_experience_needed_for_level(level + 1) - 1
        experience = max(min_exp, min(max_exp, experience))

    if moves is None:
        potential_moves: list[Move] = [entry.move for entry in species.learnset.level_up if entry.level <= level]
        moves = [LearnedMove.create(move) for move in potential_moves[-4:]]
    moves = moves[:4]

    max_hp = StatsValues.calculate(species, ivs, evs, nature, level).hp
    if current_hp is None:
        current_hp = max_hp if original_pokemon is None else original_pokemon.current_hp
    current_hp = min(current_hp, max_hp)

    iv_egg_ability = (
        ivs.hp
        | (ivs.attack << 5)
        | (ivs.defence << 10)
        | (ivs.speed << 15)
        | (ivs.special_attack << 20)
        | (ivs.special_defence << 25)
    )
    if has_second_ability and len(species.abilities) > 1:
        iv_egg_ability |= 1 << 31
    if is_egg:
        iv_egg_ability |= 1 << 30

    pp_bonuses = (
        ((moves[0].pp_ups if len(moves) > 0 else 0) << 6)
        | ((moves[1].pp_ups if len(moves) > 1 else 0) << 4)
        | ((moves[2].pp_ups if len(moves) > 2 else 0) << 2)
        | ((moves[3].pp_ups if len(moves) > 3 else 0) << 0)
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
            + pack_uint16(player.trainer_id)
            + pack_uint16(player.secret_id)
            # Nickname, gets generated later
            + (b"\x00" * 10)
            + pack_uint8(language)
            + (b"\x06" if is_egg else b"\x02")
            + encode_string(player.name).ljust(7, b"\xff")
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
            + pack_uint16(
                # OT gender
                bool(player.gender == "female") << 15
                |
                # Ball
                (get_item_by_name("Premier Ball").index << 11)
                |
                # Game of Origin
                (game_number << 7)
                |
                # Met at Level
                level
            )
            + (b"\x00" * 4)
            + pack_uint32(0 if species.name not in ("Mew", "Deoxys") else 1 << 31)
            + (b"\x00" * 20)
        )
    else:
        decrypted_data = original_pokemon._decrypted_data

    if is_egg and friendship > species.egg_cycles:
        friendship = species.egg_cycles

    contest_conditions_data = decrypted_data[62:68]
    if contest_conditions is not None:
        contest_conditions_data = (
            pack_uint8(contest_conditions.coolness)
            + pack_uint8(contest_conditions.beauty)
            + pack_uint8(contest_conditions.cuteness)
            + pack_uint8(contest_conditions.smartness)
            + pack_uint8(contest_conditions.toughness)
            + pack_uint8(contest_conditions.feel)
        )

    data_to_encrypt = (
        pack_uint16(species.index)
        + pack_uint16(held_item.index if held_item is not None else 0)
        + pack_uint32(experience)
        + pack_uint8(pp_bonuses)
        + pack_uint8(friendship)
        + decrypted_data[42:44]
        + pack_uint16(moves[0].move.index if len(moves) > 0 else 0)
        + pack_uint16(moves[1].move.index if len(moves) > 1 else 0)
        + pack_uint16(moves[2].move.index if len(moves) > 2 else 0)
        + pack_uint16(moves[3].move.index if len(moves) > 3 else 0)
        + pack_uint8(moves[0].pp if len(moves) > 0 else 0)
        + pack_uint8(moves[1].pp if len(moves) > 1 else 0)
        + pack_uint8(moves[2].pp if len(moves) > 2 else 0)
        + pack_uint8(moves[3].pp if len(moves) > 3 else 0)
        + pack_uint8(evs.hp)
        + pack_uint8(evs.attack)
        + pack_uint8(evs.defence)
        + pack_uint8(evs.speed)
        + pack_uint8(evs.special_attack)
        + pack_uint8(evs.special_defence)
        + contest_conditions_data
        + decrypted_data[68:72]
        + pack_uint32(iv_egg_ability)
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
        pack_uint32(personality_value)
        + original_pokemon.data[4:8]
        + encoded_nickname.ljust(10, b"\xff")
        + original_pokemon.data[18:19]
        + (b"\x06" if is_egg else b"\x02")
        + original_pokemon.data[20:28]
        + pack_uint16(sum(struct.unpack("<24H", data_to_encrypt)) & 0xFFFF)
        + original_pokemon.data[30:32]
        + data_to_encrypt
        + pack_uint8(status_condition.to_bitfield())
        + original_pokemon.data[81:84]
        + pack_uint8(level)
        + original_pokemon.data[85:86]
        + pack_uint16(current_hp)
        + pack_uint16(stats.hp)
        + pack_uint16(stats.attack)
        + pack_uint16(stats.defence)
        + pack_uint16(stats.speed)
        + pack_uint16(stats.special_attack)
        + pack_uint16(stats.special_defence)
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
    gets passed fewer than 6 Pokémon, the remaining slots will stay empty.

    :param party_pokemon: List of Pokémon to write to game memory.
    """
    if len(party_pokemon) == 0:
        raise ValueError("Cannot write an empty party.")
    if len(party_pokemon) > 6:
        raise ValueError(f"A party can only consist of 6 Pokémon, {len(party_pokemon)} given instead.")

    write_symbol("gPlayerPartyCount", pack_uint8(len(party_pokemon)))
    new_party_data = b""
    for pokemon in party_pokemon:
        new_party_data += pokemon.data
    write_symbol("gPlayerParty", new_party_data.ljust(600, b"\x00"))


def debug_write_item_bag(
    items: list[ItemSlot],
    key_items: list[ItemSlot],
    poke_balls: list[ItemSlot],
    tms_hms: list[ItemSlot],
    berries: list[ItemSlot],
) -> None:
    bags: dict[str, tuple[list[ItemSlot], int]] = {
        "items": (items, ItemPocket.Items.capacity),
        "key_items": (key_items, ItemPocket.KeyItems.capacity),
        "poke_balls": (poke_balls, ItemPocket.PokeBalls.capacity),
        "tms_hms": (tms_hms, ItemPocket.TmsAndHms.capacity),
        "berries": (berries, ItemPocket.Berries.capacity),
    }
    item_bag_offset = 0x310 if context.rom.is_frlg else 0x560
    registered_item_offset = 0x296 if context.rom.is_frlg else 0x496

    data = b""
    for bag_name in bags:
        bag, count = bags[bag_name]
        if len(bag) > count:
            raise ValueError(f"Bag '{bag}' only fits {count} items, but {len(bag)} were provided.")
        bag_data = b""
        for slot in bag:
            bag_data += pack_uint16(slot.item.index)
            bag_data += pack_uint16(decrypt16(slot.quantity))
        while len(bag_data) < count * 4:
            bag_data += pack_uint16(0)
            bag_data += pack_uint16(decrypt16(0))
        data += bag_data

    write_to_save_block(data, 1, item_bag_offset)
    write_symbol("gLoadedSaveData", data)

    registered_item = unpack_uint16(get_save_block(1, registered_item_offset, 2))
    if registered_item != 0:
        still_owns_key_item = False
        for slot in key_items:
            if slot.item.index == registered_item:
                still_owns_key_item = True
                break
        if not still_owns_key_item:
            write_to_save_block(pack_uint16(0), 1, registered_item_offset)


def debug_give_test_item_pack(rse_bicycle: Literal["Acro Bike", "Mach Bike"] = "Acro Bike") -> None:
    all_the_balls = []
    all_the_tms_hms = []
    all_the_berries = []
    stack_size = 999 if context.rom.is_frlg else 99
    for item in _items_by_index:
        if item.index == 0 or item.name.startswith("?"):
            continue
        if item.pocket is ItemPocket.PokeBalls:
            all_the_balls.append(ItemSlot(item, stack_size))
        elif item.pocket is ItemPocket.TmsAndHms:
            if item.name != "HM08" or context.rom.is_rse:
                all_the_tms_hms.append(ItemSlot(item, 1))
        elif item.pocket is ItemPocket.Berries:
            all_the_berries.append(ItemSlot(item, 999))

    if context.rom.is_rse:
        key_item_names = [
            rse_bicycle,
            "Basement Key",
            "Devon Scope",
            "Eon Ticket",
            "Go-Goggles",
            "Pokéblock Case",
            "Rm. 1 Key",
            "Rm. 2 Key",
            "Rm. 4 Key",
            "Rm. 6 Key",
            "Scanner",
            "Soot Sack",
            "Wailmer Pail",
        ]

        if context.rom.is_rs:
            key_item_names.append("Contest Pass")
        else:
            key_item_names.append("Magma Emblem")
            key_item_names.append("Old Sea Map")
    else:
        key_item_names = [
            "Berry Pouch",
            "Bicycle",
            "Card Key",
            "Fame Checker",
            "Gold Teeth",
            "Lift Key",
            "Poké Flute",
            "Rainbow Pass",
            "Secret Key",
            "Silph Scope",
            "Tea",
            "Teachy TV",
            "TM Case",
            "Town Map",
            "Tri-Pass",
            "VS Seeker",
        ]

    if not context.rom.is_rs:
        key_item_names.append("AuroraTicket")
        key_item_names.append("MysticTicket")
        key_item_names.append("Powder Jar")

    key_item_names.append("Coin Case")
    key_item_names.append("Super Rod")
    key_item_names.append("Good Rod")
    key_item_names.append("Old Rod")
    key_item_names.append("Itemfinder")
    key_item_names.append("S.S. Ticket")

    items_to_give = [
        "Full Restore",
        "Max Revive",
        "Max Elixir",
        "Max Repel",
        "Escape Rope",
        "Rare Candy",
        "White Flute",
    ]
    items = [
        *[ItemSlot(get_item_by_name(name), stack_size) for name in items_to_give],
        *[slot for slot in get_item_bag().items if slot.item.name not in items_to_give],
    ]

    debug_write_item_bag(
        items=items[: ItemPocket.Items.capacity],
        key_items=[ItemSlot(get_item_by_name(name), 1) for name in sorted(key_item_names)],
        poke_balls=all_the_balls,
        tms_hms=all_the_tms_hms,
        berries=all_the_berries,
    )


def debug_get_test_party() -> list[Pokemon]:
    return [
        debug_create_pokemon(
            species=get_species_by_name("Mewtwo"),
            level=100,
            is_shiny=True,
            nickname="Hulk",
            held_item=get_item_by_name("Leftovers"),
            nature=get_nature_by_name("Mild"),
            friendship=255,
            moves=[
                LearnedMove.create(get_move_by_name("Ice Beam"), pp_ups=3),
                LearnedMove.create(get_move_by_name("Thunderbolt"), pp_ups=3),
                LearnedMove.create(get_move_by_name("Psychic"), pp_ups=3),
                LearnedMove.create(get_move_by_name("Fire Blast"), pp_ups=3),
            ],
            ivs=StatsValues(31, 31, 31, 31, 31, 31),
            evs=StatsValues(255, 255, 255, 255, 255, 255),
        ),
        debug_create_pokemon(
            species=get_species_by_name("Lotad"),
            level=100,
            nickname="C",
            held_item=get_item_by_name("Lum Berry"),
            nature=get_nature_by_name("Jolly"),
            friendship=255,
            moves=[
                LearnedMove.create(get_move_by_name("False Swipe"), pp_ups=3),
                LearnedMove.create(get_move_by_name("Spore"), pp_ups=3),
                LearnedMove.create(get_move_by_name("Foresight"), pp_ups=3),
                LearnedMove.create(get_move_by_name("Sweet Scent"), pp_ups=3),
            ],
            ivs=StatsValues(31, 31, 31, 31, 31, 31),
            evs=StatsValues(255, 255, 255, 255, 255, 255),
        ),
        debug_create_pokemon(
            species=get_species_by_name("Magikarp"),
            level=100,
            gender="female",
            nickname="Fly",
            friendship=255,
            moves=[
                LearnedMove.create(get_move_by_name("Fly")),
                LearnedMove.create(get_move_by_name("Strength")),
                LearnedMove.create(get_move_by_name("Rock Smash")),
                LearnedMove.create(get_move_by_name("Flash")),
            ],
            ivs=StatsValues(0, 0, 0, 0, 0, 0),
            evs=StatsValues(0, 0, 0, 0, 0, 0),
        ),
        debug_create_pokemon(
            species=get_species_by_name("Chimecho"),
            level=100,
            gender="male",
            nickname="Swim",
            friendship=255,
            moves=[
                LearnedMove.create(get_move_by_name("Cut")),
                LearnedMove.create(get_move_by_name("Surf")),
                LearnedMove.create(get_move_by_name("Waterfall")),
                LearnedMove.create(get_move_by_name("Dive")),
            ],
            ivs=StatsValues(0, 0, 0, 0, 0, 0),
            evs=StatsValues(0, 0, 0, 0, 0, 0),
        ),
    ]


def debug_give_fainted_first_slot_pokemon_with_special_ability(ability: str) -> None:
    match ability:
        case "Illuminate":
            species = "Staryu" if context.rom.is_frlg else "Volbeat"
        case "Compoundeyes":
            species = "Nincada"
        case "Pressure":
            species = "Absol"
        case "Intimidate":
            species = "Masquerain"
        case "Magnet Pull":
            species = "Nosepass"
        case "Static":
            species = "Electrike"
        case "Sticky Hold":
            species = "Gulpin"
        case "Synchronize":
            species = "Ralts"
        case "Cute Charm":
            species = "Delcatty"
        case "Magma Armor":
            species = "Slugma"
        case _:
            raise ValueError(f"Ability not supported: {ability}")

    party = get_party()
    if not party[0].is_egg and party[0].level == 1 and party[0].ability.name in get_encounter_affecting_abilities():
        # If the first Pokémon looks like it might be another 'special ability' Pokémon, just replace that one.
        remaining_party = party[1:]
    else:
        # Otherwise, move all other party slots one down.
        remaining_party = party[0:5]

    species = get_species_by_name(species)
    debug_write_party(
        [
            debug_create_pokemon(
                species=species,
                level=1,
                nickname="Ability",
                has_second_ability=species.abilities[0].name != ability,
                moves=[
                    LearnedMove.create(get_move_by_name("Explosion")),
                    LearnedMove.create(get_move_by_name("Selfdestruct")),
                    LearnedMove.create(get_move_by_name("Memento")),
                ],
                current_hp=0,
            ),
            *remaining_party,
        ]
    )


def debug_give_max_coins_and_money() -> None:
    if context.rom.is_rse:
        money_offset = 0x490
        coins_offset = 0x494
    else:
        money_offset = 0x290
        coins_offset = 0x294

    # We only give the player 900,000 money even though the maximum
    # is 999,999. This is so they can still earn some and not
    # potentially skip messages.
    write_to_save_block(pack_uint32(decrypt32(900_000)), 1, money_offset)
    write_to_save_block(pack_uint16(decrypt16(9999)), 1, coins_offset)


def debug_write_pokedex(seen_species: list[Species], owned_species: list[Species]) -> None:
    if context.rom.is_emerald:
        seen1_offset = 0x988
        seen2_offset = 0x3B24
    elif context.rom.is_rs:
        seen1_offset = 0x938
        seen2_offset = 0x3A8C
    else:
        seen1_offset = 0x5F8
        seen2_offset = 0x3A18

    seen_data = b""
    owned_data = b""
    needs_national_dex = False
    for byte in range(52):
        value_seen = 0
        value_owned = 0
        for bit in range(8):
            try:
                species = get_species_by_national_dex(byte * 8 + bit + 1)
            except KeyError:
                continue
            if species in seen_species:
                value_seen |= 1 << bit
                if species.national_dex_number <= 251:
                    needs_national_dex = True
            if species in owned_species:
                value_seen |= 1 << bit
                value_owned |= 1 << bit
        seen_data += pack_uint8(value_seen)
        owned_data += pack_uint8(value_owned)

    write_to_save_block(seen_data, 1, offset=seen1_offset)
    write_to_save_block(seen_data, 1, offset=seen2_offset)
    write_to_save_block(owned_data + seen_data, 2, offset=0x28)

    if needs_national_dex:
        write_to_save_block(b"\xda", 2, offset=0x1A)

    if get_species_by_name("Unown") in seen_species:
        unown_personality = unpack_uint32(get_save_block(2, offset=0x1C, size=4))
        if unown_personality == 0:
            write_to_save_block(pack_uint32(random.randint(0, 2**32)), 2, offset=0x1C)

    if get_species_by_name("Spinda") in seen_species:
        spinda_personality = unpack_uint32(get_save_block(2, offset=0x20, size=4))
        if spinda_personality == 0:
            write_to_save_block(pack_uint32(random.randint(0, 2**32)), 2, offset=0x20)
