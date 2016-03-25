from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestLine(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/shapes'

    def get_config_file(self):
        return 'test_shapes.yaml'

    def test_line(self):
        self.mc.events.post('slide1')
        self.advance_time()
