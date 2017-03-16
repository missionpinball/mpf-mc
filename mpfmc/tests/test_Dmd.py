from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDmd(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/dmd'

    def get_config_file(self):
        return 'test_dmd.yaml'

    def test_dmd(self):

        self.assertIn('dmd', self.mc.targets)

        self.mc.events.post('container_slide')
        self.mc.events.post('dmd_slide')
        self.advance_time(2)

    def test_positioning_named_widgets_on_dmd(self):

        self.assertIn('dmd', self.mc.targets)

        self.mc.events.post('container_slide')
        self.mc.events.post('position_widget_left')
        self.advance_time(1)
        self.mc.events.post('position_widget_right')
        self.advance_time(1)
        self.mc.events.post('position_widget_top')
        self.advance_time(1)
        self.mc.events.post('position_widget_bottom')
        self.advance_time(1)
