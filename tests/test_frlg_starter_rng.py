import unittest


class TestFrlgStarterRng(unittest.TestCase):
    # Values recorded from FireRed (USA, rev 0) runs with trainer ID 6996 / secret ID 49045: `rng` is
    # `gRngValue` one frame before confirming, the comment is the personality value of the generated starter.
    TID, SID, ADVANCES = 6996, 49045, 183
    SHINY_MODEST = 0xCB7DDF0F  # -> 75A7D166
    SHINY_ADAMANT = 0xA52EF4F6  # -> 20B28474
    NOT_SHINY = 0x3DE04E01  # -> BED1CAAB

    def test_personality_value(self):
        from modules.modes.starters import frlg_starter_personality_value

        self.assertEqual(0x75A7D166, frlg_starter_personality_value(self.SHINY_MODEST, self.ADVANCES))
        self.assertEqual(0xBED1CAAB, frlg_starter_personality_value(self.NOT_SHINY, self.ADVANCES))

    def test_shiny_with_any_nature(self):
        from modules.modes.starters import frlg_starter_is_target

        self.assertTrue(frlg_starter_is_target(self.SHINY_MODEST, self.ADVANCES, self.TID, self.SID, set()))
        self.assertTrue(frlg_starter_is_target(self.SHINY_ADAMANT, self.ADVANCES, self.TID, self.SID, set()))
        self.assertFalse(frlg_starter_is_target(self.NOT_SHINY, self.ADVANCES, self.TID, self.SID, set()))

    def test_nature_filter(self):
        from modules.modes.starters import frlg_starter_is_target
        from modules.pokemon import get_nature_by_name

        modest_or_timid = {get_nature_by_name("Modest").index, get_nature_by_name("Timid").index}
        self.assertTrue(frlg_starter_is_target(self.SHINY_MODEST, self.ADVANCES, self.TID, self.SID, modest_or_timid))
        self.assertFalse(frlg_starter_is_target(self.SHINY_ADAMANT, self.ADVANCES, self.TID, self.SID, modest_or_timid))

    def test_finds_rng_advances(self):
        from modules.modes.starters import find_frlg_starter_rng_advances

        self.assertEqual(self.ADVANCES, find_frlg_starter_rng_advances(self.NOT_SHINY, 0xBED1CAAB))
        self.assertIsNone(find_frlg_starter_rng_advances(self.NOT_SHINY, 0x12345678, max_advances=500))
