from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDmd(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/dmd'

    def get_config_file(self):
        return 'test_color_dmd.yaml'

    def test_color_dmd(self):

        self.assertIn('dmd', self.mc.targets)

        self.mc.events.post('slide1')
        self.mc.events.post('dmd_slide')
        self.advance_time(2)
