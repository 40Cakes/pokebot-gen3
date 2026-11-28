from unittest import mock

from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states


class TestEVTrain(BotTestCase):
    # EV Train works on the same maps as Level Grind
    @with_master_test_states("Level Grind*.ss1")
    @with_frame_timeout(40000)
    def test_it_gains_the_evs_of_defeated_pokemon_in_all_languages(self):
        from modules.battle_state import BattleOutcome, EncounterType
        from modules.context import context
        from modules.debug_utilities import debug_create_pokemon, debug_write_party
        from modules.modes.ev_train import EVTrainMode
        from modules.pokemon import StatsValues
        from modules.pokemon_party import get_party

        # These states test evolving and learning a move, which would stop the bot by default
        context.config.battle = context.config.battle.model_copy(
            update={"new_move": "learn_best", "stop_evolution": False}
        )
        # A lead with no EVs yet, and a target in every stat, so that every Pokémon of the map gives wanted EVs
        stats = ("hp", "attack", "defence", "speed", "special_attack", "special_defence")
        no_evs = StatsValues(**{stat: 0 for stat in stats})
        party = list(get_party())
        party[0] = debug_create_pokemon(party[0].species, party[0].level, original_pokemon=party[0], evs=no_evs)
        debug_write_party(party)
        context.state_cache.reset()
        targets = StatsValues(**{stat: 80 for stat in stats})

        with mock.patch("modules.modes.ev_train.ask_for_ev_targets", return_value=targets):
            yield from self.run_mode(EVTrainMode, 3)

        self.assert_encounters(EncounterType.Land)
        outcomes = [encounter.outcome for encounter in self.stats.logged_encounters]
        self.assertTrue(set(outcomes) <= {BattleOutcome.Won, BattleOutcome.RanAway}, outcomes)
        self.assertIn(BattleOutcome.Won, outcomes)

        # The lead gained exactly the EV yield of the Pokémon it defeated (doubled by Macho Brace and Pokérus)
        lead = get_party()[0]
        multiplier = 1
        if lead.held_item is not None and lead.held_item.name == "Macho Brace":
            multiplier *= 2
        # Even after Pokérus is cured
        if lead.pokerus_status.strain > 0 or lead.pokerus_status.days_remaining > 0:
            multiplier *= 2
        for stat in stats:
            expected = multiplier * sum(
                encounter.pokemon.species.ev_yield[stat]
                for encounter in self.stats.logged_encounters
                if encounter.outcome is BattleOutcome.Won
            )
            details = [
                (encounter.species_name, encounter.outcome, encounter.pokemon.species.ev_yield[stat])
                for encounter in self.stats.logged_encounters
            ]
            self.assertEqual(min(expected, targets[stat]), lead.evs[stat], f"{stat}, x{multiplier}: {details}")
            self.assertLessEqual(lead.evs[stat], targets[stat], stat)
