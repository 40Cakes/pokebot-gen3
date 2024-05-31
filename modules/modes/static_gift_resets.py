from typing import Generator

from modules.console import console
from modules.context import context
from modules.encounter import handle_encounter
from modules.map import get_map_data
from modules.map_data import MapFRLG, MapRSE
from modules.map_path import calculate_path
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon import get_party, Pokemon
from modules.save_data import get_save_data
from ._asserts import (
    assert_save_game_exists,
    assert_registered_item,
    assert_empty_slot_in_party,
)
from ._interface import BotMode, BotModeError
from .util import (
    follow_waypoints,
    navigate_to,
    soft_reset,
    wait_for_player_avatar_to_be_controllable,
    wait_for_script_to_start_and_finish,
    wait_for_task_to_start_and_finish,
    wait_for_unique_rng_value,
    wait_until_event_flag_is_true,
    wait_until_task_is_active,
    wait_until_task_is_not_active,
)


def _get_targeted_encounter() -> tuple[MapFRLG | MapRSE, tuple[int, int], str] | None:
    if context.rom.is_frlg:
        encounters = [
            (MapFRLG.SILPH_CO_7F, (0, 7), "Lapras"),
            (MapFRLG.SAFFRON_CITY_DOJO, (5, 3), "Hitmonlee"),
            (MapFRLG.SAFFRON_CITY_DOJO, (7, 3), "Hitmonchan"),
            (MapFRLG.CINNABAR_ISLAND_POKEMON_LAB_EXPERIMENT_ROOM, (11, 2), "Kanto Fossils"),
            (MapFRLG.CINNABAR_ISLAND_POKEMON_LAB_EXPERIMENT_ROOM, (13, 4), "Kanto Fossils"),
            (MapFRLG.CELADON_CITY_CONDOMINIUMS_ROOF_ROOM, (7, 3), "Eevee"),
            (MapFRLG.ROUTE4_POKEMON_CENTER_1F, (1, 3), "Magikarp"),
            (MapFRLG.FIVE_ISLAND_WATER_LABYRINTH, (14, 11), "Togepi"),
        ]
    else:
        encounters = [
            (MapRSE.ROUTE119_WEATHER_INSTITUTE_2F, (2, 2), "Castform"),
            (MapRSE.ROUTE119_WEATHER_INSTITUTE_2F, (18, 6), "Castform"),
            (MapRSE.RUSTBORO_CITY_DEVON_CORP_2F, (14, 8), "Hoenn Fossils"),
            (MapRSE.MOSSDEEP_CITY_STEVENS_HOUSE, (4, 3), "Beldum"),
            (MapRSE.LAVARIDGE_TOWN, (4, 7), "Wynaut"),
        ]

    targeted_tile = get_player_avatar().map_location_in_front
    return next(
        (
            entry
            for entry in encounters
            if entry[0] == (targeted_tile.map_group, targeted_tile.map_number)
            and entry[1] == targeted_tile.local_position
        ),
        None,
    )


class StaticGiftResetsMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Static Gift Resets"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    def __init__(self):
        super().__init__()
        self._egg_has_hatched = False

    def on_egg_hatched(self, pokemon: "Pokemon", party_index: int) -> None:
        # The user could start this mode with another egg already in their party (from daycare)
        # so in order to make sure that it was Togepi/Wynaut that hatched, we verify that the
        # egg is in the last slot of the party -- since the egg was picked up at the start of
        # the mode, it's guaranteed to be in that slot.
        if party_index == len(get_party()) - 1:
            self._egg_has_hatched = True

    def run(self) -> Generator:
        encounter = _get_targeted_encounter()
        if encounter is None:
            raise BotModeError("You are not facing the NPC or tile that gives you the gift encounter.")

        assert_save_game_exists("There is no saved game. Cannot soft reset.")

        save_data = get_save_data()
        if encounter[0] != (save_data.sections[1][4], save_data.sections[1][5]):
            raise BotModeError("The targeted encounter is not in the current map. Cannot soft reset.")

        if encounter[2] == "Wynaut":
            assert_registered_item(
                ["Mach Bike"],
                "You need to register the Mach Bike for the Select button, then save again.",
                check_in_saved_game=True,
            )
            if save_data.get_event_flag("RECEIVED_LAVARIDGE_EGG"):
                raise BotModeError("You have already received the Wynaut egg in your saved game.")
        if encounter[2] in ["Wynaut", "Togepi"] and save_data.get_party()[0].ability.name not in [
            "Flame Body",
            "Magma Armor",
        ]:
            console.print(
                "[bold yellow]WARNING: First Pokemon in party does not have Flame Body / Magma Armor ability."
            )
            console.print("[bold yellow]This will slow down the egg hatching process.")
        if encounter[2] == "Togepi":
            if save_data.get_event_flag("GOT_TOGEPI_EGG"):
                raise BotModeError("You have already received the Togepi egg in your saved game.")
            assert_registered_item(
                ["Bicycle"],
                "You need to register the Bicycle for the Select button, then save again.",
                check_in_saved_game=True,
            )
            if save_data.get_party()[0].friendship < 255:
                raise BotModeError(
                    "The first Pokémon in your party in the saved game must have max friendship (255) to receive the egg."
                )

        assert_empty_slot_in_party(
            "This mode requires at least one empty party slot, but your party is full.", check_in_saved_game=True
        )

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            # Spam A through chat boxes
            if context.rom.is_frlg:
                yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                yield from wait_until_task_is_not_active("Task_DrawFieldMessageBox", "B")
            if context.rom.is_emerald:
                yield from wait_until_task_is_active("Task_DrawFieldMessage", "A")
                yield from wait_until_task_is_not_active("Task_DrawFieldMessage", "B")

            # Accept the Pokémon
            if encounter[2] in ["Beldum", "Hitmonchan", "Hitmonlee", "Magikarp", "Wynaut"]:
                if context.rom.is_rse:
                    yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "A")
                    yield from wait_for_task_to_start_and_finish("Task_Fanfare", "B")
                if context.rom.is_frlg:
                    yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "A")
                    yield from wait_for_task_to_start_and_finish("Task_Fanfare", "B")
                    yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "B")
            if context.rom.is_rs and encounter[2] in ["Hoenn Fossils"]:
                yield from wait_until_event_flag_is_true("RECEIVED_FOSSIL_MON", "A")

            # Don't rename pokemon
            if context.rom.is_frlg and encounter[2] not in ["Togepi"]:
                if encounter[2] in ["Hitmonchan", "Hitmonlee"]:
                    yield from wait_until_event_flag_is_true("GOT_HITMON_FROM_DOJO", "B")
                yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "B")
            elif context.rom.is_frlg and encounter[2] in ["Togepi"]:
                yield from wait_until_event_flag_is_true("GOT_TOGEPI_EGG", "B")
                yield from wait_for_script_to_start_and_finish("Std_MsgboxDefault", "B")
            if context.rom.is_emerald and encounter[2] not in ["Wynaut"]:
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "B")
                yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "B")
            if context.rom.is_rs and encounter[2] in ["Beldum", "Hoenn Fossils"]:
                yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "B")

            # Extra check for lapras and castform and clear extra message boxes
            if encounter[2] == "Lapras":
                yield from wait_until_event_flag_is_true("GOT_LAPRAS_FROM_SILPH", "B")
            if encounter[2] == "Castform":
                yield from wait_until_event_flag_is_true("RECEIVED_CASTFORM", "B")

            def egg_in_party() -> int:
                total_eggs = 0
                for pokemon in get_party():
                    if pokemon.is_egg:
                        total_eggs += 1
                return total_eggs

            def hatch_egg() -> Generator:
                if encounter[2] == "Wynaut":
                    point_a = get_map_data(MapRSE.LAVARIDGE_TOWN, (2, 9))
                    point_b = get_map_data(MapRSE.LAVARIDGE_TOWN, (19, 10))
                elif encounter[2] == "Togepi":
                    point_a = get_map_data(MapFRLG.FIVE_ISLAND_WATER_LABYRINTH, (11, 9))
                    point_b = get_map_data(MapFRLG.FIVE_ISLAND_WATER_LABYRINTH, (17, 13))
                else:
                    raise BotModeError("Unknown encounter type")

                yield from navigate_to(point_a.map_group_and_number, point_a.local_position)
                if not get_player_avatar().is_on_bike:
                    context.emulator.press_button("Select")

                def hatching_path():
                    path_to_point_a = calculate_path(point_b, point_a)
                    path_to_point_b = calculate_path(point_a, point_b)
                    while not self._egg_has_hatched:
                        yield from path_to_point_b
                        yield from path_to_point_a

                yield from follow_waypoints(hatching_path())

            if encounter[2] in ["Wynaut", "Togepi"]:
                yield from wait_until_task_is_not_active("Task_Fanfare", "B")
                while egg_in_party() == 0:
                    context.emulator.press_button("B")
                    yield
                while egg_in_party() > 0:
                    yield from wait_for_player_avatar_to_be_controllable()
                    self._egg_has_hatched = False
                    yield from hatch_egg()

            # Navigate to the summary screen to check for shininess
            yield from StartMenuNavigator("POKEMON").step()
            yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

            handle_encounter(get_party()[len(get_party()) - 1], disable_auto_catch=True)
