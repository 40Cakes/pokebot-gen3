from tests.utility import BotTestCase, with_frame_timeout, with_master_test_states

# The other languages fixed the script oversight the mode uses, so `tests/runner/` only runs it in these
LANGUAGES = ("JPN", "USA_EUR")


class TestNuggetBridge(BotTestCase):
    @with_master_test_states("Nugget Bridge*.ss1")
    @with_frame_timeout(60000)
    def test_it_gets_nuggets_in_all_languages(self):
        from modules.items import get_item_bag, get_item_by_name
        from modules.memory import get_event_flag
        from modules.modes.nugget_bridge import NuggetBridgeMode

        if not NuggetBridgeMode.is_selectable():
            self.skipTest("The mode is not selectable in this state.")

        nugget = get_item_by_name("Nugget")
        nuggets_at_start = get_item_bag().quantity_of(nugget)
        mode = NuggetBridgeMode()
        self.bot_mode.forward_hooks_to(mode)
        for _ in mode.run():
            if get_item_bag().quantity_of(nugget) >= nuggets_at_start + 2:
                # Getting two proves that the Rocket gives one again after a whiteout
                self.assertEqual(nuggets_at_start + 2, get_item_bag().quantity_of(nugget))
                self.assertFalse(get_event_flag("HIDE_NUGGET_BRIDGE_ROCKET"), "The Rocket is gone.")
                return
            yield
        self.fail("The mode stopped before getting two Nuggets.")
