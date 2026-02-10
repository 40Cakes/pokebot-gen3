from typing import Generator, TYPE_CHECKING

from modules.context import context
from modules.map_data import MapRSE, MapFRLG
from modules.modes import BotMode, BattleAction, BotModeError
from modules.player import get_player, get_player_avatar, get_player_location
from modules.pokemon_party import get_party
from modules.roamer import get_roamer
from ._asserts import (
    assert_player_has_poke_balls,
    assert_boxes_or_party_can_fit_pokemon,
)
from .util import (
    walk_one_tile,
    navigate_to,
    register_key_item,
    mount_bicycle,
    unmount_bicycle,
    repel_is_active,
    apply_repel,
    ensure_facing_direction,
    RanOutOfRepels,
)
from ..battle_state import battle_is_active
from ..items import get_item_bag, get_item_by_name
from ..map import get_map_data_for_current_position

if TYPE_CHECKING:
    from modules.encounter import EncounterInfo


class RoamerReencounterMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Roamer (Re-Encounter)"

    @staticmethod
    def is_selectable() -> bool:
        if context.rom.is_emerald:
            allowed_maps = (
                MapRSE.ROUTE110,
                MapRSE.SLATEPORT_CITY,
                MapRSE.SLATEPORT_CITY_BATTLE_TENT_LOBBY,
            )
        elif context.rom.is_rs:
            allowed_maps = (
                MapRSE.ROUTE110,
                MapRSE.SLATEPORT_CITY,
                # This is actually the Pokémon Centre, but R/S's map numbers are different here
                MapRSE.SLATEPORT_CITY_HOUSE,
            )
        else:
            allowed_maps = (
                MapFRLG.ROUTE1,
                MapFRLG.PALLET_TOWN,
                MapFRLG.PALLET_TOWN_RIVALS_HOUSE,
            )

        return get_roamer() is not None and get_player_avatar().map_group_and_number in allowed_maps

    def on_battle_started(self, encounter: "EncounterInfo | None") -> BattleAction:
        context.set_manual_mode()
        return BattleAction.CustomAction

    def on_repel_effect_ended(self) -> Generator:
        try:
            yield from apply_repel()
        except RanOutOfRepels:
            context.message = "Player ran out of Repel."
            context.set_manual_mode()

    def run(self) -> Generator:
        if get_roamer() is None:
            raise BotModeError("The Roamer is not currently roaming.")

        min_level = 6 if context.rom.is_frlg else 14
        max_level = 50 if context.rom.is_frlg else 40
        first_pokemon = get_party().first_non_fainted
        print(max_level, first_pokemon.level, min_level)
        if first_pokemon.level > max_level or first_pokemon.level < min_level:
            raise BotModeError(
                f"The first non-fainted Pokémon in your party must have a level between {min_level} and {max_level}. Yours is {first_pokemon.level}."
            )

        assert_player_has_poke_balls()
        assert_boxes_or_party_can_fit_pokemon()

        if get_item_bag().number_of_repels == 0:
            raise BotModeError("You do not have any repels in your item bag. Go and get some first!")

        mach_bike = get_item_by_name("Bicycle" if context.rom.is_frlg else "Mach Bike")
        if get_player().registered_item is not mach_bike and get_item_bag().quantity_of(mach_bike) > 0:
            yield from register_key_item(mach_bike)
        using_bike = get_player().registered_item is mach_bike

        has_good_ability = get_party().non_eggs[0].ability.name in ("Illuminate", "Arena Trap")

        if not repel_is_active():
            yield from apply_repel()

        is_rse = context.rom.is_rse
        is_frlg = context.rom.is_frlg
        while not battle_is_active():
            player_map, player_coordinates = get_player_location()

            if is_rse and player_map is MapRSE.SLATEPORT_CITY_BATTLE_TENT_LOBBY:
                if player_coordinates in ((6, 9), (7, 9)):
                    yield from walk_one_tile("Down")
                else:
                    yield from navigate_to(MapRSE.SLATEPORT_CITY_BATTLE_TENT_LOBBY, (6, 9))

            elif is_rse and player_map is MapRSE.SLATEPORT_CITY_HOUSE:
                if player_coordinates in ((6, 8), (7, 8)):
                    yield from walk_one_tile("Down")
                else:
                    yield from navigate_to(MapRSE.SLATEPORT_CITY_HOUSE, (6, 8))

            elif is_rse and player_map is MapRSE.SLATEPORT_CITY:
                if using_bike:
                    yield from mount_bicycle()
                    yield from navigate_to(MapRSE.ROUTE110, (13, 98), avoid_encounters=False)
                    yield from unmount_bicycle()
                    context.emulator.hold_button("B")
                    yield from walk_one_tile("Up")
                    context.emulator.release_button("B")
                else:
                    yield from navigate_to(MapRSE.ROUTE110, (14, 97), run=True, avoid_encounters=False)

            elif is_rse and player_map is MapRSE.ROUTE110:
                if not get_map_data_for_current_position().has_encounters:
                    yield from navigate_to(MapRSE.ROUTE110, (14, 97), run=True, avoid_encounters=False)

                directions = ["Down", "Right", "Up", "Left"]
                for index in range(42 if has_good_ability else 62):
                    yield from ensure_facing_direction(directions[index % 4])

                if using_bike:
                    yield from mount_bicycle()

                # In R/S, there is an NPC that wanders randomly and can get in the way of the
                # player's path. That's why in these games, we instead go into the Pokémon Center
                # to achieve the required map change.
                destination_coordinates = (10, 12) if context.rom.is_emerald else (19, 19)
                yield from navigate_to(MapRSE.SLATEPORT_CITY, destination_coordinates, avoid_encounters=False)

            elif is_frlg and player_map is MapFRLG.PALLET_TOWN_RIVALS_HOUSE:
                if player_coordinates == (4, 8):
                    yield from walk_one_tile("Down")
                else:
                    yield from navigate_to(MapFRLG.PALLET_TOWN_RIVALS_HOUSE, (4, 8))

            elif is_frlg and player_map is MapFRLG.PALLET_TOWN:
                if using_bike:
                    yield from mount_bicycle()
                yield from navigate_to(MapFRLG.ROUTE1, (12, 39), avoid_encounters=False)
                yield from unmount_bicycle()

            elif is_frlg and player_map is MapFRLG.ROUTE1:
                if not get_map_data_for_current_position().has_encounters:
                    yield from navigate_to(MapFRLG.ROUTE1, (12, 39), run=True, avoid_encounters=False)

                directions = ["Down", "Right", "Up", "Left"]
                for index in range(18 if has_good_ability else 38):
                    yield from ensure_facing_direction(directions[index % 4])

                if using_bike:
                    yield from mount_bicycle()
                yield from navigate_to(MapFRLG.PALLET_TOWN, (15, 7), avoid_encounters=False)

            else:
                raise BotModeError("Player is on an unexpected map.")

        context.set_manual_mode()
