from typing import Generator

from modules.data.map import MapRSE, MapFRLG
from modules.context import context
from modules.encounter import encounter_pokemon
from modules.save_data import get_save_data
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.pokemon import get_party
from modules.player import get_player_avatar
from ._interface import BotMode, BotModeError
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
    wait_until_task_is_not_active,
    wait_for_task_to_start_and_finish,
    wait_until_event_flag_is_true,
)


def _get_targeted_encounter() -> tuple[tuple[int, int], tuple[int, int], str] | None:
    if context.rom.is_frlg:
        encounters = [
            (MapFRLG.SILPH_CO_F.value, (0, 7), "Lapras"),
            (MapFRLG.SAFFRON_CITY_D.value, (5, 3), "Hitmonlee"),
            (MapFRLG.SAFFRON_CITY_D.value, (7, 3), "Hitmonchan"),
            (MapFRLG.CINNABAR_ISLAND_E.value, (11, 2), "Kanto Fossils"),
            (MapFRLG.CINNABAR_ISLAND_E.value, (13, 4), "Kanto Fossils"),
            (MapFRLG.CELADON_CITY_L.value, (7, 3), "Eevee"),
        ]
    if context.rom.is_rse:
        encounters = [
            (MapRSE.ROUTE_119_B.value, (2, 2), "Castform"),
            (MapRSE.ROUTE_119_B.value, (18, 6), "Castform"),
            (MapRSE.RUSTBORO_CITY_B.value, (14, 8), "Hoenn Fossils"),
            (MapRSE.MOSSDEEP_CITY_H.value, (4, 3), "Beldum"),
        ]

    targeted_tile = get_player_avatar().map_location_in_front
    for entry in encounters:
        if entry[0] == (targeted_tile.map_group, targeted_tile.map_number) and entry[1] == targeted_tile.local_position:
            return entry

    return None


class StaticGiftResetsMode(BotMode):
    @staticmethod
    def name() -> str:
        return "Static Gift Resets"

    @staticmethod
    def is_selectable() -> bool:
        return _get_targeted_encounter() is not None

    def run(self) -> Generator:
        encounter = _get_targeted_encounter()

        save_data = get_save_data()
        if save_data is None:
            raise BotModeError("There is no saved game. Cannot soft reset.")

        if encounter[0] != (save_data.sections[1][4], save_data.sections[1][5]):
            raise BotModeError("The targeted encounter is not in the current map. Cannot soft reset.")

        while context.bot_mode != "Manual":
            yield from soft_reset(mash_random_keys=True)
            yield from wait_for_unique_rng_value()

            if len(get_party()) >= 6:
                raise BotModeError("This mode requires at least one empty party slot, but your party is full.")

            # spam A through chat boxes
            if context.rom.is_frlg:
                yield from wait_until_task_is_active("Task_DrawFieldMessageBox", "A")
                yield from wait_until_task_is_not_active("Task_DrawFieldMessageBox", "B")
            if context.rom.is_emerald:
                yield from wait_until_task_is_active("Task_DrawFieldMessage", "A")
                yield from wait_until_task_is_not_active("Task_DrawFieldMessage", "B")

            # accept the pokemon
            if encounter[2] in ["Beldum", "Hitmonchan", "Hitmonlee"]:
                if context.rom.is_rse:
                    yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "A")
                    yield from wait_for_task_to_start_and_finish("Task_Fanfare", "B")
                if context.rom.is_frlg:
                    yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "A")
                    yield from wait_for_task_to_start_and_finish("Task_Fanfare", "B")
                    yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessageBox", "B")

            # don't rename pokemon
            if context.rom.is_frlg:
                if encounter[2] in ["Hitmonchan", "Hitmonlee"]:
                    yield from wait_until_event_flag_is_true("GOT_HITMON_FROM_DOJO", "B")
                yield from wait_for_task_to_start_and_finish("Task_YesNoMenu_HandleInput", "B")
            if context.rom.is_emerald:
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "B")
                yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "B")

            # extra check for lapras and castform and clear extra message boxes
            if encounter[2] == "Lapras":
                yield from wait_until_event_flag_is_true("GOT_LAPRAS_FROM_SILPH", "B")
            if encounter[2] == "Castform":
                yield from wait_until_event_flag_is_true("RECEIVED_CASTFORM", "B")

            # If the respective 'cheat' is enabled, check the Pokemon immediately
            # instead of 'genuinely' looking at the summary screen
            if context.config.cheats.fast_check_starters:
                encounter_pokemon(get_party()[len(get_party()) - 1])
                continue
            else:
                # Navigate to the summary screen to check for shininess
                yield from StartMenuNavigator("POKEMON").step()
                yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

                encounter_pokemon(get_party()[len(get_party()) - 1])
