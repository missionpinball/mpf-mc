from .MpfMcTestCase import MpfMcTestCase


class TestSlidePlayer(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/slide_player'

    def get_config_file(self):
        return 'test_slide_player.yaml'

    # todo need to fix the self.advance_time() method

    # def test_slide_on_default_display(self):
    #     self.mc.events.post('show_slide_1')
    #     self.advance_time()
    #
    #     self.assertEqual(self.mc.targets['display1'].current_slide_name,
    #                      'machine_slide_1')
    #
    #     # now replace that slide at the same priority and make sure it works
    #     self.mc.events.post('show_slide_4')
    #     self.advance_time()
    #     self.assertEqual(self.mc.targets['display1'].current_slide_name,
    #                      'machine_slide_4')
    #
    # def test_slide_on_default_display_hardcoded(self):
    #     self.mc.events.post('show_slide_2')
    #     self.advance_time()
    #     self.assertEqual(
    #         self.mc.displays['display1'].slide_frame.current_slide_name,
    #         'machine_slide_2')
    #
    # def test_slide_on_second_display(self):
    #     self.mc.events.post('show_slide_3')
    #     self.advance_time()
    #     self.assertEqual(
    #         self.mc.displays['display2'].slide_frame.current_slide_name,
    #         'machine_slide_3')
