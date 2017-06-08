from mpfmc.uix.display import Display
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDisplayMultiple(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_display_multiple.yaml'

    def test_mc_display(self):
        # Make sure a multiple displays are loaded properly:

        self.assertIn('window', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['window'], Display))
        self.assertEqual(self.mc.displays['window'].size, [401, 301])

        self.assertIn('display2', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['display2'], Display))
        self.assertEqual(self.mc.displays['display2'].size, [402, 302])

        self.assertEqual(self.mc.targets['display2'],
                         self.mc.displays['display2'])
