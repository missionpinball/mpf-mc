from mpfmc.tests.MpfIntegrationTestCase import MpfIntegrationTestCase
from mpfmc.tests.MpfSlideTestCase import MpfSlideTestCase
from mpf.tests.MpfFakeGameTestCase import MpfFakeGameTestCase


class TestSegmentDisplayEmulator(MpfIntegrationTestCase, MpfFakeGameTestCase, MpfSlideTestCase):

    def get_config_file(self):
        return 'config.yaml'

    def get_machine_path(self):
        return 'integration/machine_files/segment_display_emulator/'

    def test_segment_display_widget(self):
        """Integration test to test segment_display_player in MPF updating segment display widget in MC"""
        self.assertTextOnTopSlide("")

        self.post_event("update_segment_display_1")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("HELLO")

        # this event updates a different segment display (not on top slide) -- text should not change
        self.post_event("update_segment_display_2")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("HELLO")

        self.post_event("update_segment_display_3")
        self.advance_time_and_run()
        self.assertTextOnTopSlide("* BYE *")
