from tests.utility import BotTestCase, rom_in_language, switch_to_rom, with_master_test_states


def read_all_wild_encounters() -> dict:
    """Every map's wild encounter tables, read from the ROM."""
    from modules.context import context
    from modules.map import get_wild_encounters_for_map
    from modules.memory import read_symbol

    headers = read_symbol("gWildMonHeaders")
    result = {}
    for offset in range(0, len(headers), 20):
        if headers[offset] == 0xFF:
            break
        map_group_and_number = (headers[offset], headers[offset + 1])
        result[map_group_and_number] = get_wild_encounters_for_map(*map_group_and_number).to_dict()
    assert len(result) > 0, f"No wild encounter table found in {context.rom.game_name}."
    return result


class TestWildEncounters(BotTestCase):
    @with_master_test_states("Spin*-Everywhere.ss1")
    def test_wild_encounter_tables_match_english_in_all_languages(self):
        from modules.roms import ROMLanguage

        tables = read_all_wild_encounters()
        if self.rom.language is not ROMLanguage.English:
            game_name = self.rom.game_name
            switch_to_rom(rom_in_language(ROMLanguage.English))
            english_tables = read_all_wild_encounters()
            self.assertEqual(english_tables.keys(), tables.keys(), f"{game_name} has wild encounters on other maps.")
            for map_group_and_number, english_table in english_tables.items():
                self.assertEqual(
                    english_table,
                    tables[map_group_and_number],
                    f"{game_name} has other wild encounters on map {map_group_and_number}.",
                )
        yield
