from typing import Generator

from modules.data.map import MapRSE, MapFRLG

from modules.console import console
from modules.context import context
from modules.encounter import handle_encounter
from modules.memory import get_event_flag
from modules.menuing import PokemonPartyMenuNavigator, StartMenuNavigator
from modules.player import get_player_avatar
from modules.pokemon import get_party
from modules.save_data import get_save_data
from modules.tasks import get_global_script_context, task_is_active
from ._asserts import (
    assert_registered_item,
)
from ._interface import BotMode, BotModeError
from ._util import (
    soft_reset,
    wait_for_unique_rng_value,
    wait_until_task_is_active,
    wait_until_task_is_not_active,
    wait_for_task_to_start_and_finish,
    wait_until_event_flag_is_true,
    navigate_to,
    wait_for_n_frames,
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
            (MapFRLG.ROUTE_4_A.value, (1, 3), "Magikarp"),
        ]
    else:
        encounters = [
            (MapRSE.ROUTE_119_B.value, (2, 2), "Castform"),
            (MapRSE.ROUTE_119_B.value, (18, 6), "Castform"),
            (MapRSE.RUSTBORO_CITY_B.value, (14, 8), "Hoenn Fossils"),
            (MapRSE.MOSSDEEP_CITY_H.value, (4, 3), "Beldum"),
            (MapRSE.LAVARIDGE_TOWN.value, (4, 7), "Wynaut"),
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

        if encounter[2] == "Wynaut":
            assert_registered_item(
                ["Mach Bike"],
                "You need to register the Mach Bike for the Select button, then save again.",
            )
            if get_event_flag("RECEIVED_LAVARIDGE_EGG"):
                raise BotModeError("You have already received the Wynaut egg.")
            if get_party()[0].ability.name not in ["Flame Body", "Magma Armor"]:
                console.print(
                    "[bold yellow]WARNING: First Pokemon in party does not have Flame Body / Magma Armor ability."
                )
                console.print("[bold yellow]This will slow down the egg hatching process.")

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
            if encounter[2] in ["Beldum", "Hitmonchan", "Hitmonlee", "Magikarp", "Wynaut"]:
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
            if context.rom.is_emerald and encounter[2] not in ["Wynaut"]:
                yield from wait_for_task_to_start_and_finish("Task_DrawFieldMessage", "B")
                yield from wait_for_task_to_start_and_finish("Task_HandleYesNoInput", "B")

            # extra check for lapras and castform and clear extra message boxes
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
                if not get_player_avatar().is_on_bike:
                    context.emulator.press_button("Select")
                yield from navigate_to(3, 10, False)
                yield from navigate_to(16, 10, False)

            if encounter[2] == "Wynaut":
                yield from wait_until_task_is_not_active("Task_Fanfare", "B")
                while egg_in_party() == 0:
                    context.emulator.press_button("B")
                    yield
                while egg_in_party() > 0:
                    yield from wait_for_n_frames(20)
                    for _ in hatch_egg():
                        script_ctx = get_global_script_context()
                        if "EventScript_EggHatch" in script_ctx.stack:
                            if not task_is_active("Task_WaitForFadeAndEnableScriptCtx"):
                                yield from wait_for_task_to_start_and_finish("Task_WaitForFadeAndEnableScriptCtx", "B")
                        yield

            # Navigate to the summary screen to check for shininess
            yield from StartMenuNavigator("POKEMON").step()
            yield from PokemonPartyMenuNavigator(len(get_party()) - 1, "summary").step()

            handle_encounter(get_party()[len(get_party()) - 1], disable_auto_catch=True)
