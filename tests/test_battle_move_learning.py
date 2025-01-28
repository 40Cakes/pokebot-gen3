from tests.utility import BotTestCase, with_save_state, with_frame_timeout


class TestBattleMoveLearning(BotTestCase):
    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_learning_move_with_empty_slot.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_learning_move_with_empty_slot.ss1",
            "firered/in_tall_grass_before_levelling_up_and_learning_move_with_empty_slot.ss1",
        ]
    )
    @with_frame_timeout(1000)
    def test_it_learns_move_with_empty_slot_available(self):
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_level = get_party()[0].level
        number_of_moves = len([move for move in get_party()[0].moves if move is not None])
        yield from spin(lambda: get_party()[0].level > previous_level)
        new_number_of_moves = len([move for move in get_party()[0].moves if move is not None])
        self.assertGreater(new_number_of_moves, number_of_moves)

    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
            "firered/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_replaces_existing_move(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(new_move="learn_best")

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_moves = [learned_move.move.name for learned_move in get_party()[0].moves if learned_move is not None]
        yield from spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None)
        new_moves = [learned_move.move.name for learned_move in get_party()[0].moves if learned_move is not None]
        self.assertNotEqual(new_moves, previous_moves)

    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
            "firered/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_does_not_learn_new_move(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(new_move="cancel")

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        previous_moves = [learned_move.move.name for learned_move in get_party()[0].moves if learned_move is not None]
        yield from spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None)
        new_moves = [learned_move.move.name for learned_move in get_party()[0].moves if learned_move is not None]
        self.assertEqual(new_moves, previous_moves)

    @with_save_state(
        [
            "emerald/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
            "ruby/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
            "firered/in_tall_grass_before_levelling_up_and_learning_move_with_no_empty_slot.ss1",
        ]
    )
    @with_frame_timeout(1500)
    def test_it_switches_to_manual_when_having_to_replace_new_move(self):
        from modules.config.schemas_v1 import Battle
        from modules.context import context
        from modules.modes import BattleAction
        from modules.modes.util import spin
        from modules.pokemon_party import get_party

        context.config.battle = Battle(new_move="stop")

        self.bot_mode.set_on_battle_started(lambda *args: BattleAction.Fight)
        self.bot_mode.allow_ending_on_manual_mode = True

        previous_moves = [learned_move.move.name for learned_move in get_party()[0].moves if learned_move is not None]
        for _ in spin(lambda: self.stats.last_encounter is not None and self.stats.last_encounter.outcome is not None):
            if context.bot_mode == "Manual":
                break
            yield
        new_moves = [learned_move.move.name for learned_move in get_party()[0].moves if learned_move is not None]
        self.assertEqual(new_moves, previous_moves)
        self.assertIsInManualMode()
