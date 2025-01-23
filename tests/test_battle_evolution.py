from tests.utility import BotTestCase, with_save_state, with_frame_timeout


class TestBattleEvolution(BotTestCase):
    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_evolving.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_evolving.ss1",
            "firered/in_tall_grass_before_levelling_up_and_evolving.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_stops_evolution(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(stop_evolution=True)

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_species = get_party()[0].species_name_for_stats
        previous_level = get_party()[0].level
        yield from spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None)
        new_species = get_party()[0].species_name_for_stats
        new_level = get_party()[0].level
        self.assertGreater(new_level, previous_level)
        self.assertEqual(previous_species, new_species)

    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_evolving.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_evolving.ss1",
            "firered/in_tall_grass_before_levelling_up_and_evolving.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_allows_evolution(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(stop_evolution=False)

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_species = get_party()[0].species_name_for_stats
        previous_level = get_party()[0].level
        yield from spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None)
        new_species = get_party()[0].species_name_for_stats
        new_level = get_party()[0].level
        self.assertGreater(new_level, previous_level)
        self.assertNotEqual(previous_species, new_species)

    @with_save_state(
        [
            # In the `*_before.ss1`, the _pre-evolution_ will learn a move after levelling up
            # (i.e. learning _before_ the evolution happens.)
            "emerald/in_tall_grass_before_levelling_up_and_evolving_with_new_move_before.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_evolving_with_new_move_before.ss1",
            "firered/in_tall_grass_before_levelling_up_and_evolving_with_new_move_before.ss1",
            # In the `*_after.ss1`, the _evolved Pokémon_ will learn a move (i.e. learning
            # _after_ the evolution happens.)
            "emerald/in_tall_grass_before_levelling_up_and_evolving_with_new_move_afterwards.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_evolving_with_new_move_afterwards.ss1",
            "firered/in_tall_grass_before_levelling_up_and_evolving_with_new_move_afterwards.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_stops_evolution_with_new_move(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(stop_evolution=True, new_move="learn_best")

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_species = get_party()[0].species_name_for_stats
        previous_level = get_party()[0].level
        yield from spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None)
        new_species = get_party()[0].species_name_for_stats
        new_level = get_party()[0].level
        self.assertGreater(new_level, previous_level)
        self.assertEqual(previous_species, new_species)

    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_evolving_with_new_move_before.ss1",
            "emerald/in_tall_grass_before_levelling_up_and_evolving_with_new_move_afterwards.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_evolving_with_new_move_before.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_evolving_with_new_move_afterwards.ss1",
            "firered/in_tall_grass_before_levelling_up_and_evolving_with_new_move_before.ss1",
            "firered/in_tall_grass_before_levelling_up_and_evolving_with_new_move_afterwards.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_allows_evolution_with_new_move(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(stop_evolution=False, new_move="learn_best")

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_species = get_party()[0].species_name_for_stats
        previous_level = get_party()[0].level
        previous_moves = [learned_move.move.name for learned_move in get_party()[0].moves]
        yield from spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None)
        new_species = get_party()[0].species_name_for_stats
        new_level = get_party()[0].level
        new_moves = [learned_move.move.name for learned_move in get_party()[0].moves]
        self.assertGreater(new_level, previous_level)
        self.assertNotEqual(previous_moves, new_moves)
        self.assertNotEqual(previous_species, new_species)
