from tests.utility import BotTestCase, choose_option, with_frame_timeout, with_master_test_states


class TestBerryBlend(BotTestCase):
    @with_master_test_states("Berry Blender*.ss1")
    @with_frame_timeout(20000)
    def test_it_makes_a_pokeblock_in_all_languages(self):
        from modules.context import context
        from modules.items import get_item_bag, get_pokeblocks
        from modules.modes.berry_blend import BerryBlendMode

        if not BerryBlendMode.is_selectable():
            self.fail("The mode can't be selected in this state.")

        def number_of_berries() -> int:
            return sum(slot.quantity for slot in get_item_bag().berries)

        pokeblocks_at_start = len(get_pokeblocks())
        berries_at_start = number_of_berries()
        # Blend the first berry in the bag
        choose_option()
        mode = BerryBlendMode()
        self.bot_mode.forward_hooks_to(mode)
        self.bot_mode.allow_ending_on_manual_mode = True
        yield from mode.run()
        self.assertIsInManualMode()

        # The Pokéblock is given on the results screen, after the blending itself
        while len(get_pokeblocks()) == pokeblocks_at_start:
            context.emulator.press_button("A")
            yield
        self.assertEqual(pokeblocks_at_start + 1, len(get_pokeblocks()))
        self.assertEqual(berries_at_start - 1, number_of_berries(), "Exactly one berry should have been used.")
