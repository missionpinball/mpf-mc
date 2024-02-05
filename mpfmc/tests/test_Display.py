from mpfmc.uix.display import Display, DisplayOutput
from mpfmc.tests.MpfMcTestCase import MpfMcTestCase


class TestDisplay(MpfMcTestCase):
    def get_machine_path(self):
        return 'tests/machine_files/display'

    def get_config_file(self):
        return 'test_display.yaml'

    def test_display(self):
        # Make sure nested multiple displays are loaded properly and are centered
        self.assertEqual(self.mc.root_window.size, (800, 600))
        self.assertIn('window', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['window'], Display))
        self.assertEqual(self.mc.displays['window'].size, [600, 200])
        self.assertIsInstance(self.mc.displays['window'].parent, DisplayOutput)
        self.assertEqual(self.mc.displays['window'].parent.pos, (0, 167))

        self.assertIn('dmd', self.mc.displays)
        self.assertTrue(isinstance(self.mc.displays['dmd'], Display))
        self.assertEqual(self.mc.displays['dmd'].size, [128, 32])
        self.assertIsInstance(self.mc.displays['dmd'].parent, DisplayOutput)
        self.assertEqual(self.mc.displays['dmd'].parent.pos, (2, 0))

        self.assertEqual(self.mc.targets['window'], self.mc.displays['window'])
        self.assertEqual(self.mc.targets['dmd'], self.mc.displays['dmd'])
        self.assertEqual(self.mc.targets['default'], self.mc.displays['window'])

        self.assertEqual(self.mc.displays['window'].current_slide_name, 'window_slide_1')
        self.assertEqual(self.mc.displays['dmd'].current_slide_name, 'asset_status')
